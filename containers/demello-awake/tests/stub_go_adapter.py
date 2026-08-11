"""Offline executable that mirrors the Go adapter's argv protocol."""

from __future__ import annotations

import argparse
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("-request", required=True)
parser.add_argument("-result", required=True)
parser.add_argument("-python", required=True)
parser.add_argument("-workflow", required=True)
args = parser.parse_args()
completed = subprocess.run(
    [args.python, args.workflow, "--request", args.request, "--result", args.result],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=False,
)
raise SystemExit(completed.returncode)

