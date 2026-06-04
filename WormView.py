from matplotlib import pyplot as plt
import numpy as np
import json
import math
import os
import argparse
import sys
from Player import Player


def validate_file(file_path):
    if not os.path.exists(file_path):
        raise argparse.ArgumentTypeError(f"The file {file_path} does not exist.")
    if not os.path.isfile(file_path):
        raise argparse.ArgumentTypeError(f"{file_path} is not a valid file.")
    return file_path


class SimpleWCON:
    def __init__(self, wcon_file):

        # Check whether the filename ends with wcon.zip, and if so, unzip it, read the wcon file it contains and load the contents of that using json
        if wcon_file.endswith("wcon.zip"):
            import zipfile

            with zipfile.ZipFile(wcon_file, "r") as zip_ref:
                wcon_files = [f for f in zip_ref.namelist() if f.endswith(".wcon")]
                if len(wcon_files) == 0:
                    raise ValueError("No .wcon file found in the zip archive.")
                elif len(wcon_files) > 1:
                    raise ValueError(
                        "Multiple .wcon files found in the zip archive. Not yet supported..."
                    )
                wcon_file_in_zip = wcon_files[0]
                print(f"Extracting {wcon_file_in_zip} from {wcon_file}...")
                with zip_ref.open(wcon_file_in_zip) as f:
                    wcon = json.load(f)
        else:
            with open(wcon_file, "r") as f:
                print(f"  === Loading WCON from file: {wcon_file}...")
                wcon = json.load(f)

        print(
            " - WCON file loaded. Keys found: "
            + ", ".join(wcon.keys())
            + ". Processing data..."
        )

        self.extras = {}
        for key in wcon:
            if key.startswith("@"):
                self.extras[key] = wcon[key]

        self.t_units = "Unknown units"
        self.x_units = "Unknown units"
        self.y_units = "Unknown units"

        if "units" in wcon:
            self.t_units = wcon["units"].get("t")

            self.x_units = wcon["units"].get("x")
            self.y_units = wcon["units"].get("y")
            print(
                f"   Time units: {self.t_units}, x units: {self.x_units}, y units: {self.y_units}"
            )

        # "data" is arrayable: it may be a single record object or a list of
        # records (multiple worms / timepoint chunks). Normalise to a list.
        data = wcon["data"]
        if isinstance(data, dict):
            data = [data]

        record = data[0]
        if len(data) > 1:
            print(
                " - Note: %d data records found; this minimal viewer only displays the first (id=%s)."
                % (len(data), record.get("id"))
            )

        print(" - Data records: %d" % len(data))
        print(" - Data keys: %s" % list(record.keys()))
        print(" - Data time: %s" % len(record["t"]))
        print(" - Data x: %s" % len(record["x"]))
        print(" - Data y: %s" % len(record["y"]))

        self.times = np.array(record["t"])

        factor = 1

        if self.x_units == "millimeters" or self.x_units == "mm":
            factor = 1
            self.x_units_used = self.x_units
            self.y_units_used = self.y_units
        elif (
            self.x_units == "micrometers"
            or self.x_units == "um"
            or self.x_units == "µm"
        ):
            factor = 1e-3
            self.x_units_used = "mm"
            self.y_units_used = "mm"
        else:
            self.x_units_used = self.x_units
            self.y_units_used = self.y_units

        # Cast to float so that any None values in experimental wcon data
        # become nan (np.array([1.0, None], dtype=float) -> [1., nan]).
        self.x = np.array(record["x"], dtype=float).T * factor
        self.y = np.array(record["y"], dtype=float).T * factor

        # Low-resolution trackers may give a single xy point per timepoint, so
        # x/y are 1-D (n_timepoints,). Reshape to (1, n_timepoints) so that the
        # [:, ti] indexing used downstream works uniformly with the spine case.
        if self.x.ndim == 1:
            self.x = self.x.reshape(1, -1)
            self.y = self.y.reshape(1, -1)

        # Variable origin: if ox/oy are present, all positional values at a
        # timepoint are relative to that origin (spec: "Variable origin and
        # centroid position"). A minimal reader must add it back to recover
        # absolute coordinates. ox/oy are per-timepoint arrays (or a single
        # local constant); x has shape (n_body, n_t) so (n_t,) broadcasts.
        self.ox = record.get("ox")
        self.oy = record.get("oy")
        if self.ox is not None and self.oy is not None:
            self.ox = np.atleast_1d(np.array(self.ox, dtype=float)) * factor
            self.oy = np.atleast_1d(np.array(self.oy, dtype=float)) * factor
            self.x = self.x + self.ox
            self.y = self.y + self.oy

        print(f"Times: {self.times}, shape: {self.times.shape}")
        print(f"x: {self.x}, shape: {self.x.shape}")
        print(f"y: {self.y}, shape: {self.y.shape}")

        self.xmax = np.nanmax(self.x)
        self.xmin = np.nanmin(self.x)
        self.ymax = np.nanmax(self.y)
        self.ymin = np.nanmin(self.y)
        print(
            f"Range of time: {self.times[0]}{self.t_units}->{self.times[-1]}{self.t_units}; x range: {self.xmin}{self.x_units}->{self.xmax}{self.x_units}; y range: {self.ymin}{self.y_units}->{self.ymax}{self.y_units}"
        )

        if "px" in record:
            self.px = np.array(record["px"], dtype=float) * factor  # (n_t, n_perim)
            # px is arrayed per timepoint, so the origin (n_t,) is applied
            # along axis 0 via a trailing axis.
            if self.ox is not None and self.px.ndim == 2:
                self.px = self.px + self.ox[:, None]
            print(
                f"px shape: {np.array(self.px).shape}, max: {np.nanmax(self.px)}, min: {np.nanmin(self.px)}"
            )
        else:
            self.px = None

        if "py" in record:
            self.py = np.array(record["py"], dtype=float) * factor  # (n_t, n_perim)
            if self.oy is not None and self.py.ndim == 2:
                self.py = self.py + self.oy[:, None]
            print(
                f"py shape: {np.array(self.py).shape}, max: {np.nanmax(self.py)}, min: {np.nanmin(self.py)}"
            )
        else:
            self.py = None


