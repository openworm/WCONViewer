# WCONViewer

Python based 2D viewer for [WCON](https://github.com/openworm/tracker-commons) (Worm tracker Commons Object Notation) files, the JSON based format for *C. elegans* tracking data. See [WCON_format.md](WCON_format.md) for a description of the format.

WCONViewer shows the midline (and perimeter) of the worm as an animation, and can also plot the speed and body curvature of the worm.

## Installation

Requires Python 3.10 or later.

```
pip install .
```

For the interactive GUI, a Qt backend gives the best results (e.g. for positioning the extra plot windows):

```
pip install .[qt]
```

If no Qt bindings are found, the default matplotlib backend is used instead.

Saving animations with `-nogui` requires the `ffmpeg` binary to be installed on your system and on your PATH.

## Usage

```
wconviewer examples/simdata.wcon
```

or equivalently `python -m wconviewer examples/simdata.wcon`. The file can be a `.wcon` file or a `.wcon.zip` archive containing one.

This opens a window with the worm and play/pause/step controls and a slider for moving through time. Checkboxes at the bottom left switch the grid, zoom to the worm and the head and mean position traces on and off.

Run `wconviewer -h` for all options. The main ones are:

| Option | Description |
|--------|-------------|
| `-nogui` | Don't show a window; save the animation as an `.mp4` next to the input file instead |
| `-head`, `--show_head` | Mark the head of the worm |
| `-ht`, `--show_head_trace` | Show a trace of the position of the head |
| `-mt`, `--show_mean_trace` | Show a trace of the average position of the points along the worm |
| `-zoom`, `--zoom_to_worm` | Keep the view zoomed on the worm |
| `-grid`, `--show_grid` | Show a grid |
| `-curv`, `--show_curvature` | Also show a plot of the curvature of the worm |
| `-speed`, `--show_speed` | Also show a plot of the speed of the worm |
| `-a`, `--all` | Show all the extra plots, i.e. the same as `-curv -speed` |
| `-speed_window N` | Calculate speeds from the change in position over `N` time steps. Larger values smooth out noise, but blur fast changes |
| `-start T`, `--start_time T` | Only load the data from time `T` (in seconds) onwards |
| `-end T`, `--end_time T` | Only load the data up to time `T` (in seconds) |
| `-s`, `--suppress_automatic_generation` | Don't generate a perimeter from the midline if the file has none |
| `-i`, `--ignore_wcon_perimeter` | Ignore the perimeter in the file and generate one from the midline |
| `-r`, `--minor_radius` | Minor radius of the worm in mm, used for generated perimeters (default 0.04) |

For example, to save a movie of a file, zoomed on the worm, with the head traced:

```
wconviewer examples/worm_motion_log.wcon -nogui -zoom -ht
```

### Head and speed

Which end of the midline is the head is taken from the `head` field in the file: `"L"` means the first point, `"R"` the last point. The spec doesn't say which end the head is if `head` is missing or `"?"`; in that case WCONViewer assumes the first point is the head, for the head marker, the head trace and the sign of the speed.

The speed plot shows the speed of the worm's average position (or its centroid, if the file has `cx`/`cy`) and of the middle point of the body, in the x and y directions, and as a signed speed which is positive when the worm moves towards its head. So if the head isn't given in the file, the sign of the signed speed is only meaningful if the first point really is the head.


## What is supported

- Time, x and y, with units converted to seconds and mm when the units are recognised. If they aren't, a warning is printed and the values are used as they are.
- Spines with several points per timepoint, or a single point per timepoint.
- Variable origins (`ox`/`oy`), centroids (`cx`/`cy`), and point-based perimeters (`px`/`py`).
- `head` (single value or one per timepoint).
- Missing values (`null`) are treated as missing data.

Only the first record in `data` is displayed, so files with several worms show just the first one (a note is printed). Walk-based perimeters and linked chunks of files (`files`) are not supported.

## Examples

The [examples](examples) folder has some sample files, including data generated from a sine wave (`generate.py` in that folder makes some of them), output from [Worm2D](https://github.com/openworm/Worm2D), and a file from a real tracker.
