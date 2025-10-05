#!/bin/bash

path="${2:-/workspace/ComfyUI}"

python serve.py \
-d "$path/input" \
-d "$path/output"