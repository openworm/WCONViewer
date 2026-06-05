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


def load_view(wcon_file, show_head):
    """Load and parse the WCON file once and build the figure. The result is
    kept in session_state so the (potentially large) file is parsed only when
    the file or options change, not on every frame."""
    wv = WormView(show_head=show_head)
    wv.get_plot(make_args(wcon_file))
    return wv


st.title("WCON replay")

wcon_file = st.text_input("WCON file", value=DEFAULT_WCON)
show_head = st.checkbox("Show head", value=False)

# Load only when the file or options change; otherwise reuse the cached view.
key = (wcon_file, show_head)
if st.session_state.get("loaded_key") != key:
    try:
        with st.spinner(f"Loading {wcon_file}..."):
            st.session_state.wv = load_view(wcon_file, show_head)
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
c1, c2, c3, c4 = st.columns(4)
if c1.button("Play", use_container_width=True):
    st.session_state.running = True
if c2.button("Pause", use_container_width=True):
    st.session_state.running = False
if c3.button("Step", use_container_width=True):
    st.session_state.running = False
    st.session_state.t += 1
if c4.button("Reset", use_container_width=True):
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
        st.session_state.t += 1
        time.sleep(FRAME_DELAY)
        st.rerun()
