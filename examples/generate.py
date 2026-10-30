from matplotlib import pyplot as plt
import math
import numpy as np
import sys
import json

#  Some example data
dur = 2
dt = 0.01
period = 1


def generate_worm(amp, phase, num_points, length=1, x0=0, y0=0):
    xs = [float(x) for x in np.linspace(x0 + length, x0, num_points)]
    ys = [y0 + (amp * math.sin(2 * math.pi * x / length + phase)) for x in xs]
    return xs, ys


def generate_worm_sine(amp, phase, num_points, length=1, x0=0, y0=0):
    # Like generate_worm (head at x0 + length, tail at x0, same phase convention),
    # but the *curvature* is a pure sine along the body, so the interior angle
    # plot is a pure sine. `length` is the arc length, so the x extent is a bit
    # less than `length`. For small amp, amp is roughly the y amplitude.
    k = 2 * math.pi / length
    ds = length / (num_points - 1)
    # Heading of each segment (pi = pointing in -x, head to tail); the heading is
    # a cosine along the body, so its rate of change (curvature) is a sine.
    s_mid = (np.arange(num_points - 1) + 0.5) * ds
    headings = math.pi + amp * k * np.cos(k * s_mid + phase)
    xs = x0 + length + np.concatenate(([0], np.cumsum(ds * np.cos(headings))))
    ys = y0 + np.concatenate(([0], np.cumsum(ds * np.sin(headings))))
    return list(xs), list(ys)


num_points = 50


def local_curvature_degrees(xs, ys):
    # Interior angle (degrees) at each point i, between the lines to points i-1
    # and i+1. 180 = locally straight; below 180 = left turn (anticlockwise),
    # above 180 = right turn (clockwise), travelling from head to tail.
    xs = np.asarray(xs)
    ys = np.asarray(ys)
    headings = np.arctan2(np.diff(ys), np.diff(xs))
    turn = np.diff(headings)
    turn = (turn + np.pi) % (2 * np.pi) - np.pi  # wrap to [-pi, pi)
    return 180 - np.degrees(turn)  # length num_points - 2, for points 1..n-2


fig_body, ax_body = plt.subplots()
ax_body.set_aspect("equal", adjustable="box")

fig_angle, ax_angle = plt.subplots()
ax_angle.invert_xaxis()  # head (index 0) on the right, tail on the left, as in the body plot
ax_angle.set_xlabel("Point index along body (0 = head)")
ax_angle.set_ylabel("Interior angle (degrees, 180 = straight)")


def plot_one(xs, ys, color="g"):
    # Body shape on the body figure, interior angle along the body on the angle figure
    ax_body.plot(
        xs, ys, marker="o", linestyle="-", color=color, markersize=1, linewidth=0.5
    )
    ax_body.plot(xs[0], ys[0], marker="o", color="red", markersize=2)

    curv = local_curvature_degrees(xs, ys)
    ax_angle.plot(
        range(1, len(xs) - 1),
        curv,
        marker="o",
        linestyle="-",
        color=color,
        markersize=2,
        linewidth=0.5,
    )


xs, ys = generate_worm(0.1, 0, num_points=num_points, length=1, x0=0, y0=2)

plot_one(xs, ys, color="g")

xs1, ys1 = generate_worm(0.2, 0, num_points=num_points, length=1, x0=2, y0=1)
plot_one(xs1, ys1, color="b")

xs3, ys3 = generate_worm_sine(0.2, 0, num_points=num_points, length=1, x0=2, y0=2)
plot_one(xs3, ys3, color="m")

xs2, ys2 = generate_worm(0, 0, num_points=5, length=1, x0=0, y0=0)
ys2[0] = 0.25
# ys2[-1] = -0.25
print("Generated worm 2: ", xs2, ys2)
plot_one(xs2, ys2, color="orange")

wcon = {
    "metadata": {"who": "generate.py script in WCONViewer", "protocol": "Python..."},
    "units": {"t": "s", "x": "mm", "y": "mm"},
    "comment": "Just a test",
}

dd = {"id": "0", "t": [], "x": [], "y": []}
wcon["data"] = [dd]

for t in np.arange(0, dur, dt):
    dd["t"].append(t)

    t_start = 0.5
    scale = 0 if t < t_start else t - t_start

    xs, ys = generate_worm(
        0.1 * scale, 0, num_points=num_points, length=1, x0=t * scale, y0=0
    )
    dd["x"].append(xs)
    dd["y"].append(ys)


with open("sineworm.wcon", "w") as f:
    json.dump(wcon, f, indent=4)

if "-nogui" not in sys.argv:
    plt.show()
