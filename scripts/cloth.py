#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Steadier cloth above 60 FPS (bbport.ini steady_cloth, game version 01.09).

The game's cloth (Havok) moves each particle with Verlet integration once per step, one step per
frame for the player's cape (0x773DF0):

    new = position + (position - previous) * D + acceleration * dt^2

where D is the cloth's own damping factor, the same for every step. Two things in that line only
hold at a steady frame rate:

- (position - previous) is the motion over the previous step. When the steps differ in length,
  as frame times do uncapped (4.5 to 5.7 ms in one second at 220 FPS), the cloth's speed is
  wrong by that ratio every frame: capes and coats shiver. Time-corrected Verlet multiplies it
  by dt / previous dt.
- D is applied per step: at 240 FPS four times as often as at 60, so the cloth loses its swing
  and looks overdamped. D^(60 x frame time) keeps the damping per second of 60 FPS.

At the load of D (vbroadcastss xmm0, [r13+0x10c]; the result is the factor of the motion term in
every loop of the function) the factor becomes D^min(1, 60 x frame time) x (frame time / previous frame
time). The ratio is worked out once per frame (the frame timer's counter, +0x260, changes) by the
first cloth job to see the new frame, and clamped to 0.5..2. At a steady 60 FPS and below both
are 1: unchanged. Our own code; the per-frame timer is the game's (0x55404F8: +0x260 frames,
+0x264 the last frame's time in seconds).
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quit_menu  # noqa: E402

SITE = 0x773E77               # vbroadcastss xmm0, [r13+0x10c] in the Verlet step (0x773DF0)
SITE_BYTES = bytes.fromhex('c4c27918850c010000')
RETURN = SITE + len(SITE_BYTES)
FRAME_TIMER = 0x55404F8       # the frame timer (a pointer): +0x260 frame count, +0x264 frame time, s
FRAME_COUNT, FRAME_TIME = 0x260, 0x264
CAVE = 0x50D9C00              # past Rebirth's code (rebirth.CAVE + up to 0x300) in the last code page
STATE = 0x56D3F80             # the data segment's unused tail (past its size, in its last page):
LAST_FRAME, LAST_TIME, RATIO = STATE, STATE + 4, STATE + 8   # u32, float, float (0 until set)
CALLERS = ((0x76EC70, -0x18), (0x76EE10, -0x20))   # return address, its step number's save slot
CONSTANTS = (0.0, 0.5, 1.0, 2.0, 60.0)


def rip(code, opcode, target):
    """An instruction ending in a rip-relative disp32 to `target`."""
    end = code.here + len(opcode) + 4
    code.data += opcode + struct.pack('<i', target - end)


def code_writes():
    cave = quit_menu.Code(CAVE)
    constants = CAVE + 0x200 - 4 * len(CONSTANTS)
    zero, half, one, two, sixty = (constants + 4 * i for i in range(len(CONSTANTS)))
    labels, jumps = {}, []

    def jump(opcode, name):   # the rel32 form of a short jump's opcode, fixed up at the end
        cave.data += bytes.fromhex('e9' if opcode == 'eb' else '0f' + format(int(opcode, 16) + 0x10, '02x'))
        jumps.append((len(cave.data), name))
        cave.data += bytes(4)

    def label(name):
        labels[name] = len(cave.data)

    cave.raw('9c505152')                       # pushfq; push rax; push rcx; push rdx
    cave.raw('4883ec30')                       # sub rsp, 48
    cave.raw('c5f8110c24')                     # vmovups [rsp], xmm1
    cave.raw('c5f811542410')                   # vmovups [rsp+16], xmm2
    cave.raw('c4c17a10850c010000')             # vmovss xmm0, [r13+0x10c]  (D)
    rip(cave, bytes.fromhex('488b05'), FRAME_TIMER)   # mov rax, [frame timer]
    cave.raw('4885c0')                         # test rax, rax
    jump('74', 'broadcast')                    # no timer yet: unchanged
    # Damping per second as at 60 FPS: D^k, k = min(1, 60 x frame time), for 0 < D < 1 (the frame's,
    # not this step's: a cloth with two steps a frame keeps its damping per frame at 60 FPS).
    rip(cave, bytes.fromhex('c5f82f05'), one)         # vcomiss xmm0, [1]
    jump('73', 'ratio')                        # D >= 1: nothing to scale
    rip(cave, bytes.fromhex('c5f82f05'), zero)        # vcomiss xmm0, [0]
    jump('76', 'ratio')                        # D <= 0
    cave.raw('c5fa1088' + struct.pack('<I', FRAME_TIME).hex())   # vmovss xmm1, [rax+0x264]
    rip(cave, bytes.fromhex('c5f2590d'), sixty)       # vmulss xmm1, xmm1, [60]
    rip(cave, bytes.fromhex('c5f25d0d'), one)         # vminss xmm1, xmm1, [1]
    rip(cave, bytes.fromhex('c5f82f0d'), zero)        # vcomiss xmm1, [0]
    jump('76', 'ratio')                        # no frame time: unchanged
    cave.raw('c5fa114c2420')                   # vmovss [rsp+32], xmm1  (k)
    cave.raw('c5fa11442424')                   # vmovss [rsp+36], xmm0  (D)
    cave.raw('d9442420')                       # fld dword [rsp+32]        st0 = k
    cave.raw('d9442424')                       # fld dword [rsp+36]        st0 = D, st1 = k
    cave.raw('d9f1')                           # fyl2x                     st0 = y = k log2 D
    cave.raw('d9c0')                           # fld st0
    cave.raw('d9fc')                           # frndint                   st0 = int(y), st1 = y
    cave.raw('d9c9')                           # fxch st1                  st0 = y, st1 = int(y)
    cave.raw('d8e1')                           # fsub st0, st1             st0 = frac(y)
    cave.raw('d9f0')                           # f2xm1                     st0 = 2^frac - 1
    cave.raw('d9e8')                           # fld1
    cave.raw('dec1')                           # faddp st1, st0            st0 = 2^frac
    cave.raw('d9fd')                           # fscale                    st0 = 2^frac 2^int = D^k
    cave.raw('ddd9')                           # fstp st1
    cave.raw('d95c2424')                       # fstp dword [rsp+36]       (x87 stack empty again)
    cave.raw('c5fa10442424')                   # vmovss xmm0, [rsp+36]
    label('ratio')
    # Once per frame: RATIO = frame time / previous frame time (0.5..2; 1 for the first).
    cave.raw('8b88' + struct.pack('<I', FRAME_COUNT).hex())   # mov ecx, [rax+0x260]
    rip(cave, bytes.fromhex('3b0d'), LAST_FRAME)      # cmp ecx, [last frame]
    jump('74', 'apply')
    cave.raw('50')                             # push rax
    rip(cave, bytes.fromhex('8b05'), LAST_FRAME)      # mov eax, [last frame]
    rip(cave, bytes.fromhex('f00fb10d'), LAST_FRAME)  # lock cmpxchg [last frame], ecx
    cave.raw('58')                             # pop rax (flags kept)
    jump('75', 'apply')                        # another cloth job took this frame
    cave.raw('c5fa1088' + struct.pack('<I', FRAME_TIME).hex())   # vmovss xmm1, [rax+0x264]
    rip(cave, bytes.fromhex('c5fa1015'), LAST_TIME)   # vmovss xmm2, [last time]
    rip(cave, bytes.fromhex('c5fa110d'), LAST_TIME)   # vmovss [last time], xmm1
    rip(cave, bytes.fromhex('c5f82f15'), zero)        # vcomiss xmm2, [0]
    jump('76', 'first')
    cave.raw('c5f25eca')                       # vdivss xmm1, xmm1, xmm2
    rip(cave, bytes.fromhex('c5f25f0d'), half)        # vmaxss xmm1, xmm1, [0.5]
    rip(cave, bytes.fromhex('c5f25d0d'), two)         # vminss xmm1, xmm1, [2]
    jump('eb', 'store')
    label('first')
    rip(cave, bytes.fromhex('c5fa100d'), one)         # vmovss xmm1, [1]
    label('store')
    rip(cave, bytes.fromhex('c5fa110d'), RATIO)       # vmovss [ratio], xmm1
    label('apply')
    # Only a frame's first step follows a step of another length: the step's callers keep their
    # step number in r13 (0x76EC6B) or r12 (0x76EE0B), saved by this function at [rbp-0x18] and
    # [rbp-0x20].
    for caller, saved in CALLERS:
        rip(cave, bytes.fromhex('488d0d'), caller)    # lea rcx, [return address]
        cave.raw('483b4d08')                   # cmp rcx, [rbp+8]
        jump('75', f'not {caller:x}')
        cave.raw('8b4d' + struct.pack('<b', saved).hex())   # mov ecx, [rbp+saved]  (step number)
        cave.raw('85c9')                       # test ecx, ecx
        jump('75', 'broadcast')                # a later step of the frame: as it was
        jump('eb', 'first step')
        label(f'not {caller:x}')
    label('first step')
    rip(cave, bytes.fromhex('c5fa100d'), RATIO)       # vmovss xmm1, [ratio]
    rip(cave, bytes.fromhex('c5f82f0d'), zero)        # vcomiss xmm1, [0]
    jump('76', 'broadcast')                    # not set yet
    cave.raw('c5fa59c1')                       # vmulss xmm0, xmm0, xmm1
    label('broadcast')
    cave.raw('c5f8c6c000')                     # vshufps xmm0, xmm0, xmm0, 0  (the site's broadcast)
    cave.raw('c5f8100c24')                     # vmovups xmm1, [rsp]
    cave.raw('c5f810542410')                   # vmovups xmm2, [rsp+16]
    cave.raw('4883c430')                       # add rsp, 48
    cave.raw('5a59589d')                       # pop rdx; pop rcx; pop rax; popfq
    cave.jmp(RETURN)
    for at, name in jumps:
        cave.data[at:at + 4] = struct.pack('<i', labels[name] - (at + 4))
    if cave.here > constants:
        raise ValueError('steady cloth code does not fit')
    cave.data += b'\xcc' * (constants - cave.here) + struct.pack(f'<{len(CONSTANTS)}f', *CONSTANTS)
    if cave.here > quit_menu.CAVE_END:
        raise ValueError('steady cloth code runs past the code segment')
    site = quit_menu.Code(SITE)
    site.jmp(CAVE)
    site.data += b'\x90' * (len(SITE_BYTES) - len(site.data))
    return [(cave.offset, bytes(cave.data)), (site.offset, bytes(site.data))]


def check_original(image_bytes):
    if image_bytes(SITE, RETURN) != SITE_BYTES:
        raise ValueError(f'Steady cloth: unexpected code at {SITE + quit_menu.EBOOT_BASE:#x}')
