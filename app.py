from WormView import WormView
from WormView import parse_args

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import time

max_x = 50
scale = 5

x = np.arange(0, max_x)

args = parse_args()
args.wcon_file = "/Users/padraig/neuroConstruct/osb/invertebrate/celegans/CE_locomotion/experiments/osc_sim_nml/output.wcon"
args.wcon_file = "/Users/padraig/neuroConstruct/osb/invertebrate/celegans/WCONViewer/examples/20_R#1_OW956#5_day5_CW_2014_03_03__10_05_43___8___5.wcon"
args.wcon_file = "examples/simdata.wcon"

print("Loading...")


def init():  # give a clean slate to start
    print(" -- Initializing the plot...")

    print("Done initializing.")


def animate(t):  # update the y values (every 1000ms)
    print("\n -- Animating the plot for time:", t)

    st.session_state.the_plot = None
    plt.close("all")

    wv = WormView()
    wv.reset()
    fig, ax = wv.get_plot(args)

    midline_plot, perimeter_plot = wv.update(t)

    st.session_state.line = fig
    # plt.legend()

    st.session_state.the_plot = st.pyplot(plt)


if "t" not in st.session_state:
    print("Initializing...")
    init()
    st.session_state.t = 0
    animate(0)  # initial animation to set the plot

if "running" not in st.session_state:
    st.session_state.running = False


st.markdown(f"Time {st.session_state.t}, running {st.session_state.running}.")


def step(n):
    print(f" - Stepping forward {n} steps...")
    st.session_state.t += n
    animate(st.session_state.t)


if st.button("Play"):
    play = True

    st.session_state.running = True

    for i in range(5):
        if not st.session_state.running:
            break
        step(1)
        time.sleep(0.1)
        st.rerun()

if st.session_state.running:
    print("(re)running")

    step(1)
    time.sleep(0.1)
    st.rerun()

if st.button("Step"):
    step(1)

if st.button("FFWD"):
    step(5)

if st.button("Stop"):
    print("Stopping...")
    st.session_state.running = False
