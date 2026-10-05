import json

import numpy as np


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
