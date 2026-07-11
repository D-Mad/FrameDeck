

## Viewline

Viewline is a professional Python-based review player framework for VFX, animation, and post-production workflows.
It provides accurate frame-based and time-based playback for image sequences and movie files while integrating seamlessly with production management and publishing workflows.

This project is to provide a lightweight, extensible, and production-friendly framework for media playback, image sequence review, OpenEXR workflows, and OCIO-based color management.

<img width="1848" height="958" alt="image" src="https://github.com/user-attachments/assets/c113466d-2739-4dce-abb7-c966797285ee" />


## Core Responsibilities
* Review image sequences and movie files.
* Frame-accurate playback.
* Audio and video synchronization.
* Timeline navigation and scrubbing.
* Playback controls (Play, Pause, Stop, Loop, Frame Step).
* OpenColorIO (OCIO) color management. (in progress)
* Cache visualization.
* AOV (Arbitrary Output Variable) switching.
* Overlay information (frame number, resolution, FPS, metadata).
* Snapshot and annotation support.
* Pipeline integration with published versions and review notes.


The project is built primarily using Python 3.10, PySide6, OpenGL, OpenImageIO, PyAV, and OCIO.

This is still an early beta release focused mainly on core architecture, playback workflow, and UI foundations. There is still a lot to improve, but the project has reached a stage where I’m comfortable sharing progress publicly.

## Playback

Supported formats:

## Video

* MP4
* MOV
* AVI

## Image Sequences

* PNG
* JPEG
* EXR


## Color Management

* OpenColorIO integration
* ACES workflow architecture *(in progress)*
* Input color space selection *(in progress)*
* Display transform selection *(in progress)*
* View transform selection *(in progress)*


---
## Studio Integration (How to customized based on studio workflows?)


Viewline ships with a lightweight JSON-based implementation that allows the application to run immediately without requiring a production tracking system.

In a production environment, studios should replace these JSON examples with queries to their own production management system (for example ShotGrid, FTrack, or an in-house database).

The default implementation demonstrates how Viewline expects data to be structured. Only the data retrieval and submission logic needs to be customized.
The Viewline itself does not require modification.

* **Projects**
* **Versions**
* **Review notes**



## Projects

* Projects provide the top-level playlist displayed in the Review Player.
* The default implementation reads project information from a JSON file.
* Replace this implementation with your studio's production tracking query.

**Modify the following method:**

```
./scripts/__init__.py

class Projects

    @classmethod
    def get(cls):
```

**Default Example**

The sample project data is located in:

```
./resources/presets/projects.json
```

<span style="color:green;">Use this file as a reference for the expected data structure.</span>

The returned data should contain the information required to populate the Project Browser, such as:

* Project Name
* Description
* Thumbnail

*Studios are free to include additional metadata if required.*



## Versions
* Versions represent published media available for review.
* The default implementation reads version information from a JSON file.
* Studios should replace this implementation with queries to their production tracking system.

**Modify the following method:**

```
./scripts/__init__.py

class Versions

    @classmethod
    def get(cls):
```

**Default Example**

Example version data is located in:

```
./resources/presets/versions.json
```

<span style="color:green;">Use this file as a reference for the expected data structure.</span>

**The returned data typically includes:**

* Version Name
* Media Path
* Thumbnail Path
* project
* entity (Shot)
* task
* Status
* Description
* Created At
* Created By

*Additional metadata may be included depending on the studio workflow.*



## Review Notes
* Review Notes are used to display existing comments and submit new feedback during playback.
* The default implementation stores review notes in a JSON file.
* Production environments should replace this implementation with database queries and write operations.

**Modify the following method for query existing review notes:**

```
./scripts/__init__.py

class Review

    @classmethod
    def get(cls):
```

This method should return all review notes associated with the selected version.


**Modify the following method for create new review notes:**

```
./scripts/__init__.py

class Review

    @classmethod
    def set(cls):
```

This method should submit newly created review notes to your production tracking system.

The default implementation demonstrates the expected data structure only.


**Default Example**

Example review data is located in:

```
./resources/presets/reviews.json
```

*Use this file as a reference when integrating with your production database.*


**Data Flow**, The default application follows the workflow below.

```text

    Projects
        │
        ▼
    Project Browser
        │
        ▼
    Versions
        │
        ▼
    Media Player
        │
        ▼
    Review Notes
        │
        ├── Query Existing Notes
        │
        └── Submit New Notes

```

Only the highlighted data providers need to be replaced for studio integration.

## Why JSON?

The JSON files included with Viewline are intended solely as reference implementations.

They allow developers to:

* Understand the expected data structure.
* Run Viewline without a production tracking system.
* Prototype integrations quickly.
* Test the Review Player independently.

Once integration is complete, the JSON files are no longer required and can be replaced entirely by your production tracking system.

---

## Architecture Overview

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


## Python Version

python-3.10.10 or +

## Dependencies

| Library     | Purpose                 |
| ----------- | ----------------------- |
| PySide6     | UI framework            |
| PyOpenGL    | OpenGL rendering        |
| NumPy       | Image buffer processing |
| PyAV        | Video decoding          |
| OpenImageIO | Image sequence reading  |
| OpenColorIO | Color management        |


## Required Libraries

```yml
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

## Recommended OCIO Config ACES 1.3

Official repository:

```text
    https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES
```


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


## Viewer

* OpenGL texture rendering
* GPU OCIO transforms
* Zoom
* Pan
* Fit modes
* Pixel inspection



## Timeline

* Timeline zoom
* Cached frame visualization
* Frame markers
* Notes/comments
* In/out ranges


## EXR Features

* Layer browser
* AOV switching
* Deep EXR support
* Metadata viewer
* Multi-part EXR support


## Integrations

* USD pipelines
* FFmpeg render export
* Editorial workflow


---
# Author

Subin Gopi *subing85@gmail.com*

---
# License

This project is intended as a free educational and production workflow framework for the animation and VFX industry.

---
