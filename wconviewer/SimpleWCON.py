import json
import re

import numpy as np

# Units (see "Units" in WCON_format.md), as factors to convert to seconds and mm.
# Abbreviations and full names have separate tables since they must not be mixed
# (e.g. "ms" and "milliseconds" are valid, but "msecond" is not)
_ABBREV_PREFIXES = {
    "c": 1e-2,
    "m": 1e-3,
    "u": 1e-6,
    "µ": 1e-6,  # micro symbol
    "μ": 1e-6,  # greek mu
    "n": 1e-9,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
}
_FULL_PREFIXES = {
    "centi": 1e-2,
    "milli": 1e-3,
    "micro": 1e-6,
    "nano": 1e-9,
    "kilo": 1e3,
    "mega": 1e6,
    "giga": 1e9,
}
_UNITS = {
    "time": {
        "abbrev": {"s": 1, "sec": 1, "min": 60, "h": 3600, "d": 86400},
        "full": {"second": 1, "minute": 60, "hour": 3600, "day": 86400},
    },
    "length": {
        "abbrev": {"m": 1e3, "in": 25.4},
        "full": {"metre": 1e3, "meter": 1e3, "inch": 25.4, "micron": 1e-3},
    },
}


def _single_unit_factor(word, kind):
    abbrevs = _UNITS[kind]["abbrev"]
    names = _UNITS[kind]["full"]

    for prefix, factor in [("", 1)] + list(_ABBREV_PREFIXES.items()):
        rest = word[len(prefix) :]
        if word.startswith(prefix) and rest in abbrevs:
            return factor * abbrevs[rest]

    for prefix, factor in [("", 1)] + list(_FULL_PREFIXES.items()):
        if not word.startswith(prefix):
            continue
        rest = word[len(prefix) :]
        # Full names may be pluralized (e.g. seconds, inches)
        for name in (rest, rest[:-1], rest[:-2]):
            if name in names and (name == rest or rest in (name + "s", name + "es")):
                return factor * names[name]

    return None


def get_unit_factor(unit, kind):
    """
    Factor to convert values in a WCON unit string (e.g. "ms", "um",
    "millimetres", "0.04*s", "in/72") to seconds (kind="time") or mm
    (kind="length"). Returns None if the unit is not recognised.
    """
    if not isinstance(unit, str):
        return None

    tokens = re.split(r"([*/])", unit.replace(" ", ""))
    factor = 1.0
    num_units = 0
    op = "*"
    for token in tokens:
        if token in ("*", "/"):
            op = token
            continue
        try:
            value = float(token)
        except ValueError:
            value = _single_unit_factor(token, kind)
            if value is None or op == "/":
                return None
            num_units += 1
        factor = factor * value if op == "*" else factor / value

    return factor if num_units == 1 else None


