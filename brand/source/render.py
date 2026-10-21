#!/usr/bin/env python3
"""Render PNG/ICO assets from the SVG pack with headless Chromium."""
import os, sys, base64
from PIL import Image
from playwright.sync_api import sync_playwright

root = sys.argv[1]
J = lambda *p: os.path.join(root, *p)

jobs = [
    # (svg, png, size)
    *[("symbol/carrick-symbol.svg", f"symbol/png/carrick-symbol-{s}.png", s) for s in (64, 128, 256, 512, 1024)],
    *[("symbol/carrick-symbol-on-dark.svg", f"symbol/png/carrick-symbol-on-dark-{s}.png", s) for s in (256, 512, 1024)],
    *[("symbol/carrick-symbol-mono-basalt.svg", f"symbol/png/carrick-symbol-mono-basalt-{s}.png", s) for s in (512,)],
    *[("symbol/carrick-symbol-mono-white.svg", f"symbol/png/carrick-symbol-mono-white-{s}.png", s) for s in (512,)],
    ("symbol/carrick-symbol-small.svg", "favicon/favicon-16.png", 16),
    ("symbol/carrick-symbol.svg", "favicon/favicon-32.png", 32),
    ("symbol/carrick-symbol.svg", "favicon/favicon-48.png", 48),
    ("avatar/carrick-avatar.svg", "favicon/apple-touch-icon.png", 180),
    ("avatar/carrick-app-icon-maskable.svg", "favicon/icon-192.png", 192),
    ("avatar/carrick-app-icon-maskable.svg", "favicon/icon-512.png", 512),
    ("avatar/carrick-avatar.svg", "avatar/carrick-avatar-500.png", 500),
    ("avatar/carrick-avatar.svg", "avatar/carrick-avatar-1024.png", 1024),
]
extra = [a for a in sys.argv[2:]]  # optional "svg:png:w:h" jobs
for e in extra:
    s, p, w, h = e.split(":")
    jobs.append((s, p, (int(w), int(h))))

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page()
    for src, dst, size in jobs:
        w, h = size if isinstance(size, tuple) else (size, size)
        data = base64.b64encode(open(J(src), "rb").read()).decode()
        pg.set_viewport_size({"width": w, "height": h})
        pg.set_content(f'<html><body style="margin:0;background:transparent">'
                       f'<img id="i" src="data:image/svg+xml;base64,{data}" width="{w}" height="{h}" style="display:block"></body></html>')
        pg.wait_for_function("document.getElementById('i').complete")
        os.makedirs(os.path.dirname(J(dst)), exist_ok=True)
        pg.locator("#i").screenshot(path=J(dst), omit_background=True)
    b.close()

ims = [Image.open(J(f"favicon/favicon-{s}.png")).convert("RGBA") for s in (16, 32, 48)]
ims[2].save(J("favicon/favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)], append_images=ims[:2])
print("rendered", len(jobs), "PNGs + favicon.ico")
