#!/usr/bin/env python3
"""Shared bits for the Omo ASCII motion clips (ascii-video skill pipeline).

Reuses the exact pipeline patterns from the first proof clip
(research/social-assets/style-proofs/omo-ascii-motion/render-omo-ascii-motion.py):
  scene_fn -> tonemap (hue-preserving LUMA gain) -> FeedbackBuffer (screen
  blend) -> ffmpeg pipe. Never per-channel tonemap (it shifts orange to peach).

Brand hexes: cream #F8F7F5, pine #17352C, deep pine #142B23, mint #BDEFD4,
mint-deep #78CCA1, orange #FF6B3D, peach #FFB89D, muted #5F6F68.
"""
import math
import os
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

VW, VH, FPS = 640, 360, 24
FONT_PATH = "/System/Library/Fonts/Menlo.ttc"

# --- Omo brand palette (exact hexes from the style system) ---
PINE      = (23, 53, 44)      # #17352C  — ink
DEEP_PINE = (20, 43, 35)      # #142B23  — noir canvas
CREAM     = (248, 247, 245)   # #F8F7F5  — light
MINT      = (189, 239, 212)   # #BDEFD4  — field
MINT_DEEP = (120, 204, 161)   # #78CCA1  — terminal green
ORANGE    = (255, 107, 61)    # #FF6B3D  — the one accent
PEACH     = (255, 184, 157)   # #FFB89D  — warm highlight
MUTED     = (95, 111, 104)    # #5F6F68  — muted ink

RAMP = [MINT_DEEP, MINT_DEEP, MINT, MINT, CREAM]

PAL_BLOCKS = " \u2591\u2592\u2593\u2588"
PAL_DENSE  = " .:;+=xX$#@\u2588"
PAL_DOTS   = " \u00b7\u2218\u2022\u25cf\u2605"

_CHAR_POOL = set()
for _p in (PAL_BLOCKS, PAL_DENSE, PAL_DOTS):
    _CHAR_POOL.update(_p)
_CHAR_POOL.update(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .-:!?/|#$@*+='"
    "\u25cb\u2736\u2022\u2218\u00b7")
_CHAR_POOL.discard(" ")


class GridLayer:
    """Monospace character grid with pre-rasterized bitmaps (ascii-video skill)."""
    def __init__(self, font_size, vw=VW, vh=VH):
        self.vw, self.vh = vw, vh
        self.font = ImageFont.truetype(FONT_PATH, font_size)
        asc, desc = self.font.getmetrics()
        bbox = self.font.getbbox("M")
        self.cw = bbox[2] - bbox[0]
        self.ch = asc + desc          # CRITICAL: getmetrics, not textbbox (macOS PIL)
        self.cols = vw // self.cw
        self.rows = vh // self.ch
        self.ox = (vw - self.cols * self.cw) // 2
        self.oy = (vh - self.rows * self.ch) // 2
        cx, cy = self.cols / 2.0, self.rows / 2.0
        asp = self.cw / self.ch
        self.rr = np.arange(self.rows, dtype=np.float32)[:, None]
        self.cc = np.arange(self.cols, dtype=np.float32)[None, :]
        self.dx = self.cc - cx
        self.dy = (self.rr - cy) * asp
        self.dist = np.sqrt(self.dx ** 2 + self.dy ** 2)
        self.angle = np.arctan2(self.dy, self.dx)
        self.dx_n = (self.cc - cx) / max(self.cols, 1)
        self.dy_n = (self.rr - cy) / max(self.rows, 1) * asp
        self.dist_n = np.sqrt(self.dx_n ** 2 + self.dy_n ** 2)
        self.bm = {}
        self.blank = set()
        for c in _CHAR_POOL:
            img = Image.new("L", (self.cw, self.ch), 0)
            ImageDraw.Draw(img).text((0, 0), c, fill=255, font=self.font)
            b = np.array(img, dtype=np.float32) / 255.0
            self.bm[c] = b
            if b.max() < 0.05:
                self.blank.add(c)

    def safe_char(self, c, fallback="\u2022"):
        return fallback if c in self.blank else c

    def render(self, chars, colors, canvas=None):
        if canvas is None:
            canvas = np.zeros((self.vh, self.vw, 3), dtype=np.uint8)
        for row in range(self.rows):
            y = self.oy + row * self.ch
            if y + self.ch > self.vh:
                break
            for col in range(self.cols):
                c = chars[row, col]
                if c == " ":
                    continue
                x = self.ox + col * self.cw
                if x + self.cw > self.vw:
                    break
                a = self.bm[c]
                canvas[y:y + self.ch, x:x + self.cw] = np.maximum(
                    canvas[y:y + self.ch, x:x + self.cw],
                    (a[:, :, None] * colors[row, col]).astype(np.uint8))
        return canvas


def val2char(v, mask, pal):
    n = len(pal)
    idx = np.clip((v * n).astype(int), 0, n - 1)
    out = np.full(v.shape, " ", dtype="U1")
    for i, ch in enumerate(pal):
        out[mask & (idx == i)] = ch
    return out


def ramp_color(val, mask, ramp=RAMP):
    """Map value in [0,1] to a discrete brand ramp color."""
    n = len(ramp)
    idx = np.clip((val * n).astype(int), 0, n - 1)
    co = np.zeros((*val.shape, 3), dtype=np.uint8)
    for i, rgb in enumerate(ramp):
        m = mask & (idx == i)
        co[m] = rgb
    return co