class SimpleWCON:
    def __init__(self, wcon_file, max_time=None):
        # max_time (in seconds): only load the timepoints up to this time
        # Check whether the filename ends with wcon.zip, and if so, unzip it, read the wcon file it contains and load the contents of that using json
        if wcon_file.endswith("wcon.zip"):
            import zipfile

            print(f"  === Loading WCON from zip file: {wcon_file}...")

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

        units = wcon.get("units", {})
        self.t_units = units.get("t", "Unknown units")
        self.x_units = units.get("x", "Unknown units")
        self.y_units = units.get("y", "Unknown units")
        print(
            f"   Time units: {self.t_units}, x units: {self.x_units}, y units: {self.y_units}"
        )

        def factor_for(key, kind, standard, default_key=None):
            # Factor to convert values of key to the standard units, and the
            # units the converted values are in (unchanged if not recognised)
            unit = units.get(key, units.get(default_key))
            factor = get_unit_factor(unit, kind)
            if factor is None:
                print(
                    f" - Warning: units for {key} ({unit}) not recognised, using as is"
                )
                return 1, unit
            return factor, standard

        t_factor, self.t_units_used = factor_for("t", "time", "s")
        x_factor, self.x_units_used = factor_for("x", "length", "mm")
        y_factor, self.y_units_used = factor_for("y", "length", "mm")

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

        if max_time is not None:
            # Values arrayed per timepoint have the same length as t (see
            # "Manipulation of custom data" in the spec), so keep the start of
            # each of those, up to the last time <= max_time
            times = np.array(record["t"], dtype=float) * t_factor
            after = np.nonzero(times > max_time)[0]
            num_times = after[0] if len(after) > 0 else len(times)
            if num_times == 0:
                raise ValueError(
                    f"No timepoints at or before max_time {max_time}s "
                    f"(first time: {times[0]}s)"
                )
            print(
                f" - Keeping {num_times}/{len(times)} timepoints, up to max_time {max_time}s"
            )
            record = {
                key: value[:num_times]
                if isinstance(value, list) and len(value) == len(times)
                else value
                for key, value in record.items()
            }

        print(" - Data records: %d" % len(data))
        print(" - Data keys: %s" % list(record.keys()))
        print(" - Data time: %s" % len(record["t"]))
        print(" - Data x: %s" % len(record["x"]))
        print(" - Data y: %s" % len(record["y"]))

        # Cast to float so that any None values in experimental wcon data
        # become nan (np.array([1.0, None], dtype=float) -> [1., nan]).
        self.times = np.array(record["t"], dtype=float) * t_factor

        self.x = np.array(record["x"], dtype=float).T * x_factor
        self.y = np.array(record["y"], dtype=float).T * y_factor

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
            ox_factor = factor_for("ox", "length", "mm", default_key="x")[0]
            oy_factor = factor_for("oy", "length", "mm", default_key="y")[0]
            self.ox = np.atleast_1d(np.array(self.ox, dtype=float)) * ox_factor
            self.oy = np.atleast_1d(np.array(self.oy, dtype=float)) * oy_factor
            self.x = self.x + self.ox
            self.y = self.y + self.oy

        # Centroid: optional, but if given it is per-timepoint, and often known
        # more accurately than the rest of the positions. Like the other
        # positions, it is relative to the origin, if one is given.
        if "cx" in record and "cy" in record:
            cx_factor = factor_for("cx", "length", "mm", default_key="x")[0]
            cy_factor = factor_for("cy", "length", "mm", default_key="y")[0]
            self.cx = np.array(record["cx"], dtype=float) * cx_factor
            self.cy = np.array(record["cy"], dtype=float) * cy_factor
            if self.ox is not None and self.oy is not None:
                self.cx = self.cx + self.ox
                self.cy = self.cy + self.oy
            print(f"Centroid given, cx shape: {self.cx.shape}")
        else:
            self.cx = None
            self.cy = None

        # Which end of the midline is the head: "L" (first point), "R" (last
        # point) or "?" (unknown). Either a local constant, or arrayed with one
        # value per timepoint. Assume "L" if not given.
        self.head = record.get("head", "L")

        print(f"Times: {self.times}, shape: {self.times.shape}")
        print(f"x: {self.x}, shape: {self.x.shape}")
        print(f"y: {self.y}, shape: {self.y.shape}")

        self.xmax = np.nanmax(self.x)
        self.xmin = np.nanmin(self.x)
        self.ymax = np.nanmax(self.y)
        self.ymin = np.nanmin(self.y)
        print(
            f"Range of time: {self.times[0]}{self.t_units_used}->{self.times[-1]}{self.t_units_used}; x range: {self.xmin}{self.x_units_used}->{self.xmax}{self.x_units_used}; y range: {self.ymin}{self.y_units_used}->{self.ymax}{self.y_units_used}"
        )

        if "px" in record:
            px_factor = factor_for("px", "length", "mm", default_key="x")[0]
            self.px = np.array(record["px"], dtype=float) * px_factor  # (n_t, n_perim)
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
            py_factor = factor_for("py", "length", "mm", default_key="y")[0]
            self.py = np.array(record["py"], dtype=float) * py_factor  # (n_t, n_perim)
            if self.oy is not None and self.py.ndim == 2:
                self.py = self.py + self.oy[:, None]
            print(
                f"py shape: {np.array(self.py).shape}, max: {np.nanmax(self.py)}, min: {np.nanmin(self.py)}"
            )
        else:
            self.py = None
