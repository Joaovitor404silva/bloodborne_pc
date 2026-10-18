# AMD ML frame generation on Windows

This branch adds **AMD ML-FG 4.0.1** alongside the existing Vulkan FSR 3.1 and
DLSS frame-generation methods. It builds on the FSR 4.1.1 providers and optional
motion-vector cache in [PR #76](https://github.com/Supermedo/bloodborne_pc/pull/76).

## Selection and requirements

In **Graphics > Frame generation**, select
**AMD ML-FG 4.0.1 (RX 9000, 2× SDR, experimental)**. It generates one intermediate
image per game frame. Upscaling and frame generation are separate settings;
the tested combination uses FSR 4.1.1 AMD DX12 upscaling.

The launcher offers ML-FG after checking the selected Vulkan adapter, its DXGI
LUID, RX 9000 identity, Windows 11, D3D12 support, Win32 memory/fence sharing,
two graphics queues and the exact AMD 4.0.1 provider. The renderer checks support
again. An unsupported saved ML-FG selection or a failed provider initialization
falls back to Vulkan FSR 3.1. The in-game menu disables ML-FG on unsupported hardware.
The labels and support hints cover all 13 launcher languages. A successful check
is represented by the available selection.

The current integration supports **SDR output**. With HDR output active, bbport's
existing presenter skips frame generation and continues showing rendered game
frames. HDR FG requires additional color-format, transfer-function and composition
work. Changing providers during play may pause while GPU work is drained and
the provider context is rebuilt.

## Rendering and presentation

- AMD's unmodified 4.0.1 runtime runs on a D3D12 compute queue, with async workload
  support enabled. The game's world-camera position and basis accompany the
  existing depth, motion vectors and jitter.
- Color, motion and the result use shared textures when supported. Depth uses
  a shared buffer. D3D12 timeline fences and explicit Vulkan ownership transfers
  coordinate the two APIs; the buffer route remains available for driver compatibility.
- A second Vulkan queue consumes the generated result and handles its presentation.
  The render queue can start the next game image while FG finishes. Shared input
  reuse waits for the preceding consumer, and each presentation frame owns its
  HUD backing image until its presentation fence completes.
- Switching presentation queues drains the previous queue first, preserving the
  scheduler timeline and command-pool retirement order across provider changes.
- A compute pass combines the generated-image copy with the existing HUD-mask
  operation. Context recreation and shutdown drain outstanding work before
  destroying shared resources. The existing frames-ahead default remains one.

The original Vulkan FSR 3.1 interpolation and HUD shader retain their calculation.
The common presenter gains the completion-ticket and queue selection needed for
the ML method. FG remains opt-in through the existing saved setting.

## Measurements

Recorded **17 October 2026**, Windows 1.9 experimental integration, Windows 11,
Intel Core **i7-11700B (11th Gen)**, Radeon **RX 9070 16 GB**, AMD **26.9.2 LLPC**.
Stationary **Hunter's Dream** view, fullscreen SDR, **2560×1440 → 3840×2160 Quality**,
FSR 4.1.1 AMD DX12 upscaling, object motion and its cache enabled, RCAS 0.50,
SSR on, LOD −2, game AA/chromatic aberration off; uncapped Immediate presentation,
cheats and mods off. FG's actual context resolution was checked as 3840×2160.

Each method has two phases of **10 seconds warmup + 25 seconds measurement**.
Values below are the means from the game's frame/output counters in the same
session and fixed view. Provider changes occur outside measurement windows.

| Method | Game FPS | Reported output FPS | Game FPS per phase |
|---|---:|---:|---|
| FG off | 86.91 | 86.91 | 87.09 / 86.73 |
| AMD ML-FG 4.0.1 | 73.00 | 145.99 | 73.06 / 72.94 |

In this run ML-FG increases reported output throughput by about **68.0%**, with
about **16.0%** fewer rendered game frames. The figures describe this scene,
hardware and settings. A separate gameplay check found the accepted overlap/HUD
path functional on this RX 9070.

### Separate overlap comparison

An earlier same-session comparison used the same benchmark settings, two phases
per method and the same 10/25-second timing:

| ML-FG 4.0.1 implementation | Game FPS | Output FPS |
|---|---:|---:|
| Serial reference | 70.18 | 140.36 |
| Overlap with detached presentation | 74.54 | 149.08 |

That change improved game throughput by **6.21%**. A subsequent copy/HUD A/B
reduced that GPU step from **0.1660 to 0.1052 ms**; game FPS were **74.44 / 74.87**
(+0.58%), a small difference within the scale of phase variation. These are
separate sessions and retain their own reference values. The branch uses the
overlap and combined copy/HUD path. [Measurement data](benchmarks/ml-fg401-20261017.json).

The public branch builds on the Windows 1.9.1 integration from #76, synchronized
through upstream [`b3fc78b`](https://github.com/Supermedo/bloodborne_pc/commit/b3fc78bff0997f75f73e14a5fffeb1141f0cea70).
The merge retains upstream's controller and keyboard/mouse improvements, low-VRAM
handling, GPU fault reporting and the frame-generation fix for a single long hitch.
Both rendering and FG presentation submissions use upstream's fault reporting;
the ML method retains its separate completion queue. Build,
GPU-output and package checks cover this source; the historical gameplay figures
above retain their Windows 1.9 attribution.

## Building and checking

Use the normal Windows `bash build.sh` and
`bash packaging/windows/package.sh --zip-only`. The package includes the capability
helper, pinned AMD FG runtime and D3D12 Agility 616 runtime beside `bb-probe.exe`.
The SDK archive and extracted DLLs are verified by exact size and SHA-256 in
`packaging/windows/fetch_fg401_dx12.py`. AMD SDK license/notices accompany the
existing FSR 4.1.1 runtime; Microsoft's Agility terms accompany D3D12Core.

Optional GPU targets:

```sh
ninja -C out/gpu fg401-support-test fg401-bridge-test fg401-stress-test fg401-ui-test
```

Run bridge/stress tests with the packaged DLLs beside the test executables.
`BB_FG401_CHECK_OVERLAP=1` selects the detached path in the test harness;
`BB_FG401_SHARED_TEXTURES=0` exercises buffer sharing. The bridge test accepts
render/output dimensions, e.g. `2560x1440 3840x2160 32`.
`python -m unittest discover -s tests -p 'test_fg401*.py'` checks launcher selection,
capability failures, translations and verified runtime extraction.

The GPU tests use synthetic images, resets, multiple in-flight frame slots and
HUD pixels. Their outputs can be compared with the accepted local prototype.
Hardware coverage combines actual RX 9070 runs with older/other-vendor capability
rejection tests.

## Provenance

AMD API headers and runtime: [FidelityFX SDK v2.3.0](https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/releases/tag/v2.3.0).
Integration contract: [AMD ML-FG 4.0.1](https://gpuopen.com/manuals/fsr_sdk/techniques/frame-interpolation-ml/)
and [frame-generation API](https://gpuopen.com/manuals/fsr_sdk/techniques/frame-interpolation-api/).

Developed with OpenAI Codex, with automated GPU checks and local RX 9070 gameplay testing.
