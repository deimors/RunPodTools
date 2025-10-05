#!/bin/bash

path="${2:-/workspace/ComfyUI}"

python receive.py -H "$1" \
-d "$path/models/loras" \
-d "$path/models/diffusion_models" \
-d "$path/models/text_encoders" \
-d "$path/user/default/workflows"