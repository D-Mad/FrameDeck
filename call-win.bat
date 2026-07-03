:: Copyright (c) 2026, Motion-Craft Technology All rights reserved.
:: Author: Subin. Gopi (subing85@gmail.com).
:: Description: Motion-Craft pipeline license management bash wrapper.
:: WARNING! All changes made in this file will be lost when recompiling source file!


@echo off
set "LIB_DIR=D:/works/C2C/devkit/site-packages"
set "PYTHON=D:/works/C2C/software/python-3.10.10/python.exe"

:: Get the directory of the current script
set "dirname=%~dp0"

:: Set PYTHONPATH using semicolons (;) as separators instead of colons (:)
set "PYTHONPATH=%LIB_DIR%/charset-normalizer/3.3.2;%LIB_DIR%/certifi/2024.2.2;%LIB_DIR%/idna/3.7;%LIB_DIR%/urllib3/2.2.1;%LIB_DIR%/requests/2.32.2;%LIB_DIR%/darkdetect/0.7.1;%LIB_DIR%/pyqtdarktheme/2.1.0;%LIB_DIR%/OpenImageIO/3.0.4.0;%LIB_DIR%/PySide6/6.9.0;%LIB_DIR%/shiboken6/6.9.0;%LIB_DIR%/PySide6-Essentials/6.9.0;%LIB_DIR%/PySide6-Addons/6.9.0;%LIB_DIR%/PyOpenGL/3.1.9;%LIB_DIR%/opencolorio/2.5.0;%LIB_DIR%/av/17.0.0;%LIB_DIR%/numpy/1.26.4;D:/works/developments/review_player/;"

:: Set OpenColorIO Config Path
set "OCIO=D:/works/C2C/devkit/ocio/studio-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"

set "VIEW_LINE_PROFILE_ROOT=%USERPROFILE%/Documents"

:: Run the script passing all arguments
"D:/works/C2C/software/python-3.10.10/python.exe" "%dirname%main.py" %*
