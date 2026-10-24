#!/bin/bash
set -ex

ruff format wconviewer examples app.py 
ruff check wconviewer examples app.py

pip install .

cd examples/ && python generate.py -nogui && cd -
python -m wconviewer.Utils examples/sineworm.wcon -nogui

wconviewer examples/simdata.wcon -nogui -z # Test reloading WCON in Player
wconviewer examples/worm_motion_log.wcon -nogui -g
wconviewer examples/output_W2D.wcon -nogui -g -z

#wconviewer examples/N2\ on\ food\ L_2009_09_15__11_01_01___8___1.wcon.zip -nogui