class WormView:
    midline_plot = None
    perimeter_plot = None
    head_plot = None
    times = None

    def __init__(self, show_head=False):
        self.show_head = show_head
        print(" - Initializing WormView")

    def get_perimeter(self, x, y, r):
        n_bar = x.shape[0]
        num_steps = x.shape[1]

        n_seg = int(n_bar - 1)

        # radii along the body of the worm
        r_i = np.array(
            [
                r * abs(math.sin(math.acos(((i) - n_seg / 2.0) / (n_seg / 2.0 + 0.2))))
                for i in range(n_bar)
            ]
        ).reshape(-1, 1)

        diff_x = np.diff(x, axis=0)
        diff_y = np.diff(y, axis=0)

        arctan = np.arctan2(diff_x, -diff_y)
        d_arr = np.zeros((n_bar, num_steps))

        d_mask = np.full((n_bar, num_steps), False)
        arctan_diff = np.abs(np.diff(arctan, axis=0)) > np.pi
        d_mask[1:-1, :] = arctan_diff

        # d of worm endpoints is based off of two points, whereas d of non-endpoints is based off of 3 (x, y) points

        d_arr[:-1, :] = arctan
        d_arr[1:, :] = d_arr[1:, :] + arctan
        d_arr[1:-1, :] = d_arr[1:-1, :] / 2
        d_arr = d_arr - np.pi * d_mask
        dx = np.cos(d_arr) * r_i
        dy = np.sin(d_arr) * r_i

        px = np.zeros((2 * n_bar, x.shape[1]))
        py = np.zeros((2 * n_bar, x.shape[1]))

        px[:n_bar, :] = x - dx
        px[n_bar:, :] = np.flipud(x + dx)  # Make perimeter counter-clockwise

        py[:n_bar, :] = y - dy
        py[n_bar:, :] = np.flipud(y + dy)  # Make perimeter counter-clockwise

        return px, py

    def reset(self):

        print(" - Resetting WormView")
        self.midline_plot = None
        self.perimeter_plot = None
        self.head_plot = None
        plt.close("all")

    def get_plot(self, args):
        # global times, t_units, x, y, px, py, ax

        self.fig, self.ax = plt.subplots()

        plt.get_current_fig_manager().set_window_title("WCON replay")
        self.ax.set_aspect("equal")

        self.wcon = SimpleWCON(args.wcon_file)

        self.ax.set_xlabel("x (%s)" % self.wcon.x_units_used)
        self.ax.set_ylabel("y (%s)" % self.wcon.y_units_used)

        factor = 0.05
        if abs(self.wcon.xmax - self.wcon.xmin) > abs(self.wcon.ymax - self.wcon.ymin):
            side = abs(self.wcon.xmax - self.wcon.xmin)
            self.ax.set_xlim(
                [self.wcon.xmin - side * factor, self.wcon.xmax + side * factor]
            )
            mid = (self.wcon.ymax + self.wcon.ymin) / 2
            self.ax.set_ylim([mid - side * (0.5 + factor), mid + side * (0.5 + factor)])
        else:
            side = abs(self.wcon.ymax - self.wcon.ymin)
            self.ax.set_ylim(
                [self.wcon.ymin - side * factor, self.wcon.ymax + side * factor]
            )
            mid = (self.wcon.xmax + self.wcon.xmin) / 2
            self.ax.set_xlim([mid - side * (0.5 + factor), mid + side * (0.5 + factor)])

        if "@CelegansNeuromechanicalGaitModulation" in self.wcon.extras:
            center_x_arr = self.wcon.extras["@CelegansNeuromechanicalGaitModulation"][
                "objects"
            ]["circles"]["x"]
            center_y_arr = self.wcon.extras["@CelegansNeuromechanicalGaitModulation"][
                "objects"
            ]["circles"]["y"]
            radius_arr = self.wcon.extras["@CelegansNeuromechanicalGaitModulation"][
                "objects"
            ]["circles"]["r"]

            for center_x, center_y, radius in zip(
                center_x_arr, center_y_arr, radius_arr
            ):
                circle = plt.Circle((center_x, center_y), radius, color="b")
                self.ax.add_patch(circle)
        else:
            print("No objects found")

        if self.wcon.px is not None and self.wcon.py is not None:
            if args.ignore_wcon_perimeter:
                print(
                    "Ignoring (px, py) values in WCON file and computing perimeter from midline."
                )
                self.px, self.py = self.get_perimeter(self.x, self.y, args.minor_radius)
            else:
                print("Using (px, py) from WCON file")
                self.px = np.array(self.wcon.px).T
                self.py = np.array(self.wcon.py).T
        else:
            if not args.suppress_automatic_generation and self.wcon.x.shape[0] >= 2:
                print("Computing perimeter from midline")
                self.px, self.py = self.get_perimeter(
                    self.wcon.x, self.wcon.y, args.minor_radius
                )
            else:
                print("Not computing perimeter from midline")
                self.px = None
                self.py = None

        return self.fig, self.ax

    def update(self, ti):
        f = ti / len(self.wcon.times)
        t = self.wcon.times[ti]
        print(
            f" - Updating WormView for time index: {ti} ({t}{self.wcon.t_units}), with {len(self.wcon.x[:, ti])} x points and {len(self.wcon.y[:, ti])} y points."
        )
        # global midline_plot, perimeter_plot, times, t_units, x, y, px, py, ax

        color = "#%02x%02x00" % (int(0xFF * (f)), int(0xFF * (1 - f) * 0.8))
        print(
            "     Time %s %s, step: %s, fract: %f, color: %s"
            % (t, self.wcon.t_units, ti, f, color)
        )

        if self.midline_plot is None:
            (self.midline_plot,) = self.ax.plot(
                self.wcon.x[:, ti],
                self.wcon.y[:, ti],
                color="g",
                label="t=%sms" % self.wcon.times[ti],
                linewidth=0.5,
            )
        else:
            self.midline_plot.set_data(self.wcon.x[:, ti], self.wcon.y[:, ti])

        if self.px is not None and self.py is not None:
            if self.perimeter_plot is None:
                (self.perimeter_plot,) = self.ax.plot(
                    self.px[:, ti], self.py[:, ti], color="grey", linewidth=1
                )
            else:
                self.perimeter_plot.set_data(self.px[:, ti], self.py[:, ti])

        if self.show_head:
            if self.head_plot is None:
                print("Adding head")
                (self.head_plot,) = self.ax.plot(
                    [self.wcon.x[0, ti]],
                    [self.wcon.y[0, ti]],
                    color="r",
                    marker="o",
                    label="t=%sms" % self.wcon.times[ti],
                    linewidth=2,
                )
            else:
                self.head_plot.set_data([self.wcon.x[0, ti]], [self.wcon.y[0, ti]])

        return self.midline_plot, self.perimeter_plot, self.head_plot


