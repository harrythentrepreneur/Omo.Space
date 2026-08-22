#!/usr/bin/env python3
"""Verify the three clips: ffprobe streams + brightness + brand colors."""
import json
import os
import subprocess

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
PAL = {"pine": (23, 53, 44), "mint": (189, 239, 212),
       "orange": (255, 107, 61), "cream": (248, 247, 245)}
EXPECT = {"wordmark-omo.mp4": 5.5, "omo-audioreactive.mp4": 7.0,
          "omo-particles.mp4": 5.5}


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=index,codec_name,codec_type,width,height,"
         "avg_frame_rate,nb_frames,sample_rate,channels",
         "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def decode_frames(path):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    n = 640 * 360 * 3
    fi = 0
    while True:
        raw = p.stdout.read(n)
        if len(raw) < n:
            break
        yield np.frombuffer(raw, dtype=np.uint8).reshape(360, 640, 3), fi
        fi += 1
    p.stdout.close()
    p.wait()


def near_count(frame, rgb, tol=90):
    d = np.abs(frame.astype(np.int16) - np.array(rgb))
    return int(((d[..., 0] <= tol) & (d[..., 1] <= tol)
                & (d[..., 2] <= tol)).sum())


def main():
    ok = True
    for name, exp_dur in EXPECT.items():
        path = os.path.join(OUT, name)
        info = probe(path)
        dur = float(info["format"]["duration"])
        v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
        num, den = map(int, v["avg_frame_rate"].split("/"))
        fps = num / den
        nf = int(v.get("nb_frames", round(dur * fps)))
        dur_ok = abs(dur - exp_dur) < 0.15
        geom_ok = (v["width"], v["height"]) == (640, 360)
        fps_ok = abs(fps - 24.0) < 0.01
        print(f"\n=== {name} ===")
        print(f"  duration={dur:.3f}s (expect ~{exp_dur}) {'OK' if dur_ok else 'FAIL'}"
              f"  {v['width']}x{v['height']} {'OK' if geom_ok else 'FAIL'}"
              f"  fps={fps:.3f} {'OK' if fps_ok else 'FAIL'}"
              f"  frames={nf}  vcodec={v['codec_name']}")
        for a in [s for s in info["streams"] if s["codec_type"] == "audio"]:
            print(f"  audio: codec={a['codec_name']} sr={a.get('sample_rate')} "
                  f"ch={a.get('channels')}")
        means, counts, seen = [], {k: 0 for k in PAL}, {k: 0 for k in PAL}
        total = 0
        for frame, fi in decode_frames(path):
            total += 1
            means.append(frame.mean())
            if fi % 7 == 0:
                for k, rgb in PAL.items():
                    c = near_count(frame, rgb)
                    counts[k] += c
                    if c > 0:
                        seen[k] = 1
        mean = float(np.mean(means))
        bright_ok = mean > 8.0
        print(f"  frames-decoded={total} mean-brightness={mean:.1f} "
              f"(min {min(means):.1f}) {'OK>8' if bright_ok else 'FAIL'}")
        for k in PAL:
            flag = "OK" if seen[k] else "MISSING"
            if not seen[k]:
                ok = False
            print(f"  color {k:6s}: {flag}  (sampled px {counts[k]})")
        if not (dur_ok and geom_ok and fps_ok and bright_ok):
            ok = False
    print("\nRESULT:", "ALL PASS" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
