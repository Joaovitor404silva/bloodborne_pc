# Bloodborne PC - Path Tracing edition: full source

This branch is [SuperMedo's Bloodborne PC](https://github.com/Supermedo/bloodborne_pc) at
`windows-v1.9.8.6` with real-time path tracing added: everything needed to build the
[full download](https://github.com/Joaovitor404silva/bloodborne-pc-path-tracing/releases/latest)
(`Bloodborne-Windows.zip`) yourself.

All credit for the port (engine, launcher, DLSS/FSR, online, everything but path tracing) goes to
SuperMedo and the port's contributors. His history is kept; our work is the commit on top of his tag.
Report path tracing problems to
[bloodborne-pc-path-tracing](https://github.com/Joaovitor404silva/bloodborne-pc-path-tracing), not
to him.

## What we added

- The path tracer: `gpu/shadps4/video_core/renderer_vulkan/rt/` and the shaders
  `gpu/shadps4/video_core/host_shaders/rt_*.comp` (moonlight, bounce light, shadows, reflections,
  water and puddle mirrors, glass), with DLSS Ray Reconstruction in `gpu/dlss_bridge/`.
- The launcher's Path tracing section (Picture & performance) with Auto / Low / Medium / High /
  Custom presets, and updates from the path tracing releases (`launcher/`).
- Tests in `tests/`, tools in `tools/`, design notes and every A/B in `docs/PATH_TRACING.md`.

## Build

Exactly SuperMedo's Windows build ([packaging/windows/README.md](packaging/windows/README.md)), in the
MSYS2 CLANG64 shell with the packages listed there:

```bash
git clone --recursive --branch path-tracing-1.9.8.6 https://github.com/Joaovitor404silva/bloodborne_pc
cd bloodborne_pc
bash build.sh                                              # out/bb-probe.exe with the path tracer
git clone --depth 1 --branch v310.9.16 https://github.com/NVIDIA/DLSS ../DLSS
DLSS_SDK_ROOT=../DLSS bash packaging/windows/build_dlss.sh # DLSS bridge + Ray Reconstruction
bash packaging/windows/package.sh                          # dist/bbport-windows.zip: the full download
```

`build_dlss.sh` needs Visual Studio 2022 (MSVC) for the bridge; see `docs/PATH_TRACING.md`,
"Fetching the DLL and SDK". Path tracing is on by default; `BB_RT=0` turns it off.

## License

GPL-2.0, like the port. NVIDIA's DLSS DLLs are never committed; they come from the SDK under its
licence.