def parse_args():
    parser = argparse.ArgumentParser(
        description="Open a player for the worm behaviour."
    )
    parser.add_argument(
        "-f",
        "--wcon_file",
        type=validate_file,
        help="WCON file path",
        default="examples/simdata.wcon",
    )
    parser.add_argument(
        "-nogui", action="store_true", help="Just load file, don't show GUI"
    )
    parser.add_argument(
        "-s",
        "--suppress_automatic_generation",
        action="store_true",
        help="Suppress the automatic generation of a perimeter which would be computed from the midline of the worm. If (px, py) is not specified in the WCON, a perimeter will not be shown.",
    )
    parser.add_argument(
        "-i",
        "--ignore_wcon_perimeter",
        action="store_true",
        help="Ignore (px, py) values in the WCON. Instead, a perimeter is automatically generated based on the midline of the worm.",
    )
    parser.add_argument(
        "-r",
        "--minor_radius",
        type=float,
        default=40e-3,
        help="Minor radius of the worm in millimeters (default: 40e-3)",
        required=False,
    )
    parser.add_argument(
        "-head",
        "--show_head",
        action="store_true",
        help="Show the head of the worm.",
    )

    args = parser.parse_args()

    return args


def main():
    # Default behavior is to use (px, py) if it exists, and if it doesn’t then automatically generate the perimeter from the midline.

    args = parse_args()

    print(" - Arguments parsed: %s" % args)

    wv = WormView(show_head=args.show_head)

    fig, ax = wv.get_plot(args)

    def update(ti):
        print(" ------  Animating the plot for time index: %d" % ti)
        return wv.update(ti)

    anim = Player(
        fig,
        update,
        maxi=len(wv.wcon.times) - 1,
        times=[t for t in wv.wcon.times],
        t_units=wv.wcon.t_units,
    )

    if not args.nogui:
        plt.show()
    else:
        print("GUI suppressed, exiting without showing %s." % anim)

        from matplotlib.animation import FFMpegWriter

        FFwriter = FFMpegWriter(fps=10)
        mp4_file = args.wcon_file.replace(".wcon.zip", ".wcon").replace(".wcon", ".mp4")
        print(f"Saving animation to: {mp4_file}")
        anim.save(mp4_file, writer=FFwriter)


if __name__ == "__main__":
    sys.exit(main())
