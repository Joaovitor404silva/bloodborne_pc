#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Steadier cloth above 60 FPS (bbport.ini steady_cloth, game version 01.09).

The game's Havok cloth applies its constraints once per simulation step with a strength each
cloth operator passes in (a float, broadcast to the four lanes before the solver call). The game
was tuned at 30 and 60 FPS; above that the steps come more often and the same strength pulls the
cloth harder per second: capes and coats shiver or jump. At each of the six sites where an
operator stores its strength, the strength is multiplied by min(1, (60 x frame time)^2): 1 at 60
FPS and below (unchanged), a quarter at 120, about a tenth at 200. The frame time is the game's
own measurement of the last frame, in seconds (the frame timer, its +0x264, written by
0x2034770 as elapsed ticks / tick rate).

Facts from Lantern Engine's notes (Awaken); the code here is our own. Each site's store
(vmovaps [rbp+slot], xmm0, 5 bytes) becomes a jump to a detour in the code cave that keeps the
flags, xmm1 and rax, scales lane 0 of xmm0, does the store and jumps back.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quit_menu  # noqa: E402

# The six stores of a cloth operator's strength: (image offset, stack slot byte of [rbp+slot]).
SITES = ((0x720DEE, 0xA0), (0x72B2FE, 0xA0), (0x730ADE, 0xA0), (0x738711, 0xB0), (0x741F4E, 0x80),
         (0x7420EE, 0xA0))
FRAME_TIMER = 0x55404F8      # the frame timer (a pointer); its +0x264: the last frame's time, s
FRAME_TIME = 0x264
CAVE = 0x50D9C00             # past Rebirth's code (rebirth.CAVE + up to 0x300) in the last code page
SIXTY, ONE = 60.0, 1.0


def original(slot):
    return bytes.fromhex('c5f82945') + bytes([slot])  # vmovaps [rbp+slot], xmm0


def rip(code, opcode, target, tail=b''):
    """An instruction with a rip-relative operand: opcode bytes, disp32 to `target`, then tail."""
    end = code.here + len(opcode) + 4 + len(tail)
    code.data += opcode + struct.pack('<i', target - end) + tail


def code_writes():
    cave = quit_menu.Code(CAVE)
    constants = CAVE + 8 * 64 - 8  # two floats at the cave's end: 60 and 1
    writes = []
    for site, slot in SITES:
        detour = cave.here
        cave.raw('9c')                              # pushfq (the code after the site may test flags)
        cave.raw('488d6424f0')                      # lea rsp, [rsp-16]  (no flags)
        cave.raw('c5f8110c24')                      # vmovups [rsp], xmm1
        cave.raw('50')                              # push rax
        rip(cave, bytes.fromhex('488b05'), FRAME_TIMER)   # mov rax, [rip+FRAME_TIMER]
        cave.raw('4885c0')                          # test rax, rax
        skip = len(cave.data)
        cave.raw('7400')                            # jz done (no timer yet: unchanged)
        cave.raw('c5fa1088' + struct.pack('<I', FRAME_TIME).hex())  # vmovss xmm1, [rax+0x264]
        rip(cave, bytes.fromhex('c5f2590d'), constants)             # vmulss xmm1, xmm1, [60]
        cave.raw('c5f259c9')                        # vmulss xmm1, xmm1, xmm1
        rip(cave, bytes.fromhex('c5f25d0d'), constants + 4)         # vminss xmm1, xmm1, [1]
        cave.raw('c5fa59c1')                        # vmulss xmm0, xmm0, xmm1
        cave.data[skip + 1] = len(cave.data) - (skip + 2)
        cave.raw('58')                              # done: pop rax
        cave.raw('c5f8100c24')                      # vmovups xmm1, [rsp]
        cave.raw('488d642410')                      # lea rsp, [rsp+16]
        cave.raw('9d')                              # popfq
        cave.data += original(slot)                 # the store the site did
        cave.jmp(site + 5)
        jump = quit_menu.Code(site)
        jump.jmp(detour)
        writes.append((jump.offset, bytes(jump.data)))
    if cave.here > constants:
        raise ValueError('steady cloth code does not fit')
    cave.data += b'\xcc' * (constants - cave.here) + struct.pack('<ff', SIXTY, ONE)
    if cave.here > quit_menu.CAVE_END:
        raise ValueError('steady cloth code runs past the code segment')
    return [(cave.offset, bytes(cave.data))] + writes


def check_original(image_bytes):
    for site, slot in SITES:
        if image_bytes(site, site + 5) != original(slot):
            raise ValueError(f'Steady cloth: unexpected code at {site + quit_menu.EBOOT_BASE:#x}')
