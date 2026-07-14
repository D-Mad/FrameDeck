# FrameDeck portable for Ubuntu

The Ubuntu build has the same full feature set as Windows.

Select clips in the left Sources bin and use `Add to Playlist`. `Play Playlist`
uses one continuous frame timeline equal to the sum of all ordered shots.

`File > Export High Quality MP4` (`Ctrl+Shift+E`) converts MOV/video or EXR/JPG/PNG sequences. Movie FPS is preserved; sequence FPS is user-defined, and source audio can be retained as AAC.

Build on Ubuntu 22.04 or newer:

```bash
sudo apt update
sudo apt install -y python3 python3-venv curl libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0 libpulse0
bash build-ubuntu-appimage.sh
```

The result is `dist/FrameDeck-Ubuntu-x86_64.AppImage`.

Run it with:

```bash
chmod +x FrameDeck-Ubuntu-x86_64.AppImage
./FrameDeck-Ubuntu-x86_64.AppImage
```
