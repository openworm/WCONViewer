import argparse
import time

import streamlit as st

from WormView import WormView

DEFAULT_WCON = "examples/simdata.wcon"
FRAME_DELAY = 0.1  # seconds between frames while playing


def make_args(wcon_file):
    """Build the minimal config object that WormView.get_plot expects, without
    going through the CLI argparse (which would read Streamlit's sys.argv)."""
    return argparse.Namespace(
        wcon_file=wcon_file,
        ignore_wcon_perimeter=False,
        suppress_automatic_generation=False,
        minor_radius=40e-3,
    )


def load_view(wcon_file, show_head, show_grid=False, zoom_to_worm=False):
    """Load and parse the WCON file once and build the figure. The result is
    kept in session_state so the (potentially large) file is parsed only when
    the file or options change, not on every frame."""
    wv = WormView(show_head=show_head, show_grid=show_grid, zoom_to_worm=zoom_to_worm)
    wv.get_plot(make_args(wcon_file))
    return wv


st.title("WCON replay")

wcon_file = st.text_input("WCON file", value=DEFAULT_WCON)
show_head = st.checkbox("Show head", value=False)
show_grid = st.checkbox("Show grid", value=False)
zoom_to_worm = st.checkbox("Zoom to worm", value=False)

# Load only when the file or options change; otherwise reuse the cached view.
key = (wcon_file, show_head, show_grid, zoom_to_worm)
if st.session_state.get("loaded_key") != key:
    try:
        with st.spinner(f"Loading {wcon_file}..."):
            st.session_state.wv = load_view(
                wcon_file, show_head, show_grid, zoom_to_worm
            )
    except Exception as e:
        st.error(f"Could not load '{wcon_file}': {e}")
        st.stop()
    st.session_state.loaded_key = key
    st.session_state.t = 0
    st.session_state.running = False

wv = st.session_state.wv
n_frames = len(wv.wcon.times)

st.session_state.setdefault("t", 0)
st.session_state.setdefault("running", False)

# --- Controls (rendered before any rerun so they are always clickable) ---
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

# one back
if c1.button("$\u29cf$", use_container_width=True):
    st.session_state.running = False
    st.session_state.t -= 1

# play backwards
if c2.button("$\u25c0$", use_container_width=True):
    st.session_state.running = True
    st.session_state.t -= 1
    st.session_state.step = -1

# stop
if c3.button("$\u25a0$", use_container_width=True):
    st.session_state.running = False

# play
if c4.button("$\u25b6$", use_container_width=True):
    st.session_state.running = True
    st.session_state.t += 1
    st.session_state.step = 1

# fast forward
if c5.button("$\u25b6\u25b6$", use_container_width=True):
    st.session_state.running = True
    st.session_state.t += 10
    st.session_state.step = 10

# step forward
if c6.button("$\u29d0$", use_container_width=True):
    st.session_state.running = False
    st.session_state.t += 1

if c7.button("Reset", use_container_width=True):
    st.session_state.running = False
    st.session_state.t = 0

# Keep the frame index within range.
st.session_state.t = max(0, min(st.session_state.t, n_frames - 1))
ti = st.session_state.t

# --- Draw the current frame on the (reused) figure ---
wv.update(ti)
st.pyplot(wv.fig, clear_figure=False)

t_val = wv.wcon.times[ti]
st.caption(
    f"Frame {ti + 1} / {n_frames} — t = {t_val} {wv.wcon.t_units} "
    f"({'playing' if st.session_state.running else 'paused'})"
)
st.progress((ti + 1) / n_frames if n_frames else 0.0)

# --- Auto-advance while playing; stop automatically at the last frame ---
if st.session_state.running:
    if ti >= n_frames - 1:
        st.session_state.running = False  # reached the end
    else:
        st.session_state.t += st.session_state.step
        time.sleep(FRAME_DELAY)
        st.rerun()
