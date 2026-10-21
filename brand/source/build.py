#!/usr/bin/env python3
"""Build the Carrick (Waterline) brand asset pack.

Usage: python3 build.py OUT_DIR [--wordmark-font PATH_TO_SchibstedGrotesk.ttf]

Without --wordmark-font the lockups are written as live-text SVG set in
Schibsted Grotesk 600 and no PNG lockups are rendered. With the font, the
wordmark is converted to outlines and PNG lockups and a social card are added.
"""
import argparse, base64, json, os, shutil
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

# ---- palette ------------------------------------------------------------
C = {
    "basalt": "#1B2A31",      # primary ink
    "lough": "#2A7C7C",       # sea accent on light
    "shallows": "#74B8B2",    # sea accent on dark
    "spray": "#E4EBE9",       # rock on dark / light tint
    "foam": "#F1F5F4",        # one-colour on dark
    "ground": "#F4F6F5",      # light page background
    "night": "#15232A",       # dark background
    "slate": "#4D5D63",       # secondary text on light
}

# ---- geometry -----------------------------------------------------------
# Master symbol, 64-unit grid. Visual bounds x4..60, y11..62; the square
# viewBox "0 4 64 64" centres it with ~4 units of padding each side.
ROCK = "M6 37 L13 23 L22 18 L30 18 L36 11 L48 11 L52 19 L56 37 Z"
WAVES = [(4, 42, 56), (12, 50, 40), (22, 58, 20)]  # x, y, width; height 4, rx 2
VB = "0 4 64 64"

# Small symbol, drawn on a 16-unit pixel grid for 16-24 px use.
ROCK_S = "M1 9 L3 5 L6 4 L8 4 L9 2 L12 2 L13 4 L15 9 Z"
WAVES_S = [(1, 11, 14), (4, 14, 8)]  # height 2


def sym_body(rock, sea):
    w = "".join(f'<rect x="{x}" y="{y}" width="{wd}" height="4" rx="2" fill="{sea}"/>' for x, y, wd in WAVES)
    return f'<path d="{ROCK}" fill="{rock}"/>{w}'


def sym_small_body(rock, sea):
    w = "".join(f'<rect x="{x}" y="{y}" width="{wd}" height="2" fill="{sea}"/>' for x, y, wd in WAVES_S)
    return f'<path d="{ROCK_S}" fill="{rock}"/>{w}'


def svg(viewbox, body, w=None, h=None, title="Carrick"):
    size = f' width="{w}" height="{h}"' if w else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}"{size} role="img" aria-label="{title}">'
            f'<title>{title}</title>{body}</svg>\n')


# ---- text to outlines ---------------------------------------------------
class Outliner:
    def __init__(self, path, wght=None):
        self.f = TTFont(path)
        if wght is not None and "fvar" in self.f:
            from fontTools.varLib import instancer
            self.f = instancer.instantiateVariableFont(self.f, {"wght": wght})
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self._class_kern = []
        self.kern = self._kern_pairs()

    def _kern_pairs(self):
        pairs = {}
        if "kern" in self.f:
            for t in self.f["kern"].kernTables:
                pairs.update(t.kernTable)
        if "GPOS" in self.f:
            gpos = self.f["GPOS"].table
            for li in gpos.LookupList.Lookup:
                lt = li.LookupType
                if lt == 9 and li.SubTable:
                    lt = li.SubTable[0].ExtensionLookupType
                if lt != 2:
                    continue
                for st in li.SubTable:
                    if getattr(st, "ExtSubTable", None) is not None:
                        st = st.ExtSubTable
                    fmt = getattr(st, "Format", None)
                    cov = st.Coverage.glyphs
                    if fmt == 1:
                        for i, ps in enumerate(st.PairSet):
                            for pvr in ps.PairValueRecord:
                                v = getattr(pvr.Value1, "XAdvance", 0) if pvr.Value1 else 0
                                if v:
                                    pairs.setdefault((cov[i], pvr.SecondGlyph), v)
                    elif fmt == 2:
                        self._class_kern.append((set(cov), st.ClassDef1.classDefs, st.ClassDef2.classDefs, st.Class1Record))
        return pairs

    _class_kern = None

    def kern_value(self, a, b):
        if (a, b) in self.kern:
            return self.kern[(a, b)]
        for cov, cd1, cd2, recs in self._class_kern:
            if a in cov:
                r = recs[cd1.get(a, 0)].Class2Record[cd2.get(b, 0)]
                v = getattr(r.Value1, "XAdvance", 0) if r.Value1 else 0
                if v:
                    return v
                return 0
        return 0

    def path(self, text, size, x, baseline, tracking_em=0.0):
        s = size / self.upm
        pen = SVGPathPen(self.gs)
        cx = x
        prev = None
        for ch in text:
            g = self.cmap[ord(ch)]
            if prev:
                cx += self.kern_value(prev, g) * s
            self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, baseline)))
            cx += self.gs[g].width * s + tracking_em * size
            prev = g
        return pen.getCommands(), cx - x - tracking_em * size


