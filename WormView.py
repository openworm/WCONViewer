from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import numpy as np
import math
import os
import argparse
import sys
from Player import Player
from SimpleWCON import SimpleWCON


class HalfIntegerLocator(MultipleLocator):
    """Locator placing ticks at half-integer values (..., -0.5, 0.5, 1.5, ...),
    regardless of the current view limits (so it stays fixed while panning/zooming)."""

    def __init__(self):
        super().__init__(base=1.0)

    def tick_values(self, vmin, vmax):
        return super().tick_values(vmin - 0.5, vmax - 0.5) + 0.5


def validate_file(file_path):
    if not os.path.exists(file_path):
        raise argparse.ArgumentTypeError(f"The file {file_path} does not exist.")
    if not os.path.isfile(file_path):
        raise argparse.ArgumentTypeError(f"{file_path} is not a valid file.")
    return file_path


class WormView:
    midline_plot = None
    perimeter_plot = None
    head_plot = None
    times = None

    zoom_to_worm = False
    show_grid = False
    zoom_side = 1.5  # in mm

    def __init__(
        self, show_head=False, zoom_to_worm=False, show_grid=False, zoom_side=1.5
    ):
        self.show_head = show_head
        self.zoom_to_worm = zoom_to_worm
        self.show_grid = show_grid
        self.zoom_side = zoom_side
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

    def set_full_view_limits(self):
        factor = 0.05
        if abs(self.wcon.xmax - self.wcon.xmin) > abs(self.wcon.ymax - self.wcon.ymin):
            side_x = abs(self.wcon.xmax - self.wcon.xmin)
            self.ax.set_xlim(
                [self.wcon.xmin - side_x * factor, self.wcon.xmax + side_x * factor]
            )
            mid = (self.wcon.ymax + self.wcon.ymin) / 2
            self.ax.set_ylim(
                [mid - side_x * (0.5 + factor), mid + side_x * (0.5 + factor)]
            )
        else:
            side_y = abs(self.wcon.ymax - self.wcon.ymin)
            self.ax.set_ylim(
                [self.wcon.ymin - side_y * factor, self.wcon.ymax + side_y * factor]
            )
            mid = (self.wcon.xmax + self.wcon.xmin) / 2
            self.ax.set_xlim(
                [mid - side_y * (0.5 + factor), mid + side_y * (0.5 + factor)]
            )

    def set_zoom_to_worm(self, value):
        print(" - Setting zoom_to_worm: %s" % value)
        self.zoom_to_worm = value
        if not value:
            self.set_full_view_limits()

    def set_show_grid(self, value):
        print(" - Setting show_grid: %s" % value)
        self.show_grid = value
        if value:
            self.ax.xaxis.set_major_locator(MultipleLocator(1))
            self.ax.yaxis.set_major_locator(MultipleLocator(1))
            self.ax.xaxis.set_minor_locator(HalfIntegerLocator())
            self.ax.yaxis.set_minor_locator(HalfIntegerLocator())
            self.ax.xaxis.set_minor_formatter(FormatStrFormatter("%.1f"))
            self.ax.yaxis.set_minor_formatter(FormatStrFormatter("%.1f"))
            self.ax.tick_params(axis="both", which="minor", labelsize=8)
            self.ax.grid(True, which="major", linestyle="-", linewidth=0.5, alpha=0.7)
            self.ax.grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.7)
        else:
            self.ax.grid(False, which="major")
            self.ax.grid(False, which="minor")

    def get_plot(self, args):
        # global times, t_units, x, y, px, py, ax

        self.fig, self.ax = plt.subplots()

        plt.get_current_fig_manager().set_window_title("WCON replay")
        self.ax.set_aspect("equal")

        self.wcon = SimpleWCON(args.wcon_file)

        self.ax.set_xlabel("x (%s)" % self.wcon.x_units_used)
        self.ax.set_ylabel("y (%s)" % self.wcon.y_units_used)

        if not self.zoom_to_worm:
            self.set_full_view_limits()

        self.set_show_grid(self.show_grid)

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

        if self.zoom_to_worm:
            xi = self.wcon.x[:, ti]
            yi = self.wcon.y[:, ti]
            if self.px is not None and self.py is not None:
                xi = np.concatenate([xi, self.px[:, ti]])
                yi = np.concatenate([yi, self.py[:, ti]])

            cx = (np.nanmax(xi) + np.nanmin(xi)) / 2
            cy = (np.nanmax(yi) + np.nanmin(yi)) / 2

            half = self.zoom_side / 2

            self.ax.set_xlim([cx - half, cx + half])
            self.ax.set_ylim([cy - half, cy + half])

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
    parser.add_argument(
        "-zoom",
        "--zoom_to_worm",
        action="store_true",
        help="Zoom the view to the extent of the worm.",
    )
    parser.add_argument(
        "-grid",
        "--show_grid",
        action="store_true",
        help="Show the grid in the view.",
    )

    args = parser.parse_args()

    return args


def main():
    # Default behavior is to use (px, py) if it exists, and if it doesn’t then automatically generate the perimeter from the midline.

    args = parse_args()

    print(" - Arguments parsed: %s" % args)

    wv = WormView(
        show_head=args.show_head,
        zoom_to_worm=args.zoom_to_worm,
        show_grid=args.show_grid,
    )

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
        grid_state=wv.show_grid,
        zoom_state=wv.zoom_to_worm,
        on_toggle_grid=wv.set_show_grid,
        on_toggle_zoom=wv.set_zoom_to_worm,
    )

    if args.nogui:
        # Checkboxes are only useful for interactive control; don't bake them
        # into the frames used for the saved movie.
        anim.check_buttons.ax.set_visible(False)

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
