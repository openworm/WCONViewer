import math
import sys
import os
import numpy as np
import matplotlib.pyplot as plt

from wconviewer.SimpleWCON import SimpleWCON


def dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def print_(msg):
    print("WCONViewer >>> %s" % (msg))


def select_frames(wcon, rate_to_plot=1, max_time_s=1e12):
    """
    Select the frames to analyse from a SimpleWCON: the first frame, then every
    rate_to_plot-th frame (counting from 1), up to max_time_s.

    Returns ts (n_frames), x and y (n_body_points, n_frames).
    """
    frame_indices = [
        fi
        for fi in range(len(wcon.times))
        if (fi == 0 or (fi + 1) % rate_to_plot == 0) and wcon.times[fi] <= max_time_s
    ]
    return wcon.times[frame_indices], wcon.x[:, frame_indices], wcon.y[:, frame_indices]


def _swap_xy(x, y):
    # The worm is plotted with x and y swapped, so that it moves "up"
    return y, x


def compute_speeds(ts, x, y):
    """
    Speed of the middle point of the body and of the average of all body points,
    in the x and y directions of the file, between successive frames.

    Returns a dict with the times of the speeds (ts[1:]), the number of body
    points, the index of the middle point and the four speed series.
    """
    points = x.shape[0]
    middle_point = points / 2
    dt = np.diff(ts)

    return {
        "times": ts[1:],
        "num_points": points,
        "middle_point": middle_point,
        "middle_x": np.diff(x[int(middle_point)]) / dt,
        "middle_y": np.diff(y[int(middle_point)]) / dt,
        "ave_x": np.diff(x.mean(axis=0)) / dt,
        "ave_y": np.diff(y.mean(axis=0)) / dt,
    }


def compute_body_curvature(ts, x, y):
    """
    Angle (degrees, 180 = straight) between the points 2 before and 2 after each
    body point, for all body points except the 2 at each end.

    Returns an array of shape (n_frames, n_body_points - 4).
    """
    body_curv_data = np.zeros((len(ts), x.shape[0] - 4))

    for ti in range(len(ts)):
        for i in range(x.shape[0])[2:-2]:
            x1 = x[i - 2, ti]
            xc = x[i, ti]
            x2 = x[i + 2, ti]

            y1 = y[i - 2, ti]
            yc = y[i, ti]
            y2 = y[i + 2, ti]

            a1 = math.atan2(y1 - yc, x1 - xc)
            a2 = math.atan2(y2 - yc, x2 - xc)
            angle = a2 - a1
            if angle < 0:
                angle += 2 * math.pi
            if angle > 2 * math.pi:
                angle = 2 * math.pi - angle

            deg = 360 * (angle / (2 * math.pi))

            body_curv_data[ti][i - 2] = deg

            # print("At t=%s, i=%s: angle from between (%s,%s) - (%s,%s) - (%s,%s) = %s, %sdeg"%(ts[ti], i, x1,y1,xc,yc,x2,y2,angle,deg))

    return body_curv_data


def generate_midlines_plot(ts, x, y, spacing=0.05, save_to=None):
    """
    Plot the midline of the worm at each time, each shifted by spacing, with the
    first midline (dotted) repeated at each shift for comparison.
    """
    fig = plt.figure()
    ax = fig.add_subplot(111)

    plot_x, plot_y = _swap_xy(x, y)

    for fi, t_s in enumerate(ts):
        offset = fi * spacing

        lines = ax.plot(plot_x[:, fi] + offset, plot_y[:, fi], "-")
        if fi % 5 == 0:
            time_ = "%ss" % t_s if not t_s == int(t_s) else "%ss" % int(t_s)

            ax.text(50 + (fi * spacing), 10, time_, fontsize=12)
        ax.plot(
            plot_x[:, 0] + offset,
            plot_y[:, 0],
            ":",
            color=lines[0].get_color(),
            linewidth=0.5,
        )

    info = "Midline of worm through time (to %s seconds)" % ts[-1]

    plt.xlabel("y direction (scaled)")
    plt.ylabel("x direction")
    fig.canvas.manager.set_window_title(info)
    plt.title(info)

    if save_to:
        plt.savefig(save_to)

    return fig