def live_text(text, size, x, baseline, fill, weight=600, tracking_em=-0.03, family="'Schibsted Grotesk', 'Inter', system-ui, sans-serif"):
    return (f'<text x="{x}" y="{baseline}" font-family="{family}" font-weight="{weight}" '
            f'font-size="{size}" letter-spacing="{tracking_em}em" fill="{fill}">{text}</text>')


# ---- builders -----------------------------------------------------------
def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def build(out, wordmark_font=None):
    # Clear only generated folders, so README.md and source/ survive a rebuild.
    for d in ("symbol", "lockup", "favicon", "avatar", "badge", "tokens"):
        if os.path.exists(os.path.join(out, d)):
            shutil.rmtree(os.path.join(out, d))
    files = {}

    def put(rel, content):
        write(os.path.join(out, rel), content)
        files[rel] = content

    # Symbols
    put("symbol/carrick-symbol.svg", svg(VB, sym_body(C["basalt"], C["lough"])))
    put("symbol/carrick-symbol-on-dark.svg", svg(VB, sym_body(C["spray"], C["shallows"])))
    put("symbol/carrick-symbol-mono-basalt.svg", svg(VB, sym_body(C["basalt"], C["basalt"])))
    put("symbol/carrick-symbol-mono-white.svg", svg(VB, sym_body("#FFFFFF", "#FFFFFF")))
    put("symbol/carrick-symbol-small.svg", svg("0 0 16 16", sym_small_body(C["basalt"], C["lough"])))
    put("symbol/carrick-symbol-small-on-dark.svg", svg("0 0 16 16", sym_small_body(C["spray"], C["shallows"])))
    put("symbol/carrick-symbol-small-mono-basalt.svg", svg("0 0 16 16", sym_small_body(C["basalt"], C["basalt"])))
    put("symbol/carrick-symbol-small-mono-white.svg", svg("0 0 16 16", sym_small_body("#FFFFFF", "#FFFFFF")))

    # Favicon (adapts to dark browser chrome)
    fav = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><style>'
           f'.r{{fill:{C["basalt"]}}}.w{{fill:{C["lough"]}}}'
           f'@media (prefers-color-scheme:dark){{.r{{fill:{C["spray"]}}}.w{{fill:{C["shallows"]}}}}}'
           f'</style><path class="r" d="{ROCK_S}"/>'
           + "".join(f'<rect class="w" x="{x}" y="{y}" width="{wd}" height="2"/>' for x, y, wd in WAVES_S)
           + "</svg>\n")
    put("favicon/favicon.svg", fav)

    # Avatar / app tile (basalt square, on-dark symbol at ~68%)
    def tile(bg, radius=0, pad=10.5):
        # 64-unit tile; symbol scaled into a centred square of side 64-2*pad
        side = 64 - 2 * pad
        s = side / 64
        rect = f'<rect width="64" height="64" rx="{radius}" fill="{bg}"/>'
        return svg("0 0 64 64", rect + f'<g transform="translate({pad} {pad}) scale({s}) translate(0 -4)">{sym_body(C["spray"], C["shallows"])}</g>')

    put("avatar/carrick-avatar.svg", tile(C["basalt"]))
    put("avatar/carrick-app-icon-maskable.svg", tile(C["basalt"], pad=16))

    # Lockups
    ol = Outliner(wordmark_font, 600) if wordmark_font else None
    ol_reg = Outliner(wordmark_font, 400) if wordmark_font else None
    H = 112            # symbol box
    GAP = 22
    TS = 92            # wordmark size
    BASE = 88          # baseline in lockup space

    def lockup(rock, sea, ink, sub=None, sub_ink=None):
        sym = f'<g transform="scale({H/64}) translate(0 -4)">{sym_body(rock, sea)}</g>'
        x = H + GAP
        if ol:
            d, w = ol.path("Carrick", TS, x, BASE, -0.03)
            text = f'<path d="{d}" fill="{ink}"/>'
            width = x + w
            if sub:
                d2, w2 = ol_reg.path(sub, TS, width + 0.26 * TS, BASE, -0.01)
                text += f'<path d="{d2}" fill="{sub_ink}"/>'
                width += 0.26 * TS + w2
        else:
            text = live_text("Carrick", TS, x, BASE, ink)
            width = x + 330
            if sub:
                text = (f'<text x="{x}" y="{BASE}" font-family="\'Schibsted Grotesk\', \'Inter\', system-ui, sans-serif" '
                        f'font-size="{TS}" fill="{ink}"><tspan font-weight="600" letter-spacing="-0.03em">Carrick</tspan>'
                        f'<tspan font-weight="400" letter-spacing="-0.01em" fill="{sub_ink}"> {sub}</tspan></text>')
                width = x + 720
        return svg(f"0 0 {round(width + 4)} {H}", sym + text, title="Carrick" + (f" {sub}" if sub else ""))

    put("lockup/carrick-lockup.svg", lockup(C["basalt"], C["lough"], C["basalt"]))
    put("lockup/carrick-lockup-on-dark.svg", lockup(C["spray"], C["shallows"], C["foam"]))
    put("lockup/carrick-lockup-mono-basalt.svg", lockup(C["basalt"], C["basalt"], C["basalt"]))
    put("lockup/carrick-lockup-mono-white.svg", lockup("#FFFFFF", "#FFFFFF", "#FFFFFF"))
    put("lockup/carrick-protocol-lockup.svg", lockup(C["basalt"], C["lough"], C["basalt"], "Protocol", C["slate"]))
    put("lockup/carrick-protocol-lockup-on-dark.svg", lockup(C["spray"], C["shallows"], C["foam"], "Protocol", "#A9B8BC"))

    # README badge: shields "flat" geometry, text outlined in DejaVu Sans
    # (the fallback shields.io itself renders with), so it is identical everywhere.
    dv = Outliner("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    def badge(label, msg, left_bg, right_bg, scale=1):
        icon_w = 12
        pad = 6
        dl, wl = dv.path(label, 11, 0, 0)
        dm, wm = dv.path(msg, 11, 0, 0)
        left_w = pad - 1 + icon_w + 4 + wl + pad
        right_w = pad + wm + pad
        W = left_w + right_w
        lx = pad - 1 + icon_w + 4
        body = (f'<clipPath id="c"><rect width="{W:.1f}" height="20" rx="3"/></clipPath><g clip-path="url(#c)">'
                f'<rect width="{left_w:.1f}" height="20" fill="{left_bg}"/>'
                f'<rect x="{left_w:.1f}" width="{right_w:.1f}" height="20" fill="{right_bg}"/></g>'
                f'<g transform="translate({pad-1} 4) scale(0.75)">{sym_small_body(C["foam"], C["shallows"])}</g>'
                f'<path transform="translate({lx:.1f} 14)" d="{dl}" fill="#FFFFFF"/>'
                f'<path transform="translate({left_w + pad:.1f} 14)" d="{dm}" fill="#FFFFFF"/>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*scale:.0f}" height="{20*scale}" viewBox="0 0 {W:.1f} 20" '
                f'role="img" aria-label="{label}: {msg}"><title>{label}: {msg}</title>{body}</svg>\n')

    put("badge/carrick-compatible.svg", badge("Carrick", "compatible", C["basalt"], C["lough"]))
    put("badge/carrick-compatible@2x.svg", badge("Carrick", "compatible", C["basalt"], C["lough"], scale=2))

    # Website badge (larger card). Title in brand face when outlined, else live text.
    def site_badge(dark):
        bg, border = (C["night"], "#2C3D45") if dark else ("#FFFFFF", "#C9D3D0")
        ink, sub = (C["foam"], "#A9B8BC") if dark else (C["basalt"], C["slate"])
        rock, sea = (C["spray"], C["shallows"]) if dark else (C["basalt"], C["lough"])
        sym = f'<g transform="translate(16 14) scale({40/64}) translate(0 -4)">{sym_body(rock, sea)}</g>'
        if ol:
            d, w = ol.path("Carrick compatible", 18, 70, 32, -0.01)
            title = f'<path d="{d}" fill="{ink}"/>'
        else:
            title = live_text("Carrick compatible", 18, 70, 32, ink, tracking_em=-0.01)
        if ol:
            ds, ws = ol_reg.path("Passes the conformance suite", 12, 70, 50)
            subtitle = f'<path d="{ds}" fill="{sub}"/>'
        else:
            subtitle = live_text("Passes the conformance suite", 12, 70, 50, sub, weight=400, tracking_em=0)
        body = (f'<rect x="0.5" y="0.5" width="279" height="67" rx="11.5" fill="{bg}" stroke="{border}"/>'
                f'{sym}{title}{subtitle}')
        return svg("0 0 280 68", body, w=280, h=68, title="Carrick compatible")

    put("badge/carrick-compatible-card.svg", site_badge(False))
    put("badge/carrick-compatible-card-dark.svg", site_badge(True))

    # Tokens
    tokens = {
        "color": {
            "basalt": {"value": C["basalt"], "use": "Primary ink: rock, wordmark, text on light"},
            "lough": {"value": C["lough"], "use": "Sea accent on light backgrounds; badge message field"},
            "shallows": {"value": C["shallows"], "use": "Sea accent on dark backgrounds"},
            "spray": {"value": C["spray"], "use": "Rock on dark backgrounds; light tint"},
            "foam": {"value": C["foam"], "use": "Wordmark and one-colour symbol on dark"},
            "ground": {"value": C["ground"], "use": "Light page background"},
            "night": {"value": C["night"], "use": "Dark page background"},
            "slate": {"value": C["slate"], "use": "Secondary text on light ('Protocol' in lockup)"},
        },
        "font": {
            "wordmark": {"family": "Schibsted Grotesk", "weight": 600, "letterSpacing": "-0.03em", "licence": "SIL OFL 1.1"},
            "text": {"family": "Schibsted Grotesk", "weights": [400, 500, 600]},
            "mono": {"family": "IBM Plex Mono", "weights": [400, 500], "licence": "SIL OFL 1.1"},
        },
        "symbol": {
            "minSizeFull": "24px", "smallVariantBelow": "24px",
            "clearSpace": "one quarter of the symbol's width on every side",
        },
    }
    put("tokens/carrick-tokens.json", json.dumps(tokens, indent=2) + "\n")
    css = ":root {\n" + "".join(f"  --carrick-{k}: {v['value']};\n" for k, v in tokens["color"].items()) + \
        "  --carrick-font-wordmark: 'Schibsted Grotesk', system-ui, sans-serif;\n" \
        "  --carrick-font-mono: 'IBM Plex Mono', ui-monospace, monospace;\n}\n"
    put("tokens/carrick-tokens.css", css)

    # shields.io logo data URI for people who prefer a hosted badge
    logo = svg("0 0 16 16", sym_small_body(C["foam"], C["shallows"]))
    files["_shields_logo_b64"] = base64.b64encode(logo.encode()).decode()
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--wordmark-font")
    a = ap.parse_args()
    f = build(a.out, a.wordmark_font)
    with open(os.path.join(a.out, ".shields-logo.b64"), "w") as fh:
        fh.write(f["_shields_logo_b64"])
    print("\n".join(sorted(k for k in f if not k.startswith("_"))))
