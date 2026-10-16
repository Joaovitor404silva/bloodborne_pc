# FSR 4.1.1 on Windows

Select **FSR 4.1.1 (experimental)** in **Upscaler**, then choose the method in
**Graphics > FSR 4.1.1 backend** or the **Play** page's quick settings. Press the
normal **PLAY** button. `Play Bloodborne.exe` uses the same saved selection.
A method change takes effect on the next game start.

| Method | Provider | Installation |
|---|---|---|
| AMD DX12 | AMD's original FSR 4.1.1 runtime through a Vulkan/DX12 shared-buffer bridge | Included in the Windows package |
| Vulkan (fsr4vk) | fsr4vk's INT8 FSR 4.1.1 implementation/model | Press **Download fsr4vk** in Graphics |

The launcher remembers the method independently of the upscaler. When another
upscaler is selected, both method controls show a disabled dash; returning to
FSR 4.1.1 restores the saved method. The controls stay synchronized. Existing
profiles without `fsr411_backend` keep Vulkan (`vk`), rather than silently
switching providers. All new controls and status messages cover the 13 launcher
languages; `vk` and `dx12` are language-independent stored values.

Neither method needs Linux, shader extraction or an additional game starter.
The pre-existing **FSR 4 assets** controls and `fsr4_shaders/` are for the older
FSR 4 v07 path, independent of these two providers.

## AMD DX12: runtime and packaging

`packaging/windows/package.sh` includes the unmodified
`bin/amd_fidelityfx_upscaler_dx12.dll` **4.1.1.2740**, from the official
[AMD FSR SDK v2.3.0 release](https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/releases/tag/v2.3.0).
The DLL must be beside `bb-probe.exe`, not beside the launcher. No binary or
model file is committed to this repository.

`packaging/windows/fetch_fsr411_dx12.py` prepares a verified build cache under
`out/fsr411-dx12/`. The first package build downloads the official prebuilt SDK
archive (about 127 MB); subsequent builds reuse the verified DLL. It checks the
archive and exact member size/SHA-256 before replacing a cached runtime:

- Archive: `FidelityFX-Samples-v2.3.0-prebuilt.zip`
- Archive SHA-256: `f90890b9323bb2f4f2404ac4cdc9395e8495ecdac6f7aa0bcdf1ad1848422273`
- Member: `Samples/Upscalers/FidelityFX_FSR/dx12/x64/Release/amd_fidelityfx_upscaler_dx12.dll`
- DLL SHA-256: `d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46`

The package includes the full, unmodified SDK license, third-party notices and
source/download note under `licenses/AMD-FSR-SDK-*`. The runtime has AMD's
binary redistribution terms; it is **not** covered by the MIT notice on the
vendored API headers. The C headers under `gpu/fsr411_dx12/sdk/` are from the
same SDK release and retain AMD's MIT notices. Only the required headers are
vendored. The bridge is compiled with MSYS2 CLANG64 and system DX12/DXGI APIs;
it does not require an additional MSVC-built bridge DLL.

For a source build, prepare and copy the runtime beside the source loader:

```bash
python packaging/windows/fetch_fsr411_dx12.py
cp out/fsr411-dx12/amd_fidelityfx_upscaler_dx12.dll out/
```

## Vulkan: download and lifetime

The optional provider is installed into `<data>/fsr4vk` (the port folder by
default). `run.py` passes this folder as `BB_FSR4VK_DIR`. Both the launcher
updater and package refresh preserve it. Downloading and replacement are
disabled while the game runs.

