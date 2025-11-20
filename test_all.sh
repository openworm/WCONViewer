#!/bin/bash
set -ex

ruff format *.py
ruff check *.py

python WormView.py -f examples/simdata.wcon -nogui # Test reloading WCON in Player
