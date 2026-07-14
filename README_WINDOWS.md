# FrameDeck for Windows

## Run the portable build

1. Extract the complete ZIP archive.
2. Open the `FrameDeck` folder.
3. Double-click `FrameDeck.exe`.

Python is not required. Keep `_internal` beside the EXE. User data is stored under `%USERPROFILE%\Documents\framedeck` and network media cache under `%LOCALAPPDATA%\FrameDeck\media-cache`.

## Review workflow

- Starts blank with no demo project or media.
- Import multiple MP4/MOV/AVI videos or EXR/PNG/JPG sequences using drag-and-drop or `Ctrl+O`.
- The left panel is a Sources bin. Select one or more clips and use `Add to Playlist`; the same source may be used more than once.
- `Play Playlist` presents one continuous global timeline whose frame range is the sum of every ordered shot.
- Reorder clips by dragging them left/right in the Shot Playlist Timeline. `Earlier`, `Later`, `Alt+Left`, and `Alt+Right` are also available.
- Remove playlist occurrences from the horizontal strip, or remove a Source from the left bin. Source files are never deleted.
- Ctrl+click two sources and choose Compare for synchronized vertical/horizontal wipe, opacity overlay, difference, side-by-side, checkerboard, A/B-only, or flicker modes.
- Pencil and Text notes are stored independently per frame. Press `Esc` or click Navigate to leave an annotation tool. Text returns to Navigate after one placement.
- Export All Notes writes every annotated source frame as PNG.
- Export High Quality MP4 (`Ctrl+Shift+E`) converts MOV/video or EXR/JPG/PNG sequences. Movie FPS is preserved, sequence FPS is entered by the user, and source audio can be retained as AAC.
- Save Playlist (`Ctrl+Shift+S`) writes a portable `.fdplaylist`; Open Playlist (`Ctrl+Shift+O`) restores shot order, active shot, current frame, and timeline visibility.
- Export Image Sequence (`Ctrl+Alt+E`) extracts the active view to full-resolution JPG or PNG frames. EXR/image export uses the current AOV and OCIO view transform.
- User/studio `OCIO` is preferred; otherwise EXR uses the bundled ACES config and JPG/PNG use sRGB.
- Project Color Settings includes ACES 1.2 offline, ACES 1.3/2.0 CG and Studio configs, working space, monitor/view, file-type defaults, and common film-camera presets.
- Use Preset updates the paused viewer as a live OCIO preview; Apply saves it. The active Input, Display, and View are shown in the color/status bars.
- 4K video uses a 2K review proxy without modifying the source.
- Heavy EXR frames decode/OCIO on a bounded background worker, prefetch upcoming frames, and persist color-aware 2K display proxies in Cache Manager. Full-resolution pixels are still used for image/note and MP4 exports.
- The flat teal audio control changes volume or mutes clips containing audio.

## Mouse navigation

- Wheel: zoom at pointer while playback continues.
- Middle drag or Alt+left drag: pan.
- Right drag: continuous zoom.
- Left double-click on the viewer: toggle full screen.
- F: fit the image; F11: toggle full screen; Esc: exit full screen.

## Server cache

Server video and server image sequences begin loading immediately and cache in the background. Tools > Cache Selected Shots can cache several sequences; Tools > Cache Manager shows usage, changes the limit, opens the cache folder, or clears cached files. Optional settings are `FRAMEDECK_CACHE_GB` and `FRAMEDECK_CACHE_MBPS`.
