#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from traffic_ai_demo import TraceFrame, export_video


def _extract_payload_from_html(html_text: str) -> dict[str, object]:
    start_marker = "const payload = "
    end_marker = ";\n    const fixedFrames = payload.fixed_frames;"
    start_index = html_text.find(start_marker)
    if start_index < 0:
        raise RuntimeError("Could not find embedded replay payload in the HTML file.")
    start_index += len(start_marker)
    end_index = html_text.find(end_marker, start_index)
    if end_index < 0:
        raise RuntimeError("Could not find the end of the embedded replay payload in the HTML file.")
    return json.loads(html_text[start_index:end_index])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the embedded SUMO replay HTML into an MP4 file.")
    parser.add_argument(
        "--input-html",
        default="sumo_visualization.html",
        help="Path to the replay HTML that already contains the embedded payload.",
    )
    parser.add_argument(
        "--output-mp4",
        default="sumo_visualization.mp4",
        help="Path to the output MP4 file.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Frames per second for the rendered MP4.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    html_path = Path(args.input_html)
    payload = _extract_payload_from_html(html_path.read_text(encoding="utf-8"))
    fixed_frames = [TraceFrame(**frame_dict) for frame_dict in payload["fixed_frames"]]
    ai_frames = [TraceFrame(**frame_dict) for frame_dict in payload["ai_frames"]]
    video_path = export_video(
        fixed_frames,
        ai_frames,
        payload["metrics"],
        output_path=args.output_mp4,
        fps=args.fps,
    )
    print(f"MP4 written to: {video_path.resolve()}")


if __name__ == "__main__":
    main()
