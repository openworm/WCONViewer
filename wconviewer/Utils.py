import math
import sys
import os
import numpy as np

from wconviewer.SimpleWCON import SimpleWCON


def dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def print_(msg):
    print("WCONViewer >>> %s" % (msg))


def analyse_wcon_file(
    wcon_file_name,
    rate_to_plot=1,
    max_time_s=1e12,
    plot=False,
    save_figure1_to=None,
    save_figure2_to=None,
    save_figure3_to=None,
    verbose=False,
):
    print_(
        "Analyzing WCON file %s, with plotting rate %i" % (wcon_file_name, rate_to_plot)
    )

    wcon = SimpleWCON(wcon_file_name)

    # Use the first frame, then every rate_to_plot-th frame (counting from 1)
    frame_indices = [
        fi
        for fi in range(len(wcon.times))
        if (fi == 0 or (fi + 1) % rate_to_plot == 0) and wcon.times[fi] <= max_time_s
    ]

    speed_units = "%s/%s" % (wcon.x_units_used, wcon.t_units)

    ts = [float(wcon.times[fi]) for fi in frame_indices]
    x = {t_s: wcon.x[:, fi] for t_s, fi in zip(ts, frame_indices)}
    y = {t_s: wcon.y[:, fi] for t_s, fi in zip(ts, frame_indices)}

    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111)

    num_plotted_frames = 0

    middle_points = []
    ave_points = []
    middle_point_speed_x = []
    middle_point_speed_y = []
    ave_point_speed_x = []
    ave_point_speed_y = []
    time_points = []

    xs0 = None
    ys0 = None
    for t_s, fi in zip(ts, frame_indices):
        points = len(x[t_s])
        middle_point = points / 2

        if verbose:
            print_(
                "Frame %i: at time: %s sec found %i points: [(%s,%s),...,(%s,%s)]"
                % (
                    fi,
                    t_s,
                    points,
                    x[t_s][0],
                    y[t_s][0],
                    x[t_s][points - 1],
                    y[t_s][points - 1],
                )
            )

        spacing = 0.05

        xs = []
        ys = []
        avx = 0
        avy = 0
        offset = num_plotted_frames * spacing

        for i in range(len(x[t_s])):
            # Swap x and y so worm moves "up"
            xs.append(y[t_s][i] + offset)
            ys.append(x[t_s][i])

            avx += xs[-1] - offset
            avy += ys[-1]

        if xs0 is None:
            xs0 = xs
        if ys0 is None:
            ys0 = ys

        avx = avx / points
        avy = avy / points

        if len(middle_points) > 0:
            dt = t_s - time_points[-1]
            middle_point_speed_x.append(
                (xs[int(middle_point)] - offset - middle_points[-1][0]) / dt
            )

            middle_point_speed_y.append(
                (ys[int(middle_point)] - middle_points[-1][1]) / dt
            )
            # dav = dist(avx, avy, ave_points[-1][0], ave_points[-1][1])

            ave_point_speed_x.append((avx - ave_points[-1][0]) / dt)
            ave_point_speed_y.append((avy - ave_points[-1][1]) / dt)

            if verbose:
                print_(
                    "  Speed of point"
                    + " %i: (%s,%s) -> (%s,%s): x %s%s, y %s%s"
                    % (
                        middle_point,
                        middle_points[-1][0],
                        middle_points[-1][1],
                        xs[int(middle_point)],
                        ys[int(middle_point)],
                        middle_point_speed_x[-1],
                        speed_units,
                        middle_point_speed_y[-1],
                        speed_units,
                    )
                )

            if verbose:
                print_(
                    "  Speed of av point "
                    + "(%s,%s) -> : (%s,%s): x %s%s, y %s%s"
                    % (
                        ave_points[-1][0],
                        ave_points[-1][1],
                        avx,
                        avy,
                        ave_point_speed_x[-1],
                        speed_units,
                        ave_point_speed_y[-1],
                        speed_units,
                    )
                )

        middle_points.append((xs[int(middle_point)] - offset, ys[int(middle_point)]))
        ave_points.append((avx, avy))
        time_points.append(t_s)

        if verbose:
            print_(
                "  Plot frame %i at %s s; frame %i: [(%s,%s),...#%i]"
                % (num_plotted_frames, t_s, fi, xs[0], ys[0], len(xs))
            )

        num_plotted_frames += 1

        lines = ax.plot(xs, ys, "-")
        if num_plotted_frames % 5 == 1:
            time_ = "%ss" % t_s if not t_s == int(t_s) else "%ss" % int(t_s)

            ax.text(50 + ((num_plotted_frames - 1) * spacing), 10, time_, fontsize=12)
        ax.plot(
            [xx + offset for xx in xs0],
            ys0,
            ":",
            color=lines[0].get_color(),
            linewidth=0.5,
        )

    body_curv_data = np.zeros((len(ts), len(xs) - 4))

    for ti in range(len(ts)):
        for i in range(len(y[ts[0]]))[2:-2]:
            x1 = x[ts[ti]][i - 2]
            xc = x[ts[ti]][i]
            x2 = x[ts[ti]][i + 2]

            y1 = y[ts[ti]][i - 2]
            yc = y[ts[ti]][i]
            y2 = y[ts[ti]][i + 2]

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

    info = "Loaded: %s frames from %s, using %i frames" % (
        len(wcon.times),
        wcon_file_name,
        len(ts),
    )
    print_(info)

    info = "Midline of worm through time (to %s seconds)" % time_points[-1]

    plt.xlabel("y direction (scaled)")
    plt.ylabel("x direction (%s)" % wcon.x_units_used)
    fig.canvas.manager.set_window_title(info)
    plt.title(info)

    if save_figure1_to:
        plt.savefig(save_figure1_to)

    fig = plt.figure()
    info = "Speed of worm in x (lateral) & y (along body) directions"
    fig.canvas.manager.set_window_title(info)
    plt.title(info)
    plt.xlabel("Time (s)")
    plt.ylabel("Speed")

    plt.plot(
        time_points[1:],
        ave_point_speed_x,
        "red",
        label="Speed in x of average of %i points" % points,
    )
    plt.plot(
        time_points[1:],
        middle_point_speed_x,
        "pink",
        label="Speed in x dir of point %i/%i" % (middle_point, points),
        linestyle="--",
    )
    plt.plot(
        time_points[1:],
        ave_point_speed_y,
        "blue",
        label="Speed in y of average of %i points" % points,
    )
    plt.plot(
        time_points[1:],
        middle_point_speed_y,
        "cyan",
        label="Speed in y dir of point %i/%i" % (middle_point, points),
        linestyle="--",
    )

    plt.plot([0, time_points[-1]], [0, 0], "grey", linestyle=":")

    plt.legend(loc=2, fontsize="x-small")

    if save_figure2_to:
        plt.savefig(save_figure2_to, bbox_inches="tight")

    fig = plt.figure()

    plt.xlabel("Time (s)")
    plt.ylabel("Percentage along worm")

    plot0 = plt.imshow(
        body_curv_data.transpose(), interpolation="nearest", aspect="auto"
    )
    ax = plt.gca()
    info = "Propagation of curvature along body of worm (180=straight)"
    fig.canvas.manager.set_window_title(info)
    plt.title(info)

    xt = ax.get_xticks()
    # print(xt)
    time_ticks = [
        time_points[int(ti)] if (ti >= 0 and ti < len(time_points)) else 0 for ti in xt
    ]
    # print(time_ticks)
    # Fix the ticks before labelling them (keeping the current view limits)
    xlim = ax.get_xlim()
    ax.set_xticks(xt)
    ax.set_xlim(xlim)
    ax.set_xticklabels(time_ticks)

    fig.colorbar(plot0)

    if save_figure3_to:
        plt.savefig(save_figure3_to, bbox_inches="tight")

    if plot:
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
        plot="-nogui" not in sys.argv,
        verbose=False,
    )