def blend_canvas(base, top, opacity=0.6):
    af = base.astype(np.float32)
    bf = top.astype(np.float32)
    return np.clip(af * (1 - opacity) + bf * opacity, 0, 255).astype(np.uint8)


def tonemap(canvas, gamma=0.8):
    """Hue-preserving adaptive tonemap: one luma-based gain per pixel applied
    to ALL channels, so brand hexes (orange #FF6B3D, cream #F8F7F5) keep their
    exact hue. (Per-channel percentile stretching shifts orange toward peach.)"""
    f = canvas.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114])          # luma
    sub = lum[::4, ::4]
    lo = np.percentile(sub, 1)
    hi = np.percentile(sub, 99.5)
    if hi - lo < 10:
        hi = lo + 10
    target = np.clip((lum - lo) / (hi - lo), 0, 1) ** gamma * 255.0
    gain = np.where(lum > 2.0, target / np.maximum(lum, 1e-6), 0.0)
    out = f * gain[:, :, None]
    return np.clip(out, 0, 255).astype(np.uint8)


class FeedbackBuffer:
    """Screen-blended trails — screen never saturates a bright brand pixel to
    white, so brand hues survive feedback."""
    def __init__(self):
        self.buf = None

    def apply(self, canvas, decay=0.82, opacity=0.5):
        cur = canvas.astype(np.float32)
        if self.buf is None:
            self.buf = cur
            return canvas
        self.buf *= decay
        out = 255.0 - (255.0 - cur) * (255.0 - self.buf) / 255.0   # screen
        self.buf = out
        return blend_canvas(canvas, np.clip(out, 0, 255).astype(np.uint8), opacity)


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ease_out_cubic(t):
    t = np.clip(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def encode_mp4(frame_iter, path, n_frames, audio=None, fps=FPS):
    """Pipe raw RGB frames to ffmpeg. stderr goes to a FILE (never PIPE —
    a full stderr buffer deadlocks the pipe). Returns per-frame means."""
    err_log = os.path.join(os.path.dirname(path), "ffmpeg-encode.log")
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(fps), "-i", "pipe:0"]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [path]
    means = []
    with open(err_log, "w") as fh:
        pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=fh)
        for canvas in frame_iter:
            means.append(float(np.asarray(canvas).mean()))
            pipe.stdin.write(np.ascontiguousarray(canvas, dtype=np.uint8).tobytes())
        pipe.stdin.close()
        rc = pipe.wait()
    print(f"encode {os.path.basename(path)} rc={rc} frames={n_frames} "
          f"mean-brightness min/max={min(means):.1f}/{max(means):.1f}")
    return means


def load_audio_features(wav_path, fps=24):
    """Full audio analysis per ascii-video skill (inputs.md § Audio Analysis):
    mono 22050Hz decode -> per-frame FFT bands -> rms/flux -> beat + bdecay.
    All features normalized to [0,1]. Returns (feats, samples, hop, sr)."""
    from scipy import signal as _sig
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-ac", "1", "-ar", "22050",
                    "-sample_fmt", "s16", tmp],
                   capture_output=True, check=True)
    with wave.open(tmp) as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    os.unlink(tmp)
    hop = sr // fps
    n_frames = len(samples) // hop
    win = hop
    window = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    bands = {
        "sub":   (freqs >= 20)  & (freqs < 80),
        "bass":  (freqs >= 80)  & (freqs < 250),
        "lomid": (freqs >= 250) & (freqs < 500),
        "mid":   (freqs >= 500) & (freqs < 2000),
        "himid": (freqs >= 2000) & (freqs < 6000),
        "hi":    (freqs >= 6000),
    }
    feats = {k: np.zeros(n_frames, dtype=np.float32)
             for k in list(bands) + ["rms", "flux"]}
    prev_mag = None
    for fi in range(n_frames):
        chunk = samples[fi * hop: fi * hop + win]
        feats["rms"][fi] = float(np.sqrt(np.mean(chunk ** 2) + 1e-12))
        mag = np.abs(np.fft.rfft(chunk * window))
        for k, m in bands.items():
            if m.any():
                feats[k][fi] = float(np.sqrt(np.mean(mag[m] ** 2) + 1e-12))
        if prev_mag is not None:
            feats["flux"][fi] = float(np.sum(np.maximum(0.0, mag - prev_mag)))
        prev_mag = mag
    for k in feats:
        a = feats[k]
        lo, hi = a.min(), a.max()
        feats[k] = (a - lo) / (hi - lo + 1e-10)
    # Beat detection on the SUB band (kick energy), not flux — white-noise
    # hats keep flux high and random, which drowns kick onsets after
    # normalization. Sub peaks are clean for beat-driven material.
    fs = np.convolve(feats["sub"], np.ones(5) / 5, mode="same")
    peaks, _ = _sig.find_peaks(fs, height=0.2,
                               distance=max(3, fps // 4), prominence=0.08)
    beat = np.zeros(n_frames)
    bdecay = np.zeros(n_frames, dtype=np.float32)
    for p in peaks:
        beat[p] = 1.0
        for d in range(fps // 2):
            if p + d < n_frames:
                bdecay[p + d] = max(bdecay[p + d],
                                    math.exp(-d * 2.5 / (fps // 2)))
    feats["beat"] = beat
    feats["bdecay"] = bdecay
    return feats, samples, hop, sr
