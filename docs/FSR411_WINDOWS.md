# FSR 4.1.1 on Windows through fsr4vk

In **Graphics**, press **Download FSR 4.1.1**, select **FSR 4.1.1 (experimental)**
in the existing Upscaler control, and press the normal **PLAY** button. No Linux,
Proton, shader extraction, OptiScaler injection or additional game starter is needed.

This uses [fsr4vk](https://github.com/dvj5411/fsr4vk)'s **INT8 4.1.1 model**.
It is a different implementation from executing AMD's original DX12 DLL; the
images are not claimed to be identical. The ordinary FSR 4 choice remains v07.

## Download and lifetime

The optional provider is installed into `<data>/fsr4vk` (the port folder by
default). `run.py` passes this folder as `BB_FSR4VK_DIR`. Both the launcher updater
and the package refresh preserve it. Downloading is disabled while the game runs.

The pinned download is **fsr4vk v0.4.3 with the AMD Windows fix**, published by
[0xCydral](https://github.com/0xCydral/bloodborne_pc/releases/tag/windows-v1.7.0-beta.2).
Upstream v0.4.3 fails on this RX 9070 with `descriptor binding exceeds queried
layout size`; the fixed build removes the variable descriptor count flags from
the three fixed-size descriptor heaps. See [upstream issue #1](https://github.com/dvj5411/fsr4vk/issues/1).

`scripts/fetch_fsr4vk.py` verifies the archive SHA-256 and every installed DLL and
license file, supports interrupted downloads, and replaces each file atomically.
The archive SHA-256 is
`049e81577dd0836fd6fb24a2d7fb07d1276951987519d11251905b9e60456ebb`;
the DLL SHA-256 is
`60a90b24f6789cd52c467471d5a66a0fa6d04e1b8af41095242f50367904f8b2`.
The download contains the provider licenses and a source/provenance note. No
provider binary, extracted model, game data or proprietary AMD DX12 DLL is added
to this repository. The provider is GPLv3, AMD-derived data MIT, and zstd BSD.

From a source tree:

```sh
python scripts/fetch_fsr4vk.py
python scripts/fetch_fsr4vk.py --check
```

`BB_FSR4VK_DIR` overrides the provider directory; `BB_FSR4VK=0` disables this
provider. Direct `bb-probe.exe` users can set the directory explicitly (without
`run.py`, the fallback directory is `fsr4vk` beside the executable).

## Renderer integration

The DLL is loaded through its FFX API. Only when it is installed and the device
supports the complete [integration contract](https://github.com/dvj5411/fsr4vk/blob/v0.4.3/provider/INTEGRATION-CONTRACT.md)
does device creation enable the additional descriptor-buffer, mutable-descriptor
and descriptor-indexing features. This route does not require
`VK_VALVE_shader_mixed_float_dot_product`. The existing replay remains available
when this optional provider is absent, including on Linux.

A GPU compute pass converts the game's color input to RGBA16F and its forward
depth to R32F reverse depth. It crops aligned scene targets to the actual render
extent and preserves the original RG16F motion vectors. HDR scene inputs and
tonemapped sRGB inputs use their respective FFX color modes. The existing host
RCAS pass supplies the complete sharpening range because fsr4vk has no internal
sharpening. HUD composition remains after reconstruction.

The provider owns eight frame slots. The wrapper waits for their completion
before reusing them and propagates any replacement command buffer to its callers.
Output changes retire the previous context safely. Missing features, a load
failure or a rejected frame follow the existing FSR 3.1 fallback, with the reason
in the log/menu. The provider is experimental and limited to output dimensions
from 64x64 through 3840x2160. Prefer the launcher's standard, even-sized outputs;
upstream documents an unwritten final row/column at odd output dimensions.

The adapter and downloader are adapted from
[0xCydral/bloodborne_pc at 66576ef](https://github.com/0xCydral/bloodborne_pc/tree/66576efbbd272d0c97e04a9bdb5631455d530eae).
This integration adds input normalization, the scheduler handoff, persistent
asset storage, and Supermedo's launcher controls. It does not need the large
0.3/0.4 merge in Supermedo PR #50, whose replay still requires the VALVE feature.

## Validation and comparison

Test machine: Windows 11, **Radeon RX 9070 16 GB**, AMD **26.9.2** (LLPC;
Vulkan 1.4.355). Base: Supermedo `windows` at `bee7ec1` / windows-v1.8.1.

The same port was also tested with a native Vulkan/DX12 shared-buffer bridge to
AMD's original `amd_fidelityfx_upscaler_dx12.dll` **4.1.1.2740**. Both routes
used the same game, output/preset, motion vectors and a common host RCAS pass at
0.50. The game used a copy of the saves and a separate configuration. Stealth and
no-death were enabled in that test configuration to keep the scene stationary.

Four static phases, DX12 / Vulkan / Vulkan / DX12, each measured for 30 seconds
after 15 seconds of warmup, at **2560x1440 -> 3840x2160, Quality**:

| Backend | Mean reported FPS | Phase means |
|---|---:|---|
| fsr4vk with AMD fix | 59.9 | 59.88 / 59.87 |
| Original AMD DLL through the shared-buffer DX12 bridge | 49.6 | 49.72 / 49.52 |

These are means of the port's five-second FPS reports, not 1%-low measurements.
fsr4vk reaches the approximately 60 Hz presentation ceiling here; this is not its
maximum uncapped throughput. No FSR 3.1 fallback, device loss or frame-slot error
occurred in these phases. Brief camera pans and captured frames were also checked;
this is not a complete play-through or an image-quality equivalence test.

The isolated 4K synthetic test favored the original DLL (about 3.08 ms versus
6.75 ms including the necessary wrapper work and completion waits). The opposite
result in the full game is consistent with the DX12 bridge's per-frame Vulkan
completion and DX12 fence waits serializing the renderer. The native Vulkan
provider is therefore the proposed integration for this tested configuration.

Additional checks:

- MSYS2 CLANG64 build of the renderer and `bb-probe.exe`.
- `fsr4vk-test`: finite, nonconstant GPU output with real RGBA8-sRGB / D32S8
  inputs, 720p -> 1080p HDR inputs, 1440p -> 4K sRGB inputs, and 1080p Native AA.
- Eight downloader tests: interruption/resume, archive/member corruption,
  outdated files, refused replacement, license extraction, persistent paths.
- `upscaler-support-test`: independently available providers and fallback while
  preserving the startup choice, quality preset and output resolution.

The final source launcher downloaded the provider over HTTPS, saved the FSR 4.1.1
choice, and launched the normal game-start path into the world. Its log confirmed
the 4.1.1 VK INT8 Quality model at 4K, with no FSR 3.1 fallback.
Other GPUs, full game coverage, odd/custom outputs and a rebuilt public release
package are not established by these results.
