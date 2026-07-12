#!/bin/bash
set -ex

ruff format *.py
ruff check *.py

python WormView.py -f examples/simdata.wcon -nogui -z # Test reloading WCON in Player
python WormView.py -f examples/worm_motion_log.wcon -nogui -g
python WormView.py -f examples/output_W2D.wcon -nogui -g -z

#python WormView.py -f examples/N2\ on\ food\ L_2009_09_15__11_01_01___8___1.wcon.zip -nogui
