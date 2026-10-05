#!/bin/bash
set -ex

ruff format wconviewer app.py
ruff check wconviewer app.py

pip install .

wconviewer examples/simdata.wcon -nogui -z # Test reloading WCON in Player
wconviewer examples/worm_motion_log.wcon -nogui -g
wconviewer examples/output_W2D.wcon -nogui -g -z

#wconviewer examples/N2\ on\ food\ L_2009_09_15__11_01_01___8___1.wcon.zip -nogui
