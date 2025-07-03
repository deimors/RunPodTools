#!/bin/bash

python receive.py -H "$1" \
-d /workspace/ComfyUI/models/loras \
-d /workspace/ComfyUI/models/diffusion_models \
-d /workspace/ComfyUI/models/text_encoders \
-d /workspace/ComfyUI/user/default/workflows