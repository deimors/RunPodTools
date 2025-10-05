#!/bin/bash

path="${2:-/workspace/ComfyUI}"

python receive.py -H "$1" \
-d "$path/input" \
-d "$path/output"
