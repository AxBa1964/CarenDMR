"""CarenDMR-Tastenfeld – parametrisches CAD-Modell (CadQuery).

Erzeugt STEP (für CAD-Programme) und STL (für den Drucker) aller Teile:

    python tastenfeld.py            → Dateien in ./out
    python tastenfeld.py --out DIR

Alle Maße in mm. Die Parameter stehen gesammelt in ``Params``; nach dem
Nachmessen von Lautsprecher und Vibrationsmodul hier anpassen.

Koordinaten: X = Breite (links → rechts), Y = Tiefe (vorne → hinten),
Z = Höhe. Caren sitzt vorne (Y = 0).
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq


@dataclass(frozen=True)
class Params:
    # Gehäuse
    wall: float = 2.5
    base: float = 2.5
    rim: float = 3.0                 # Auflagekante für Platte und Deckel
    width: float = 145.0             # außen
    h_front: float = 20.0            # Oberkante Tastenplatte vorne
    angle: float = 7.0               # Neigung der Tastenplatte
    plate_len: float = 112.0         # Tastenplatte entlang der Schräge
    plate_t: float = 1.5             # Plattenstärke (Gateron-Klipse brauchen 1,5)
    pod_depth: float = 45.0          # Podest Tiefe (außen, ohne Rückwand)
    h_pod: float = 52.0              # Podest Höhe
    lid_t: float = 2.5               # Podestdeckel
    fit: float = 0.2                 # Spiel je Seite für Einlegeteile
    # Tasten
    unit: float = 19.05
    cut: float = 14.0                # Ausschnitt; Probestreifen 27.11.2026: 14,0 passt
    cap: float = 18.0
    row_first: float = 17.0          # erste Reihe: Abstand Mitte ↔ Hinterkante Platte
    ptt_width: float = 57.15
    ptt_switch_gap: float = 38.0
    # Schrauben / Einschmelzmuttern M3
    insert_d: float = 4.0
    insert_depth: float = 6.0
    dome_d: float = 7.5
    screw_clear: float = 3.4
    # Kabel
    cable_d: float = 6.0
    # Lautsprecher (vorläufig, laut Händler ca. 70 × 30 × 15)
    grille_hole: float = 2.0
    grille_pitch: float = 4.0
    grille_nx: int = 13
    grille_ny: int = 5
    # Füße
    foot_d: float = 12.0
    foot_h: float = 3.0
    foot_recess: float = 1.0

    # abgeleitete Größen
    @property
    def tan(self) -> float:
        return math.tan(math.radians(self.angle))

    @property
    def cos(self) -> float:
        return math.cos(math.radians(self.angle))

    @property
    def plate_y1(self) -> float:          # Plattenende hinten (Projektion)
        return self.wall + self.plate_len * self.cos

    @property
    def h_back(self) -> float:            # Oberkante Platte hinten
        return self.top_z(self.plate_y1)

    @property
    def depth(self) -> float:             # außen
        return self.plate_y1 + self.pod_depth + self.wall

    @property
    def plate_w(self) -> float:
        return self.width - 2 * self.wall

    def top_z(self, y: float) -> float:
        """Oberkante der Tastenplatte bei Tiefe y."""
        return self.h_front + y * self.tan

    # Tastenpositionen in Plattenkoordinaten (u = quer, v = entlang Schräge ab Vorderkante)
    def key_columns(self) -> list[float]:
        u = self.unit
        cols = [0, u, 2.5 * u, 3.5 * u, 5 * u]
        off = (self.plate_w - (cols[-1] + self.cap)) / 2 + self.cap / 2
        return [off + c for c in cols]

    def key_rows(self) -> list[float]:
        u = self.unit
        back = [self.row_first + i * 1.25 * u for i in range(4)]
        return [self.plate_len - d for d in back]       # v ab Vorderkante

    def keys(self) -> list[tuple[str, float, float, str]]:
        c, r = self.key_columns(), self.key_rows()
        return [
            ("favorit_1", c[0], r[0], "braille1"), ("favorit_2", c[1], r[0], "braille2"),
            ("favorit_3", c[2], r[0], "braille3"), ("favorit_4", c[3], r[0], "braille4"),
            ("beenden", c[4], r[0], "mulde"),
            ("tg_zurueck", c[0], r[1], "links"), ("tg_vor", c[1], r[1], "rechts"),
            ("leiser", c[2], r[1], "minus"), ("lauter", c[3], r[1], "plus"),
            ("verbinden", c[0], r[2], "noppe"), ("trennen", c[3], r[2], "kreuz"),
        ]

    def ptt_switches(self) -> list[tuple[float, float]]:
        v = self.key_rows()[3]
        mid = self.plate_w / 2
        g = self.ptt_switch_gap / 2
        return [(mid - g, v), (mid + g, v)]

    def plate_screws(self) -> list[tuple[float, float]]:
        """Schraubenlöcher in Plattenkoordinaten (u, v)."""
        return [(6.0, 6.0), (self.plate_w - 6.0, 6.0),
                (6.0, self.plate_len - 5.0), (self.plate_w - 6.0, self.plate_len - 5.0)]

    def pod_inner(self) -> tuple[float, float, float, float]:
        """Innenraum des Podests (x0, x1, y0, y1)."""
        return (self.wall, self.width - self.wall,
                self.plate_y1 + self.wall, self.depth - self.wall)

    def lid_screws(self) -> list[tuple[float, float]]:
        x0, x1, y0, y1 = self.pod_inner()
        return [(x0 + 5, y0 + 5), (x1 - 5, y0 + 5), (x0 + 5, y1 - 5), (x1 - 5, y1 - 5)]

    def pico_xy(self) -> tuple[float, float]:
        """Mitte der USB-Kante des Pico (hinten links)."""
        return (self.wall + 14.0 + 10.5, self.depth - self.wall - 1.0)


# ---------------------------------------------------------------- Unterteil

def _profile_solid(p: Params, pts: list[tuple[float, float]], x0: float, x1: float) -> cq.Workplane:
    """Polygon in der YZ-Ebene, von x0 bis x1 extrudiert."""
    return (cq.Workplane("YZ", origin=(x0, 0, 0)).polyline(pts).close().extrude(x1 - x0))


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _plate_to_world(p: Params, u: float, v: float) -> tuple[float, float]:
    return (p.wall + u, p.wall + v * p.cos)


def housing(p: Params) -> cq.Workplane:
    w, d = p.width, p.depth
    y1 = p.plate_y1
    outer = _profile_solid(p, [(0, 0), (0, p.h_front), (y1, p.h_back), (y1, p.h_pod),
                               (d, p.h_pod), (d, 0)], 0, w)
    body = outer.cut(_box(p.wall + p.rim, w - p.wall - p.rim,
                          p.wall + p.rim, d - p.wall - p.rim, p.base, 200))
    # Podest-Vorderwand mit Auflage für den Deckel (unten offen für Kabel)
    z_low = p.h_back - p.plate_t - 6
    body = body.union(_box(p.wall, w - p.wall, y1 - p.rim, y1 + p.wall + p.rim, z_low, p.h_pod))
    # Dome für Einschmelzmuttern
    for u, v in p.plate_screws():
        x, y = _plate_to_world(p, u, v)
        body = body.union(cq.Workplane("XY").circle(p.dome_d / 2).extrude(80).translate((x, y, p.base)))
    for x, y in p.lid_screws():
        body = body.union(cq.Workplane("XY").circle(p.dome_d / 2).extrude(80).translate((x, y, p.base)))
    # Sitz der schrägen Tastenplatte
    seat_drop = p.plate_t / p.cos
    seat = _profile_solid(p, [(p.wall, p.top_z(p.wall) - seat_drop), (y1, p.h_back - seat_drop),
                              (y1, 200), (p.wall, 200)], p.wall, w - p.wall)
    body = body.cut(seat)
    # über der Platte nichts stehen lassen (Dome, Wand)
    body = body.cut(_profile_solid(p, [(-1, p.top_z(-1)), (y1, p.h_back), (y1, 200), (-1, 200)], -1, w + 1))
    # Sitz des Podestdeckels
    x0, x1, py0, py1 = p.pod_inner()
    body = body.cut(_box(x0, x1, py0, py1, p.h_pod - p.lid_t, 200))
    # Löcher für Einschmelzmuttern
    for u, v in p.plate_screws():
        x, y = _plate_to_world(p, u, v)
        z = p.top_z(y) - seat_drop
        body = body.cut(cq.Workplane("XY").circle(p.insert_d / 2).extrude(p.insert_depth + 1)
                        .translate((x, y, z - p.insert_depth)))
    for x, y in p.lid_screws():
        z = p.h_pod - p.lid_t
        body = body.cut(cq.Workplane("XY").circle(p.insert_d / 2).extrude(p.insert_depth + 1)
                        .translate((x, y, z - p.insert_depth)))
    # Kabelausgang hinten
    cx, _ = p.pico_xy()
    body = body.cut(cq.Workplane("XZ", origin=(cx, d + 1, p.base + 8)).circle(p.cable_d / 2).extrude(p.wall + 2))
    # Zugentlastung: zwei Pfosten für einen Kabelbinder
    for dx in (-7, 7):
        body = body.union(_box(cx + dx - 2, cx + dx + 2, d - p.wall - 14, d - p.wall - 10, p.base, p.base + 10))
    # Vertiefungen für TPU-Füße
    for x, y in ((12, 12), (w - 12, 12), (12, d - 12), (w - 12, d - 12)):
        body = body.cut(cq.Workplane("XY").circle(p.foot_d / 2 + 0.3).extrude(p.foot_recess)
                        .translate((x, y, 0)))
    return body


# ---------------------------------------------------------------- Tastenplatte

def key_plate(p: Params, cut: float | None = None) -> cq.Workplane:
    """Flach liegend (Oberseite +Z), u = X, v = Y."""
    cut = p.cut if cut is None else cut
    w = p.plate_w - 2 * p.fit
    l = p.plate_len - 2 * p.fit
    plate = cq.Workplane("XY").box(w, l, p.plate_t, centered=False).translate((p.fit, p.fit, 0))
    holes = [(u, v) for _, u, v, _ in p.keys()] + p.ptt_switches()
    for u, v in holes:
        plate = plate.cut(_box(u - cut / 2, u + cut / 2, v - cut / 2, v + cut / 2, -1, p.plate_t + 1))
    for u, v in p.plate_screws():
        plate = plate.cut(cq.Workplane("XY").circle(p.screw_clear / 2).extrude(p.plate_t + 2)
                          .translate((u, v, -1)))
    # Orientierungsnoppe vorne Mitte
    nub = cq.Workplane("XY").sphere(1.6).translate((p.plate_w / 2, 4.5, p.plate_t))
    plate = plate.union(nub.intersect(_box(-1, 300, -1, 300, p.plate_t, 10)))
    return plate


# ---------------------------------------------------------------- Podestdeckel

def lid(p: Params) -> cq.Workplane:
    x0, x1, y0, y1 = p.pod_inner()
    w, l = x1 - x0 - 2 * p.fit, y1 - y0 - 2 * p.fit
    part = cq.Workplane("XY").box(w, l, p.lid_t, centered=False).translate((x0 + p.fit, y0 + p.fit, 0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    pts = [(cx + (i - (p.grille_nx - 1) / 2) * p.grille_pitch, cy + (j - (p.grille_ny - 1) / 2) * p.grille_pitch)
           for i in range(p.grille_nx) for j in range(p.grille_ny)]
    part = part.cut(cq.Workplane("XY").pushPoints(pts).circle(p.grille_hole / 2).extrude(p.lid_t + 2)
                    .translate((0, 0, -1)))
    for x, y in p.lid_screws():
        part = part.cut(cq.Workplane("XY").circle(p.screw_clear / 2).extrude(p.lid_t + 2).translate((x, y, -1)))
    return part


# ---------------------------------------------------------------- Tastenkappen

CAP_H = 7.0
CAP_TOP = 14.5
STEM_D, STEM_DEPTH = 5.5, 4.0
CROSS_L, CROSS_W = 4.15, 1.35       # MX-Kreuz mit Druckspiel


def _stem(x: float, y: float, z_top: float) -> tuple[cq.Workplane, cq.Workplane]:
    stem = cq.Workplane("XY").circle(STEM_D / 2).extrude(STEM_DEPTH).translate((x, y, z_top - STEM_DEPTH))
    cross = (cq.Workplane("XY").rect(CROSS_L, CROSS_W).extrude(STEM_DEPTH + 1)
             .union(cq.Workplane("XY").rect(CROSS_W, CROSS_L).extrude(STEM_DEPTH + 1))
             .translate((x, y, z_top - STEM_DEPTH - 1)))
    return stem, cross


def _shell(w_bottom: float, d_bottom: float, w_top: float, d_top: float, h: float, wall: float = 1.4) -> cq.Workplane:
    outer = (cq.Workplane("XY").rect(w_bottom, d_bottom).workplane(offset=h).rect(w_top, d_top).loft())
    inner = (cq.Workplane("XY").workplane(offset=-0.01).rect(w_bottom - 2 * wall, d_bottom - 2 * wall)
             .workplane(offset=h - 1.4).rect(w_top - 2 * wall, d_top - 2 * wall).loft())
    return outer.cut(inner)


def _dot(x: float, y: float, z: float, base_d: float = 1.5, h: float = 0.5) -> cq.Workplane:
    r = base_d / 2
    radius = (r * r + h * h) / (2 * h)
    sphere = cq.Workplane("XY").sphere(radius).translate((x, y, z + h - radius))
    return sphere.intersect(_box(x - 2, x + 2, y - 2, y + 2, z, z + 2))


# Braille: Punkte 1–3 links oben→unten, 4–6 rechts
BRAILLE = {"#": (3, 4, 5, 6), "1": (1,), "2": (1, 2), "3": (1, 4), "4": (1, 4, 5)}


def _braille(text: str, z: float, dot: float = 2.5, cell: float = 6.0) -> cq.Workplane:
    total = (len(text) - 1) * cell + dot
    result = None
    for i, ch in enumerate(text):
        x0 = -total / 2 + i * cell
        for n in BRAILLE[ch]:
            col = 0 if n <= 3 else 1
            row = (n - 1) % 3
            d = _dot(x0 + col * dot, dot - row * dot, z)
            result = d if result is None else result.union(d)
    return result


def keycap(symbol: str) -> cq.Workplane:
    cap = _shell(18.0, 18.0, CAP_TOP, CAP_TOP, CAP_H)
    stem, cross = _stem(0, 0, CAP_H - 1.4)
    cap = cap.union(stem).cut(cross)
    z = CAP_H
    relief = 0.8
    if symbol.startswith("braille"):
        cap = cap.union(_braille("#" + symbol[-1], z))
    elif symbol == "links":
        cap = cap.union(cq.Workplane("XY").polyline([(-4, 0), (3, 4), (3, -4)]).close().extrude(relief).translate((0, 0, z)))
    elif symbol == "rechts":
        cap = cap.union(cq.Workplane("XY").polyline([(4, 0), (-3, 4), (-3, -4)]).close().extrude(relief).translate((0, 0, z)))
    elif symbol == "minus":
        cap = cap.union(_box(-4.5, 4.5, -1, 1, z, z + relief))
    elif symbol == "plus":
        cap = cap.union(_box(-4.5, 4.5, -1, 1, z, z + relief)).union(_box(-1, 1, -4.5, 4.5, z, z + relief))
    elif symbol == "noppe":
        # Kugelkappe: Ø ca. 4, 1,2 hoch
        cap = cap.union(cq.Workplane("XY").sphere(2.3).translate((0, 0, z - 1.1)).intersect(_box(-3, 3, -3, 3, z, z + 3)))
    elif symbol == "kreuz":
        bar = _box(-5, 5, -0.9, 0.9, z, z + relief)
        cap = cap.union(bar.rotate((0, 0, 0), (0, 0, 1), 45)).union(bar.rotate((0, 0, 0), (0, 0, 1), -45))
    elif symbol == "mulde":
        cap = cap.cut(cq.Workplane("XY").sphere(12).translate((0, 0, z + 12 - 1.2)))
    return cap


def ptt_cap(p: Params) -> cq.Workplane:
    cap = _shell(p.ptt_width, 18.0, p.ptt_width - 3.5, CAP_TOP, CAP_H)
    for dx in (-p.ptt_switch_gap / 2, p.ptt_switch_gap / 2):
        stem, cross = _stem(dx, 0, CAP_H - 1.4)
        cap = cap.union(stem).cut(cross)
    # tastbare Längsrille als Erkennung
    cap = cap.cut(_box(-p.ptt_width / 2 + 8, p.ptt_width / 2 - 8, -0.8, 0.8, CAP_H - 0.6, CAP_H + 1))
    return cap


# ---------------------------------------------------------------- Kleinteile

TEST_CUTS = (13.8, 13.9, 14.0, 14.1, 14.2)


def test_strip(p: Params) -> cq.Workplane:
    """Probestreifen: Ausschnitte 13,8 … 14,2; Kerben am Rand zählen 1 … 5."""
    pitch = 20.0
    strip = _box(0, pitch * len(TEST_CUTS), 0, 24, 0, p.plate_t)
    for i, c in enumerate(TEST_CUTS):
        x = pitch / 2 + i * pitch
        strip = strip.cut(_box(x - c / 2, x + c / 2, 12 - c / 2, 12 + c / 2, -1, p.plate_t + 1))
        for n in range(i + 1):
            nx = x - (i * 1.6) / 2 + n * 1.6
            strip = strip.cut(_box(nx - 0.4, nx + 0.4, -1, 1.5, -1, p.plate_t + 1))
    return strip


def foot(p: Params) -> cq.Workplane:
    return cq.Workplane("XY").circle(p.foot_d / 2).extrude(p.foot_h)


# ---------------------------------------------------------------- Export

def parts(p: Params) -> dict[str, cq.Workplane]:
    result = {
        "unterteil": housing(p),
        "tastenplatte": key_plate(p),
        "podestdeckel": lid(p),
        "kappe_ptt": ptt_cap(p),
        "probestreifen_ausschnitt": test_strip(p),
        "fuss_tpu": foot(p),
    }
    for name, _, _, symbol in p.keys():
        result[f"kappe_{name}"] = keycap(symbol)
    return result


def assembly(p: Params, built: dict[str, cq.Workplane]) -> cq.Assembly:
    asm = cq.Assembly(name="carendmr_tastenfeld")
    asm.add(built["unterteil"], name="unterteil", color=cq.Color(0.85, 0.88, 0.92))
    # Tastenplatte auf die Schräge setzen
    seat_drop = p.plate_t / p.cos
    loc = cq.Location((p.wall, p.wall, p.top_z(p.wall) - seat_drop), (1, 0, 0), p.angle)
    asm.add(built["tastenplatte"], name="tastenplatte", loc=loc, color=cq.Color(0.55, 0.65, 0.78))
    asm.add(built["podestdeckel"], name="podestdeckel",
            loc=cq.Location((0, 0, p.h_pod - p.lid_t)), color=cq.Color(0.6, 0.7, 0.8))
    for name, u, v, _ in p.keys():
        cap_loc = cq.Location((p.wall, p.wall, p.top_z(p.wall) - seat_drop), (1, 0, 0), p.angle) * \
            cq.Location((u, v, p.plate_t + 5.0))
        asm.add(built[f"kappe_{name}"], name=f"kappe_{name}", loc=cap_loc, color=cq.Color(0.95, 0.95, 0.95))
    pu = p.plate_w / 2
    pv = p.key_rows()[3]
    ptt_loc = cq.Location((p.wall, p.wall, p.top_z(p.wall) - seat_drop), (1, 0, 0), p.angle) * \
        cq.Location((pu, pv, p.plate_t + 5.0))
    asm.add(built["kappe_ptt"], name="kappe_ptt", loc=ptt_loc, color=cq.Color(1.0, 0.85, 0.6))
    return asm


def export_all(out: Path, p: Params | None = None) -> list[Path]:
    p = p or Params()
    out = Path(out)
    (out / "step").mkdir(parents=True, exist_ok=True)
    (out / "stl").mkdir(parents=True, exist_ok=True)
    built = parts(p)
    written = []
    for name, part in built.items():
        step = out / "step" / f"{name}.step"
        stl = out / "stl" / f"{name}.stl"
        cq.exporters.export(part, str(step))
        cq.exporters.export(part, str(stl), tolerance=0.05, angularTolerance=0.2)
        written += [step, stl]
    asm_path = out / "step" / "baugruppe.step"
    assembly(p, built).export(str(asm_path))
    written.append(asm_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(Path(__file__).with_name("out")))
    args = parser.parse_args()
    for path in export_all(Path(args.out)):
        print(path)


if __name__ == "__main__":
    main()
