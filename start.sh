#!/bin/bash

cd /workspace/RunPodTools

pip install -r requirements.txt

python ./gallery.py /workspace/ComfyUI/output -u /workspace/ComfyUI/input -a /workspace/Archives
