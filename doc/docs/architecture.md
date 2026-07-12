
### Supported formats:
---

### Video
* MP4
* MOV
* AVI

### Image Sequences

* PNG
* JPEG
* EXR


### Color Management

* OpenColorIO integration
* <span style="color:red;">ACES workflow architecture (in progress)</p>
* <span style="color:red;">Input color space selection (in progress)</p>
* <span style="color:red;">Display transform selection (in progress)</p>
* <span style="color:red;">View transform selection (in progress)</p>

---

### Architecture Overview

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

### Python Version

>[Python-3.10.10](https://www.python.org/downloads/release/python-31010/) or +


### Dependencies

>| Library     | Purpose                 |
>| ----------- | ----------------------- |
>| PySide6     | UI framework            |
>| PyOpenGL    | OpenGL rendering        |
>| NumPy       | Image buffer processing |
>| PyAV        | Video decoding          |
>| OpenImageIO | Image sequence reading  |
>| OpenColorIO | Color management        |


## Required Libraries

```yml

    requests: 2.32.2

        certifi: 2024.2.2 or +
        idna: 3.7 or +
        urllib3: 2.2.1 or +
        charset-normalizer: 3.3.2 or +

    PySide6: 6.9.0 or +

        shiboken6: 6.9.0 or +
        PySide6-Essentials: 6.9.0 or +
        PySide6-Addons: 6.9.0 or +

    pyqtdarktheme: 2.1.0 or +

        darkdetect: 0.7.1 or +

    OpenImageIO: 3.0.4.0 or +

    PyOpenGL: 3.1.9 or +

    opencolorio: 2.5.0 or +

    av: 17.0.0 or +

    numpy: 1.26.4 or +

```

---

## Recommended OCIO Config ACES 1.3

Official repository:

<https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES>



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

---

**© Support, subing85@gmail.com.**

---