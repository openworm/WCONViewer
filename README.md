# WCONViewer
Python based viewer for WCON files in 2D

## Installation

```
pip install .
```

Saving animations with `-nogui` requires the `ffmpeg` binary to be installed on your system.

## Usage

```
wconviewer -f examples/simdata.wcon
```

Run `wconviewer -h` for all options (e.g. `-nogui` to save an `.mp4` instead of showing a window).
