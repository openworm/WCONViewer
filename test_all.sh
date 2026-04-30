#!/bin/bash
set -ex

ruff format *.py
ruff check *.py

python WormView.py -f examples/simdata.wcon -nogui # Test reloading WCON in Player
python WormView.py -f examples/worm_motion_log.wcon -nogui
python WormView.py -f examples/output_W2D.wcon -nogui