def generate_speeds_plot(speeds, save_to=None):
    """
    Plot the output of compute_speeds, with the same x/y swap as plot_midlines.
    """
    fig = plt.figure()
    info = "Speed of worm in x (lateral) & y (along body) directions"
    fig.canvas.manager.set_window_title(info)
    plt.title(info)
    plt.xlabel("Time (s)")
    plt.ylabel("Speed")

    times = speeds["times"]
    points = speeds["num_points"]
    middle_point = speeds["middle_point"]
    ave_x, ave_y = _swap_xy(speeds["ave_x"], speeds["ave_y"])
    middle_x, middle_y = _swap_xy(speeds["middle_x"], speeds["middle_y"])

    plt.plot(
        times,
        ave_x,
        "red",
        label="Speed in x of average of %i points" % points,
    )
    plt.plot(
        times,
        middle_x,
        "pink",
        label="Speed in x dir of point %i/%i" % (middle_point, points),
        linestyle="--",
    )
    plt.plot(
        times,
        ave_y,
        "blue",
        label="Speed in y of average of %i points" % points,
    )
    plt.plot(
        times,
        middle_y,
        "cyan",
        label="Speed in y dir of point %i/%i" % (middle_point, points),
        linestyle="--",
    )

    plt.plot([0, times[-1]], [0, 0], "grey", linestyle=":")

    plt.legend(loc=2, fontsize="x-small")

    if save_to:
        plt.savefig(save_to, bbox_inches="tight")

    return fig


def generate_body_curvature_plot(
    ts,
    body_curv_data,
    save_to=None,
    cmap="bwr",
    min_curvature=170,
    max_curvature=190,
):
    """
    Plot the output of compute_body_curvature as a heat map of curvature against
    time and position along the body.
    """
    fig = plt.figure()

    plt.xlabel("Time (s)")
    plt.ylabel("Percentage along worm")

    plot0 = plt.imshow(
        body_curv_data.transpose(),
        interpolation="nearest",
        aspect="auto",
        cmap=cmap,
        vmin=min_curvature,
        vmax=max_curvature,
    )
    ax = plt.gca()
    info = "Propagation of curvature along body of worm (180=straight)"
    fig.canvas.manager.set_window_title(info)
    plt.title(info)

    xt = ax.get_xticks()
    time_ticks = [ts[int(ti)] if (ti >= 0 and ti < len(ts)) else 0 for ti in xt]
    # Fix the ticks before labelling them (keeping the current view limits)
    xlim = ax.get_xlim()
    ax.set_xticks(xt)
    ax.set_xlim(xlim)
    ax.set_xticklabels(time_ticks)

    fig.colorbar(plot0)

    if save_to:
        plt.savefig(save_to, bbox_inches="tight")

    return fig


def analyse_wcon_file(
    wcon_file_name,
    rate_to_plot=1,
    max_time_s=1e12,
    show_plots_already=False,
    plot_midlines=True,
    plot_speeds=True,
    plot_body_curvature=True,
    save_figure_midlines_to=None,
    save_figure_speeds_to=None,
    save_figure_curvature_to=None,
):
    print_(
        "Analyzing WCON file %s, with plotting rate %i" % (wcon_file_name, rate_to_plot)
    )

    wcon = SimpleWCON(wcon_file_name)
    ts, x, y = select_frames(wcon, rate_to_plot, max_time_s)

    print_(
        "Loaded: %s frames from %s, using %i frames"
        % (len(wcon.times), wcon_file_name, len(ts))
    )

    if plot_midlines:
        generate_midlines_plot(ts, x, y, save_to=save_figure_midlines_to)
    if plot_speeds:
        generate_speeds_plot(compute_speeds(ts, x, y), save_to=save_figure_speeds_to)
    if plot_body_curvature:
        generate_body_curvature_plot(
            ts, compute_body_curvature(ts, x, y), save_to=save_figure_curvature_to
        )

    if show_plots_already:
        plt.show()


def validate(wcon_file):
    if not wcon_file.endswith(".wcon"):
        print_("Cannot validate file: %s!! WCON file must end with .wcon!!" % wcon_file)
        return

    import json
    import jsonschema

    wcon_schema = "wcon_schema.json"

    if not os.path.isfile("wcon_schema.json"):
        print_(
            "Cannot validate file: %s!! WCON schema %s not found!!"
            % (wcon_file, wcon_schema)
        )
        return

    # The WCON schema
    with open(wcon_schema, "r") as wcon_schema_file:
        schema = json.loads(wcon_schema_file.read())

    # Our example WCON file
    with open(wcon_file, "r") as infile:
        serialized_data = infile.read()

    # Load the whole JSON file into a nested dict.
    w = json.loads(serialized_data)

    # Validate the raw file against the WCON schema
    jsonschema.validate(w, schema)

    print_("File %s is valid WCON!!" % wcon_file)


def transform(i, max_rad=0.03):
    return 1 + max_rad * math.sin((math.pi / 4) * (i) / 24.0)


def get_color_for_fract(fract):
    if fract < 0:
        fract = 0
    if fract > 1:
        fract = 1
    minCol = [0.4, 0, 0.9]
    maxCol = [1, 0.5, 0]
    return (
        minCol[0] + fract * (maxCol[0] - minCol[0]),
        minCol[1] + fract * (maxCol[1] - minCol[1]),
        minCol[2] + fract * (maxCol[2] - minCol[2]),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        wcon_file = sys.argv[1]
    else:
        wcon_file = "examples/simdata_test.wcon"

    validate(wcon_file)

    analyse_wcon_file(
        wcon_file,
        show_plots_already="-nogui" not in sys.argv,
    )
