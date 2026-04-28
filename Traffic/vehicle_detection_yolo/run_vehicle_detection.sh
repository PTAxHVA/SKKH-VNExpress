#!/bin/zsh
set -euo pipefail

ROOT="/Users/tinngo/Documents/Traffic/vehicle_detection_yolo"
VENV_PY="$ROOT/.venv/bin/python"
YOLO_BIN="$ROOT/.venv/bin/yolo"
VIDEO="$ROOT/data/bellevue_ne8th_190824_short.mp4"
MODEL="$ROOT/models/yolo26s.pt"
PROJECT="$ROOT/runs"
NAME="vehicle_types"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing virtualenv at $ROOT/.venv"
  exit 1
fi

if [[ ! -f "$VIDEO" ]]; then
  echo "Missing input video at $VIDEO"
  exit 1
fi

"$YOLO_BIN" predict \
  model="$MODEL" \
  source="$VIDEO" \
  classes=2 \
  conf=0.12 \
  imgsz=1280 \
  device=cpu \
  project="$PROJECT" \
  name="$NAME" \
  exist_ok=True \
  save=True

echo "Annotated output: $PROJECT/$NAME"
