# FrameDeck v0.0.1-beta.12

This beta focuses on reliable professional playback and review collaboration.

## New in this build

- Broad FFmpeg/PyAV container and codec compatibility, including H.264/AVC,
  H.265/HEVC, AV1, VP8/VP9 and ProRes in common professional containers.
- Robust stream selection, VFR FPS fallback, bounded damaged-frame recovery,
  codec metadata and clearer diagnostics when a file cannot be decoded.
- Persistent frame notes and a right-side review comment panel with pins,
  Open/Resolved status, All/Current Frame filters and frame navigation.
- Pencil/Text annotation redo plus the new Arrow annotation tool.
- SMPTE timecode with correct 29.97 and 59.94 drop-frame counting.
- Optional session restore. Startup remains empty unless the user enables
  `Tools > Restore Last Session on Startup`.
- Automatic VFX shot-name matching to locate related plate/comp versions for
  A/B comparison.
- Ping-Pong playback for image sequences, including reverse-aware prefetch and
  playlist/session persistence.

## Codec scope

Actual decode availability is determined by the FFmpeg libraries bundled in
the PyAV runtime. Proprietary camera formats that require a vendor SDK may
still require transcoding to a standard review format.
