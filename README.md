# Review Player

A professional Python-based review player framework for VFX, animation, and post-production workflows.

This project is designed as a playback and review foundation inspired by internal studio review tools used across the animation and VFX industry.

The goal of this project is to provide a lightweight, extensible, and production-friendly framework for media playback, image sequence review, OpenEXR workflows, and OCIO-based color management.

<img width="1848" height="958" alt="image" src="https://github.com/user-attachments/assets/c113466d-2739-4dce-abb7-c966797285ee" />


---
# bug

* Clear all draws
* Resrt Review Type, Status
* Smooth brush
* Documntation
---

---

The goal of this project is to build a lightweight and pipeline-friendly media review tool focused on animation and VFX workflows.

Current features include:

• Image sequence and video playback
• EXR and AOV support
• OpenGL-based viewer
• Timeline scrubbing and playback cache
• Watermark and overlay system
• Playlist/version browsing workflow

The project is built primarily using Python 3.10, PySide6, OpenGL, OpenImageIO, PyAV, and OCIO.

This is still an early beta release focused mainly on core architecture, playback workflow, and UI foundations. There is still a lot to improve, but the project has reached a stage where I’m comfortable sharing progress publicly.

Planned areas of development include 

annotation tools
comparison modes
improved caching
audio support
deeper production pipeline integration

---

---

# Features

## Viewer

* Video playback
* Image sequence playback
* OpenEXR workflow support
* OpenColorIO (OCIO) integration *(in progress)*
* Frame-accurate stepping
* Timeline scrubbing
* OpenGL-based viewer
* Dynamic fit-to-window display
* Aspect ratio preservation
* Frame stepping
* Loop playback
* Playback overlays / burn-ins
* Cached frame visualization
* AOV switching support

---

## Playback

Supported formats:

### Video

* MP4
* MOV
* AVI

### Image Sequences

* PNG
* JPEG
* EXR

---

## Color Management

* OpenColorIO integration
* ACES workflow architecture *(in progress)*
* Input color space selection *(in progress)*
* Display transform selection *(in progress)*
* View transform selection *(in progress)*

---

# Project Structure

```text
review_player
├── constants
│   └── __init__.py
├── logger
│   └── __init__.py
├── main.py
├── ocio
│   └── __init__.py
├── playback
│   ├── cache.py
│   ├── player.py
│   └── reader.py
├── playlist
│   └── __init__.py
├── resources
│   ├── icons
│   ├── __init__.py
│   └── presets
│       ├── projects.json
│       ├── versions.json
│       └── watermarks.json
├── utils
│   └── __init__.py
└── widgets
    ├── buttons.py
    ├── comboboxs.py
    ├── dialogs.py
    ├── __init__.py
    ├── labels.py
    ├── layouts.py
    ├── menus.py
    ├── pixmaps.py
    ├── playlist.py
    ├── styles.py
    ├── timeline.py
    ├── treewidgets.py
    ├── viewer.py
    └── widgetItems.py
```

---

# Playlist Customization

The playlist system is designed to be customized based on studio workflows.

Enhance the playlist module:

```text
./review_player/playlist/__init__.py
```

### Projects Class

Update the `Projects` class to query project playlist data.

The returned data structure should match:

```text
./review_player/resources/presets/projects.json
```

### Versions Class

Update the `Versions` class to query media/version data.

The returned data structure should match:

```text
./review_player/resources/presets/versions.json
```

---

# Architecture Overview

The project separates playback into multiple independent systems.

```text
Media Reader
    ↓
Frame Cache
    ↓
OCIO Processing
    ↓
Viewer Rendering
    ↓
Timeline / UI
```

---

# Python Version

python-3.10.10 or +

# Dependencies

| Library     | Purpose                 |
| ----------- | ----------------------- |
| PySide6     | UI framework            |
| PyOpenGL    | OpenGL rendering        |
| NumPy       | Image buffer processing |
| PyAV        | Video decoding          |
| OpenImageIO | Image sequence reading  |
| OpenColorIO | Color management        |

---

# Required Libraries

```text
requests: 2.32.2
    certifi: 2024.2.2
    idna: 3.7
    urllib3: 2.2.1
    charset-normalizer: 3.3.2

PySide6: 6.9.0
    shiboken6: 6.9.0
    PySide6-Essentials: 6.9.0
    PySide6-Addons: 6.9.0

pyqtdarktheme: 2.1.0
    darkdetect: 0.7.1

OpenImageIO: 3.0.4.0

PyOpenGL: 3.1.9
opencolorio: 2.5.0
av: 17.0.0
numpy: 1.26.4
```

---

# Recommended OCIO Config

## ACES 1.3 Config

Official repository:

```text
https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES
```

---

# EXR Support

The player currently supports:

* Single-layer EXR
* Multi-layer EXR
* RGB layer extraction
* Basic AOV switching

The EXR reader automatically searches for valid RGB layers.

Example supported channel patterns:

```text
R G B
beauty.R beauty.G beauty.B
rgba.R rgba.G rgba.B
Ci.R Ci.G Ci.B
```

---

# OCIO Workflow (In Progress)

Typical workflow:

```text
EXR (ACEScg)
    ↓
OCIO Display Transform
    ↓
sRGB Monitor
```

---

# Recommended Professional Workflow

| Input      | Display |
| ---------- | ------- |
| ACEScg     | Rec709  |
| Linear     | sRGB    |
| UtilityRaw | Raw     |

---

# Current Limitations

This project is currently an early playback framework.

Known limitations:

* OpenGL currently uses `glDrawPixels()`
* No GPU texture rendering yet
* No threaded decoding
* Video decoding may load many frames into memory
* EXR playback currently converts float images into uint8 previews
* No HDR display pipeline yet
* No audio synchronization
* No annotation system

---

# Future Roadmap

## Playback

* Threaded decoding
* Async frame prefetch
* Smart frame cache
* GPU upload pipeline

---

## Viewer

* OpenGL texture rendering
* GPU OCIO transforms
* Zoom
* Pan
* Fit modes
* Pixel inspection

---

## Timeline

* Timeline zoom
* Cached frame visualization
* Frame markers
* Notes/comments
* In/out ranges

---

## EXR Features

* Layer browser
* AOV switching
* Deep EXR support
* Metadata viewer
* Multi-part EXR support

---

## Review System

* Task integration
* Version integration
* Notes/comments
* Draw annotations
* Review sessions

---

## Integrations

* USD pipelines
* FFmpeg render export
* Editorial workflow

---

# Author

Subin Gopi

---

# License

This project is intended as a free educational and production workflow framework for the animation and VFX industry.
