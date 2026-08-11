"""Provider-mocked workflow process: deterministic files, zero paid calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--request", required=True)
parser.add_argument("--result", required=True)
args = parser.parse_args()
request = json.loads(Path(args.request).read_text(encoding="utf-8"))
run_id = request["run_id"]
artifact_dir = Path(request["run_artifact_dir"])
artifact_dir.mkdir(parents=True, exist_ok=True)
(artifact_dir / "diagnostic.json").write_text('{"phase":"generate"}\n', encoding="utf-8")
# Give the Modal-side process monitor enough time to observe a real file-based
# checkpoint without coupling the protocol to stdout/stderr.
time.sleep(0.3)
video = artifact_dir / "video.mp4"
contact = artifact_dir / "contact-sheet.jpg"
video.write_bytes(b"offline-h264-aac-fixture")
contact.write_bytes(b"offline-jpeg-contact-sheet")


def artifact(path: Path, name: str) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "key": f"runs/{run_id}/{name}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


result = {
    "run_id": run_id,
    "status": "completed",
    "artifacts": {
        "video": artifact(video, "video.mp4"),
        "contact_sheet": artifact(contact, "contact-sheet.jpg"),
    },
    "frames_used": {"generated": 2, "semantic": 15, "output": 150},
    "usage": {
        "provider_costs_usd": {
            "transcription": 0.0,
            "director": 0.0,
            "image_generation": 0.0,
        },
        "provider_costs_complete": True,
        "modal_cpu_core_seconds": 0.0,
        "modal_memory_gib_seconds": 0.0,
        "artifact_storage_usd": 0.0,
        "artifact_egress_usd": 0.0,
    },
    "pricing_history": {
        "static_estimate_usd": 0.02,
        "successful_delivered_usd": [],
        "delivered_7d_usd": 0.0,
        "delivered_30d_usd": 0.0,
    },
    "media": {
        "duration_seconds": 5.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "width": 1080,
        "height": 1920,
        "fps": 30,
    },
    "generation_provider": "procedural-fallback",
}
Path(args.result).write_text(json.dumps(result), encoding="utf-8")
