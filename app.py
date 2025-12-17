import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import time


max_x = 50
scale = 5

x = np.arange(0, max_x)

# from WormView import get_plot
# from WormView import parse_args

# args = parse_args()

print("Loading...")


def get_y(t):
    """Get the y values for the plot based on time t."""
    return scale * np.sin(
        2 * np.pi * (x / 50 + t / 5)
    )  # Example function, can be modified


def init():  # give a clean slate to start
    print("Initializing the plot...")
    fig, ax = plt.subplots()
    ax.set_ylim(-1.1 * scale, scale * 1.1)
    ax.set_xlim(-1, max_x + 1)

    (st.session_state.line,) = ax.plot(x, get_y(0), color="red")
    st.session_state.the_plot = st.pyplot(plt)


def animate(t):  # update the y values (every 1000ms)
    print("Animating the plot for time:", t)
    plt.close()
    fig, ax = plt.subplots()
    ax.set_ylim(-1.1 * scale, scale * 1.1)
    ax.set_xlim(-1, max_x + 1)
    (st.session_state.line,) = ax.plot(x, get_y(t), color="green", label=f"t={t:.2f}")
    plt.legend()
    # st.session_state.line.set_ydata(get_y(t))
    st.session_state.the_plot.pyplot(plt)


if "t" not in st.session_state:
    print("Initializing...")
    init()
    st.session_state.t = 0
    animate(0)  # initial animation to set the plot


if st.button("Step"):
    print("Stepping...")
    st.session_state.t += 0.1
    animate(st.session_state.t)

if st.button("Stop"):
    print("Stopping...")
    st.session_state.t += 0.1
    animate(st.session_state.t)

play = False

if st.button("Play"):
    play = True
    print("Playing...")
    for i in range(50):
        if not play:
            break
        animate(st.session_state.t)
        st.session_state.t += 0.1
        time.sleep(0.1)


st.markdown(f"Time {st.session_state.t}.")
