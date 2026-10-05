#!/bin/bash
set -ex

no_cache_flag=""
if [[ ($# -eq 1) && ($1 == '-r') ]]; then
    no_cache_flag="--no-cache"
fi

# Set the platform flag if we're on ARM
arch=$(uname -m)
if [[ "$arch" == "arm64" || "$arch" == "aarch64" ]]; then
    platform_flag="--platform linux/amd64"
else
    platform_flag=""
fi


docker build $platform_flag -t wconviewer $no_cache_flag .