The pinned download is **fsr4vk v0.4.3 with the AMD Windows fix**, published by
[0xCydral](https://github.com/0xCydral/bloodborne_pc/releases/tag/windows-v1.7.0-beta.2).
Unpatched v0.4.3 fails on the tested RX 9070 with
`descriptor binding exceeds queried layout size`; the fix removes variable
descriptor count flags from three fixed-size descriptor heaps. See
[upstream issue #1](https://github.com/dvj5411/fsr4vk/issues/1).

`scripts/fetch_fsr4vk.py` verifies the archive and every installed DLL/license,
supports interrupted downloads, and replaces files atomically:

- Archive SHA-256: `049e81577dd0836fd6fb24a2d7fb07d1276951987519d11251905b9e60456ebb`
- DLL SHA-256: `60a90b24f6789cd52c467471d5a66a0fa6d04e1b8af41095242f50367904f8b2`

The download includes provider licenses and a source/patch provenance note.
fsr4vk is GPLv3, its AMD-derived data MIT licensed, and zstd BSD licensed.
It is downloaded by the player rather than bundled into the release.

### Coalesced output stores

On Navi 48 (`1002:7550`, tested on RX 9070), **3840x2160 Quality SDR**
(`2560x1440` input) automatically uses coalesced output stores in the known
v0.4.3 post shader. The host collects the four output pixels per invocation in
workgroup memory, then writes contiguous blocks, following the idea used by the
older FSR 4 post optimization. Original SPIR-V arithmetic, floating-point controls,
and writes to recurrent/history images are retained. The provider DLL, embedded
assets and verified download hashes are unchanged. There is no new download,
sidecar asset directory, startup compiler or launcher setting.

The v0.4.3 DLL imports core Vulkan functions directly rather than obtaining them
through its backend callback. During the first eligible dispatch only, the host
temporarily redirects its `vkCreateShaderModule` import in memory, then restores
it. It does not alter the application's Vulkan dispatch table, patch the DLL on
disk or change environment variables. An existing third-party import hook is
left alone. A thread-local scope enables the rewrite only for the configuration
above; an exact-size/128-bit content fingerprint rejects other shader revisions.
An unavailable import or a rejected optimized module uses the original.
Changing eligibility recreates the context so cached pipelines cannot carry the
rewrite into other modes. Other GPUs, presets, outputs and HDR use the original
shaders. `BB_FSR4VK_POST=0` disables it at process startup for comparisons.

`tools/fsr411_post_lds.py` reproduces the small generated instruction-edit recipe
in `fsr4vk_post_edits.inc` using SPIRV-Tools and the pinned upstream shader.
Original shader SHA-256:
`590d5a48eaf7390059249b59c0b61e664cb6e3198380f0f011b12d165260e7b6`.
The recipe contains only added instructions and replaced stores, rather than a
complete shader or model. GLSL round-tripping was rejected because it changed
output values; the selected direct-SPIR-V rewrite passed full-image byte checks.

Frame retirement also waits for the oldest of the eight provider slots rather
than draining the entire GPU every eight frames. A wait that splits a submission
refreshes the caller's command buffer. A separate in-game A/B test found no FPS
gain from this lifetime change alone. The post-shader
comparison below uses this same retirement behavior in both Vulkan variants.

```bash
python scripts/fetch_fsr4vk.py
python scripts/fetch_fsr4vk.py --check
```

`BB_FSR4VK_DIR` overrides the directory; `BB_FSR4VK=0` disables this provider.
For direct `bb-probe.exe` use, set the directory explicitly; otherwise it looks
for `fsr4vk` beside the executable. The adapter/downloader build on
[0xCydral's integration at 66576ef](https://github.com/0xCydral/bloodborne_pc/tree/66576efbbd272d0c97e04a9bdb5631455d530eae),
with input normalization, scheduler handoff and persistent asset storage here.

## Renderer integration and requirements

The launcher sets `BB_FSR411_BACKEND=dx12` or `vk` for the normal game-start
path, overriding inherited values. `BB_FSR411_NATIVE` is set consistently for
the native feature probe. The renderer chooses the requested Windows provider;
it does not silently change the saved method when it fails.

**AMD DX12** matches the Vulkan adapter's LUID to the DXGI adapter. It requires
an AMD adapter, the original DLL, shared device-local D3D12/Vulkan buffer
memory and importable D3D12 fences as Vulkan timeline semaphores. It explicitly
selects the DLL's non-INT8 **4.1.1** provider, rejecting its legacy FSR 3
provider. DLL presence alone does not prove hardware/driver support: provider
enumeration and context creation must succeed. This route has been tested on
RX 9070; other adapters are not validated by these results.

Inputs/output cross APIs through one shared buffer, GPU copies and explicit
external queue-family ownership transfers. Vulkan signals an input fence;
the D3D12 queue waits on it, executes FSR and signals an output fence. The next
Vulkan submission waits before consuming the result. There is no unconditional
per-frame CPU completion wait at either API boundary. Three DX12 allocator/list
slots wait before reusing an occupied slot; resource changes and teardown still
wait for completion. The synchronous bridge remains available only in the
headless comparison test as a control, not as a launcher method.

**Vulkan (fsr4vk)** enables the provider's complete
[device-feature contract](https://github.com/dvj5411/fsr4vk/blob/v0.4.3/provider/INTEGRATION-CONTRACT.md)
only when its optional DLL is installed. It normalizes color to RGBA16F and
forward depth to reverse R32F, retains motion vectors, and retires the provider's
eight frame slots safely. Both paths propagate replacement command buffers to
callers after splitting a submission. Both support HDR/nonlinear scene inputs
and use the same existing host RCAS sharpening pass, followed by HUD composition.

Neither Windows provider needs `VK_VALVE_shader_mixed_float_dot_product`.
The existing replay remains available when no Windows provider is selected or
installed, including on Linux; the older FSR 4 path is unchanged. A rejected
requested provider follows the existing FSR 3.1 fallback with the reason in the
log/menu. Selection, quality preset and output setting remain intact. fsr4vk is
limited to standard outputs up to 3840x2160 (minimum 64x64); upstream documents
an unwritten final row/column at odd output sizes. Prefer the standard even sizes.

## Vulkan post-shader comparison: Hunter's Dream

Measured on **16 October 2026**, RX 9070, AMD 26.9.2 LLPC, Windows 11, same
stationary Hunter's Dream view in one process. Fullscreen SDR,
**2560x1440 -> 3840x2160 Quality**, host RCAS **0.50**, no FPS cap/VSync,
Immediate presentation. The test build was based on `739e60d` / v1.8.1;
these measurements are not a new in-game benchmark of the subsequent 1.8.2 merge.

| Method | First phase mean FPS | Second phase mean FPS | Combined mean FPS |
|---|---:|---:|---:|
| FSR 4.1.1 Vulkan (fsr4vk) | 81.45 | 80.74 | **81.09** |
| FSR 4.1.1 AMD DX12, reference | 93.90 | 94.10 | **94.00** |
| Existing FSR 4 Vulkan (v07), reference | 85.99 | 85.73 | **85.86** |

The Vulkan row includes the new output-store optimization. An internal A/B
control with the original shader reached **69.29 FPS** in the same run; the new
shader raises it to **81.09 FPS (+17.0%)**. This improves the existing Vulkan
method without adding a launcher choice. FSR 4 and DX12 remain faster here.
Order: original / coalesced / FSR 4 / DX12 / DX12 / FSR 4 /
coalesced / original. Each phase settled for 15 seconds then measured for 40:
80 measured seconds and 16 five-second FPS reports per method, 64 reports total.
No shader/pipeline compilations in the measured reports; similar draw counts
(1126-1133/frame). Repeated phase means differ by less than 0.9% per method.
These are means of FPS reports, not 1% lows or latency measurements. See the
[measurement data](benchmarks/fsr411-vulkan-20261016.json).

Six independent synthetic complete-output comparisons were byte-identical
between original and coalesced shaders, including changing inputs/jitter and
batched submissions; synthetic motion vectors were zero. The tester also reported no obvious issues after several minutes of
gameplay; this is an informal observation, not full-game validation.

The production integration performs the same rewrite in memory with preserved
original numeric IDs instead of using the test's external asset directory.
Final production-wrapper correctness and package checks are listed below;
the eight-phase game benchmark applies to the experimental test build above.

## Validation and reproduction

- Windows CLANG64 renderer, loader and capability-tool build.
- `fsr4vk-post-test` checks device/mode guards, exact generated shader bytes,
  and rejection of changed/truncated modules without a Vulkan device.
- The final in-memory production rewrite passed six complete 4K SDR byte
  comparisons, including changing color, jitter and nonzero motion vectors,
  with submissions batched up to 16 frames. HDR and 1080p checks retained the
  original shader. A 1,200-frame stress test and repeated Quality/Balanced
  switches with unsubmitted work passed; switch-test output was byte-identical
  with optimization disabled/enabled. No import-restoration error was reported.
- Frozen Windows launcher and release package, including the pinned native DLL,
  license/notices and this document; fsr4vk remains a separate verified download.
- Downloader tests cover interrupted/corrupt Vulkan downloads, pinned archive
  and native member rejection, cache reuse and replacement protection.
- Launcher tests cover both methods, inherited environment overrides, preserved
  settings and complete translations in all 13 languages.
- `upscaler-support-test` checks independent availability/fallback without
  changing startup choice, preset or output resolution.
- Both methods were launched through the packaged launcher's normal PLAY path
  into the game world using copied saves. Logs confirmed the requested 4.1.1
  provider rather than an FSR 3.1 fallback.
- Headless production-wrapper checks produce finite, nonconstant SDR/HDR output.
  Synchronous and GPU-fence DX12 output matched byte-for-byte at 1080p and 4K,
  including changing inputs and jitter, over 272 frames per test (16 warmup).
  This compares the two native synchronization paths; it does **not** establish
  image equivalence between AMD's provider and fsr4vk's INT8 implementation/model.

To rebuild and exercise the production wrappers without game files in CLANG64:

```bash
bash build.sh
python packaging/windows/fetch_fsr411_dx12.py
cp out/fsr411-dx12/amd_fidelityfx_upscaler_dx12.dll out/gpu/
python scripts/fetch_fsr4vk.py
ninja -C out/gpu fsr411-compare upscaler-support-test
out/gpu/upscaler-support-test.exe
BB_FSR4VK_DIR="$PWD/fsr4vk" BB_FSR411_NATIVE=1 \
  BB_FSR411_PIPELINE_TEST=1 BB_FSR411_VARY_INPUT=1 \
  out/gpu/fsr411-compare.exe async 2560x1440 3840x2160 ldr 256
```

Use `dx12` for the synchronous control, `vk` for fsr4vk; use `hdr` instead of
`ldr` for HDR inputs. `BB_FSR411_BENCH_DUMP=<file>` saves raw RGBA16F output for
byte comparison. `BB_FSR4VK_DIR` can point to an existing verified provider.
The synthetic timing is a diagnostic, not a substitute for game measurements.

To reproduce and validate the post rewrite (maintainer workflow; not required
to play), download the pinned original shader from fsr4vk v0.4.3 and run with
SPIRV-Tools on PATH:

```bash
curl -L --fail -o original-post.spv \
  https://raw.githubusercontent.com/dvj5411/fsr4vk/7c04e511195bf4420a060d64df84d625a37457e0/assets/fsr411/colors/2160/quality/srgb/pass-27.spv
python tools/fsr411_post_lds.py original-post.spv optimized-post.spv \
  --header gpu/shadps4/video_core/renderer_vulkan/fsr4vk_post_edits.inc
ninja -C out/gpu fsr4vk-post-test
out/gpu/fsr4vk-post-test.exe original-post.spv optimized-post.spv
```

`BB_FSR411_BATCH_SIZE=16` exercises multiple dispatches in one command buffer.
Use otherwise identical `vk 2560x1440 3840x2160 ldr` runs with
`BB_FSR4VK_POST=0` and `BB_FSR4VK_POST=1` to compare raw RGBA16F dumps.

Full-game stability, other GPUs/drivers, odd/custom outputs and identical image
quality between the two different providers are not established by these tests.
