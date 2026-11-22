#!/usr/bin/env python3
"""
familytree.py — render a printable, centred family tree (SVG, optional PDF/PNG)
from a GEDCOM export of FamilySearch Family Tree data.

  python3 familytree.py TREE.ged --focus KWZ1-ABC -o tree.svg --pdf tree.pdf

The focus person may be given as a FamilySearch ID (_FSFTID / REFN), a GEDCOM
xref (@I12@ or I12), or a unique name fragment.

Layout: ancestors as a pedigree above the focus person (paternal line left,
maternal right, up to 4 generations back); descendants as an indented outline
below (up to 3 generations forward), flowed into balanced columns.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ───────────────────────────── data model ──────────────────────────────

@dataclass
class Event:
    date: str | None = None
    place: str | None = None


@dataclass
class Person:
    id: str
    given: str = ""
    surname: str = ""
    sex: str = "U"
    birth: Event = field(default_factory=Event)
    death: Event = field(default_factory=Event)
    fsid: str | None = None
    living: bool | None = None
    famc: list[str] = field(default_factory=list)
    fams: list[str] = field(default_factory=list)

    @property
    def full(self) -> str:
        return " ".join(x for x in (self.given, self.surname) if x) or "Unknown"


@dataclass
class Family:
    id: str
    husb: str | None = None
    wife: str | None = None
    children: list[str] = field(default_factory=list)
    marr: Event = field(default_factory=Event)


class Tree:
    def __init__(self):
        self.people: dict[str, Person] = {}
        self.families: dict[str, Family] = {}

    # ── loaders ──
    @classmethod
    def from_gedcom(cls, path: Path) -> "Tree":
        t = cls()
        raw = path.read_bytes()
        if raw[:2] == b"PK":  # GEDCOM 7 zip package (.gdz) — use the .ged inside
            import io, zipfile
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                name = next((n for n in z.namelist() if n.lower().endswith(".ged")), None)
                if not name:
                    sys.exit("error: no .ged file inside the archive")
                raw = z.read(name)
        text = raw.decode("utf-8-sig", errors="replace")
        rec = None          # current Person/Family
        ev = None           # current Event
        l1 = None           # current level-1 tag
        for line in text.splitlines():
            m = re.match(r"\s*(\d+)\s+(@[^@]+@\s+)?(\S+)\s?(.*)$", line)
            if not m:
                continue
            lvl, xref, tag, val = int(m[1]), (m[2] or "").strip(), m[3], m[4].strip()
            if lvl == 0:
                ev = l1 = None
                xid = xref.strip("@")
                if tag == "INDI":
                    rec = t.people.setdefault(xid, Person(xid))
                elif tag == "FAM":
                    rec = t.families.setdefault(xid, Family(xid))
                else:
                    rec = None
                continue
            if rec is None:
                continue
            ref = val.strip("@")
            if lvl == 1:
                l1, ev = tag, None
                if isinstance(rec, Person):
                    if tag == "NAME" and not (rec.given or rec.surname):
                        nm = re.match(r"([^/]*)/?([^/]*)/?(.*)", val)
                        rec.given = " ".join((nm[1] + " " + nm[3]).split())
                        rec.surname = nm[2].strip()
                    elif tag == "SEX":
                        rec.sex = (val[:1] or "U").upper()
                    elif tag in ("BIRT", "CHR", "BAPM") and (tag == "BIRT" or not (rec.birth.date or rec.birth.place)):
                        if tag == "BIRT":
                            rec.birth = Event()
                        ev = rec.birth
                    elif tag in ("DEAT", "BURI") and (tag == "DEAT" or not (rec.death.date or rec.death.place)):
                        if tag == "DEAT":
                            rec.death = Event()
                        ev = rec.death
                        if val.upper() == "Y":
                            rec.living = False
                    elif tag in ("_FSFTID", "_FSID", "_FID") or (tag in ("REFN", "EXID", "UID") and re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{3,4}", val.split("/")[-1])):
                        rec.fsid = rec.fsid or val.split("/")[-1]
                    elif tag == "_LIVING" or tag == "LIVING":
                        rec.living = val.upper() in ("Y", "YES", "TRUE", "1")
                    elif tag == "FAMC":
                        rec.famc.append(ref)
                    elif tag == "FAMS":
                        rec.fams.append(ref)
                else:
                    if tag == "HUSB":
                        rec.husb = ref
                    elif tag == "WIFE":
                        rec.wife = ref
                    elif tag == "CHIL":
                        rec.children.append(ref)
                    elif tag == "MARR":
                        ev = rec.marr
            elif lvl == 2 and ev is not None:
                if tag == "DATE":
                    ev.date = val
                elif tag == "PLAC":
                    ev.place = val
                if isinstance(rec, Person) and l1 in ("DEAT", "BURI"):
                    rec.living = False
        t._link()
        return t

    @classmethod
    def from_json(cls, path: Path) -> "Tree":
        """JSON: {"people": {id: {given, surname, sex, birth:{date,place}, death:{...},
        fsid, living}}, "families": {id: {husb, wife, children:[...], marr:{...}}}}"""
        data = json.loads(path.read_text(encoding="utf-8"))
        t = cls()
        for pid, d in data.get("people", {}).items():
            t.people[pid] = Person(
                pid, d.get("given", ""), d.get("surname", ""), (d.get("sex") or "U")[:1].upper(),
                Event(**(d.get("birth") or {})), Event(**(d.get("death") or {})),
                d.get("fsid"), d.get("living"))
        for fid, d in data.get("families", {}).items():
            t.families[fid] = Family(fid, d.get("husb"), d.get("wife"),
                                     list(d.get("children", [])), Event(**(d.get("marr") or {})))
        for f in t.families.values():
            for x in (f.husb, f.wife):
                if x in t.people and f.id not in t.people[x].fams:
                    t.people[x].fams.append(f.id)
            for c in f.children:
                if c in t.people and f.id not in t.people[c].famc:
                    t.people[c].famc.append(f.id)
        t._link()
        return t

    def _link(self):
        # Make family membership symmetric even if the export only listed one side.
        for f in self.families.values():
            for x in (f.husb, f.wife):
                if x in self.people and f.id not in self.people[x].fams:
                    self.people[x].fams.append(f.id)
            for c in f.children:
                if c in self.people and f.id not in self.people[c].famc:
                    self.people[c].famc.append(f.id)
        for p in self.people.values():
            for fid in p.famc:
                f = self.families.get(fid)
                if f and p.id not in f.children:
                    f.children.append(p.id)

    # ── queries ──
    def find(self, key: str) -> Person:
        k = key.strip().strip("@")
        if k in self.people:
            return self.people[k]
        hits = [p for p in self.people.values() if p.fsid and p.fsid.upper() == k.upper()]
        if not hits:
            low = k.lower()
            hits = [p for p in self.people.values() if low in p.full.lower()]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            sys.exit(f"error: no person matches {key!r}")
        listing = "\n".join(f"  {p.id:>8}  {p.fsid or '':10} {p.full} {lifespan(p)}" for p in hits[:25])
        sys.exit(f"error: {key!r} is ambiguous; use an ID:\n{listing}")

    def parents(self, p: Person) -> tuple[Person | None, Person | None]:
        for fid in p.famc:
            f = self.families.get(fid)
            if f:
                return self.people.get(f.husb or ""), self.people.get(f.wife or "")
        return None, None

    def ahnentafel(self, focus: Person, depth: int) -> dict[int, Person]:
        anc = {1: focus}
        for n in range(1, 2 ** depth):
            if n in anc:
                fa, mo = self.parents(anc[n])
                if fa:
                    anc[2 * n] = fa
                if mo:
                    anc[2 * n + 1] = mo
        return anc

    def ahnentafel_family(self, fam: Family, depth: int) -> dict[int, Person]:
        """Pedigree for a couple: 2 = husband, 3 = wife (no person at position 1)."""
        anc = {}
        if fam.husb in self.people:
            anc[2] = self.people[fam.husb]
        if fam.wife in self.people:
            anc[3] = self.people[fam.wife]
        for n in range(2, 2 ** depth):
            if n in anc:
                fa, mo = self.parents(anc[n])
                if fa:
                    anc[2 * n] = fa
                if mo:
                    anc[2 * n + 1] = mo
        return anc

    def unions(self, p: Person):
        """[(spouse|None, Family, [children sorted by birth])]"""
        out = []
        for fid in p.fams:
            f = self.families.get(fid)
            if not f:
                continue
            sp_id = f.wife if f.husb == p.id else f.husb
            kids = [self.people[c] for c in f.children if c in self.people]
            kids.sort(key=lambda c: (year(c.birth.date) or 9999))
            out.append((self.people.get(sp_id or ""), f, kids))
        out.sort(key=lambda u: year(u[1].marr.date) or min([year(k.birth.date) or 9999 for k in u[2]] or [9999]))
        return out


# ───────────────────────────── formatting ──────────────────────────────

MONTHS = dict(JAN="Jan", FEB="Feb", MAR="Mar", APR="Apr", MAY="May", JUN="Jun",
              JUL="Jul", AUG="Aug", SEP="Sep", OCT="Oct", NOV="Nov", DEC="Dec")
QUAL = {"ABT": "c.", "ABOUT": "c.", "EST": "c.", "CAL": "c.", "CIRCA": "c.",
        "BEF": "bef.", "BEFORE": "bef.", "AFT": "aft.", "AFTER": "aft."}


def year(d: str | None) -> int | None:
    if not d:
        return None
    m = re.search(r"\b(\d{3,4})\b", d)
    return int(m[1]) if m else None


def short_date(d: str | None) -> str:
    """'ABT 1850' -> 'c. 1850'; '12 MAR 1872' -> '1872'."""
    if not d:
        return ""
    y = year(d)
    if y is None:
        return ""
    q = d.split()[0].upper().rstrip(".")
    if q in ("BET", "FROM"):
        return f"c. {y}"
    return f"{QUAL[q]} {y}" if q in QUAL else str(y)


def long_date(d: str | None) -> str:
    if not d:
        return ""
    parts = d.split()
    q = ""
    if parts and parts[0].upper().rstrip(".") in QUAL:
        q = QUAL[parts[0].upper().rstrip(".")] + " "
        parts = parts[1:]
    parts = [MONTHS.get(x.upper(), x) for x in parts]
    return q + " ".join(parts)


def is_living(p: Person) -> bool:
    if p.living is not None:
        return p.living
    if p.death.date or p.death.place:
        return False
    y = year(p.birth.date)
    return y is not None and y > _dt.date.today().year - 105


def lifespan(p: Person, redact: bool = False) -> str:
    if redact and is_living(p):
        return "Living"
    b, d = short_date(p.birth.date), short_date(p.death.date)
    if b and d:
        return f"{b} – {d}"
    if b:
        return f"b. {b}" if is_living(p) else f"{b} – ?"
    if d:
        return f"d. {d}"
    return "Living" if p.living else ""


def short_place(pl: str | None, parts: int = 2) -> str:
    if not pl:
        return ""
    xs = [x.strip() for x in pl.split(",") if x.strip()]
    xs = [x for x in xs if x not in ("United States", "USA", "United States of America")] or xs
    if len(xs) <= parts:
        return ", ".join(xs)
    return ", ".join([xs[0]] + xs[-(parts - 1):]) if parts > 1 else xs[0]


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# Width estimates (em per character) for the chosen faces — conservative.
W_SERIF = 0.47
W_CAPS = 0.68


def tw(s: str, size: float, k: float = W_SERIF, track: float = 0.0) -> float:
    return len(s) * size * k + max(0, len(s) - 1) * track


def fit_given(given: str, max_w: float, size: float) -> str:
    if tw(given, size) <= max_w:
        return given
    parts = given.split()
    # Drop to initials for middle names, then for all but the first.
    for keep in range(len(parts) - 1, 0, -1):
        cand = " ".join(parts[:keep] + [p[0] + "." for p in parts[keep:]])
        if tw(cand, size) <= max_w:
            return cand
    s = parts[0] if parts else given
    while len(s) > 3 and tw(s + "…", size) > max_w:
        s = s[:-1]
    return s if tw(s, size) <= max_w else s + "…"


def fit_text(s: str, max_w: float, size: float, k: float = W_SERIF, track: float = 0.0) -> str:
    if tw(s, size, k, track) <= max_w:
        return s
    while len(s) > 2 and tw(s + "…", size, k, track) > max_w:
        s = s[:-1]
    return s.rstrip(" ,") + "…"


# ───────────────────────────── palette & type ──────────────────────────

PALETTE = {
    "paper": "#FBF8F1",
    "card": "#FFFEFA",
    "ink": "#2B302C",
    "ink2": "#5E625A",
    "faint": "#9A9C90",
    "gold": "#A8894F",
    "sage": "#6F8461",     # paternal
    "clay": "#A6705E",     # maternal
    "line": "#8C8A7E",
}
FONT_DISPLAY = "'Cormorant Garamond', 'Cormorant', 'EB Garamond', Garamond, Georgia, 'Times New Roman', serif"
FONT_TEXT = "'EB Garamond', Garamond, Georgia, 'Times New Roman', serif"
FONTS_URL = ("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500"
             "&family=EB+Garamond:ital,wght@0,400;0,500;1,400"
             "&family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&family=Pinyon+Script&display=swap")


# ───────────────────────────── ornaments ───────────────────────────────

def _quad(p0, p1, p2, t):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
    dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
    dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
    return x, y, math.atan2(dy, dx)


def leaf(x, y, ang, length, width) -> str:
    """Almond-shaped line-art leaf with a midrib, base at (x,y), pointing along ang."""
    ca, sa = math.cos(ang), math.sin(ang)
    def P(u, v):  # local (along, across) → global
        return f"{x + u * ca - v * sa:.2f},{y + u * sa + v * ca:.2f}"
    L, W = length, width
    outline = f"M{P(0,0)} Q{P(L*0.45, W)} {P(L,0)} Q{P(L*0.45,-W)} {P(0,0)}Z"
    rib = f"M{P(0,0)} L{P(L*0.82,0)}"
    return f'<path d="{outline}"/><path d="{rib}" stroke-width="0.35"/>'


def sprig(length=120.0, leaves=6, curve=0.10, leaf_len=13.0, seed_side=1) -> str:
    """A curved stem along +x from the origin with alternating leaves and a bud."""
    p0, p1, p2 = (0, 0), (length * 0.5, -length * curve), (length, 0)
    out = [f'<path d="M0,0 Q{p1[0]:.2f},{p1[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}" stroke-width="0.6"/>']
    for i in range(leaves):
        t = 0.16 + 0.78 * i / max(1, leaves - 1)
        x, y, a = _quad(p0, p1, p2, t)
        side = seed_side if i % 2 == 0 else -seed_side
        ll = leaf_len * (1.0 - 0.45 * t)
        out.append(leaf(x, y, a + side * 0.75, ll, ll * 0.32))
    x, y, a = _quad(p0, p1, p2, 1.0)
    out.append(f'<circle cx="{x + 2.2 * math.cos(a):.2f}" cy="{y + 2.2 * math.sin(a):.2f}" r="1.4"/>')
    return "".join(out)


def corner(x, y, sx, sy, color) -> str:
    """Two sprigs fanning from a corner along the border edges."""
    g = [f'<g transform="translate({x},{y}) scale({sx},{sy})" fill="none" stroke="{color}" '
         f'stroke-width="0.55" stroke-linecap="round" opacity="0.75">']
    g.append(f'<g transform="rotate(4)">{sprig(130, 7, 0.07, 12, 1)}</g>')
    g.append(f'<g transform="rotate(86)">{sprig(95, 5, -0.07, 11, -1)}</g>')
    g.append(f'<g transform="rotate(45)">{sprig(34, 2, 0.0, 9, 1)}</g>')
    g.append('<circle cx="0" cy="0" r="1.8"/>')
    g.append("</g>")
    return "".join(g)


def flourish(cx, cy, half, color) -> str:
    """Horizontal laurel: mirrored sprigs either side of a small lozenge."""
    s = sprig(half, 5, 0.06, 9, 1)
    return (f'<g fill="none" stroke="{color}" stroke-width="0.55" stroke-linecap="round" opacity="0.85">'
            f'<g transform="translate({cx + 7},{cy})">{s}</g>'
            f'<g transform="translate({cx - 7},{cy}) scale(-1,1)">{s}</g>'
            f'<path d="M{cx},{cy - 3.2} L{cx + 3.2},{cy} L{cx},{cy + 3.2} L{cx - 3.2},{cy}Z" fill="{color}" stroke="none"/>'
            f'</g>')


# ───────────────────────────── themes ──────────────────────────────────

THEMES = {
    "classic": dict(palette=dict(PALETTE), border="fine", tree_art=0.0, card="rounded", glyphs=False, sprigs=True),
    "woodcut": dict(palette={"paper": "#F4ECDA", "card": "#FBF6EA", "ink": "#2A2016", "ink2": "#584734",
                             "faint": "#9A8970", "gold": "#7C5D31", "sage": "#4E6240", "clay": "#874C35",
                             "line": "#6C5843"},
                    border="woodcut", tree_art=0.12, card="woodcut", glyphs=True, sprigs=False),
    "heirloom": dict(palette={"paper": "#FAF6EE", "card": "#FFFDF8", "ink": "#1E2622", "ink2": "#4B554F",
                              "faint": "#959D97", "gold": "#A3813D", "sage": "#2E5A4D", "clay": "#7A2C3A",
                              "line": "#7D837E"},
                     border="ornate", tree_art=0.055, card="cartouche", glyphs=True, sprigs=False),
    "victorian": dict(palette={"paper": "#EDE0C2", "card": "#F5ECD6", "ink": "#3A2918", "ink2": "#5B442D",
                               "faint": "#977F5E", "gold": "#8A6630", "sage": "#4B5A38", "clay": "#7C3324",
                               "line": "#5D4831"},
                      border="engraved", tree_art=0.10, card="cartouche", glyphs=True, sprigs=False,
                      aged=True, banner=True,
                      fonts=("'IM Fell English', 'EB Garamond', Georgia, serif",
                             "'IM Fell English', 'EB Garamond', Georgia, serif"),
                      title_font="'Pinyon Script', 'IM Fell English', cursive"),
}


def hypotrochoid(cx, cy, R, r, d, scale, turns) -> str:
    pts = []
    n = int(turns * 90)
    for i in range(n + 1):
        t = turns * 2 * math.pi * i / n
        x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
        y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
        pts.append(f"{cx + x * scale:.2f},{cy + y * scale:.2f}")
    return "M" + " L".join(pts)


def guilloche_band(x0, y0, x1, y1, amp, wl, strands=3) -> str:
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    out = []
    for k in range(strands):
        ph = 2 * math.pi * k / strands
        pts = []
        for i in range(int(L / 1.5) + 1):
            t = i * 1.5
            o = amp * math.sin(2 * math.pi * t / wl + ph)
            pts.append(f"{x0 + ux * t + nx * o:.1f},{y0 + uy * t + ny * o:.1f}")
        out.append("M" + " L".join(pts))
    return " ".join(out)


def swash(cx, y, half, color) -> str:
    """Calligraphic thick-thin flourish, mirrored about cx."""
    def side(s):
        p = (f"M{cx + s*8:.1f},{y:.1f} C{cx + s*40:.1f},{y - 9:.1f} {cx + s*half*0.55:.1f},{y + 9:.1f} {cx + s*half*0.85:.1f},{y - 1:.1f} "
             f"C{cx + s*half*0.97:.1f},{y - 6:.1f} {cx + s*half*0.93:.1f},{y - 12:.1f} {cx + s*half*0.86:.1f},{y - 8:.1f} "
             f"C{cx + s*half*0.82:.1f},{y - 4:.1f} {cx + s*half*0.92:.1f},{y + 1:.1f} {cx + s*half:.1f},{y - 2:.1f}")
        thick = (f"M{cx + s*14:.1f},{y + 0.3:.1f} C{cx + s*42:.1f},{y - 7.2:.1f} {cx + s*half*0.5:.1f},{y + 8.6:.1f} {cx + s*half*0.78:.1f},{y + 0.8:.1f}")
        return (f'<path d="{p}" stroke="{color}" stroke-width="0.7" fill="none"/>'
                f'<path d="{thick}" stroke="{color}" stroke-width="1.7" fill="none" stroke-linecap="round"/>')
    return (side(1) + side(-1) +
            f'<path d="M{cx},{y - 4} l4,4 l-4,4 l-4,-4Z" fill="{color}"/>'
            f'<circle cx="{cx - 9}" cy="{y}" r="1.1" fill="{color}"/><circle cx="{cx + 9}" cy="{y}" r="1.1" fill="{color}"/>')


def ribbon(cx, y, w, h, fill, ink) -> str:
    """Engraved ribbon banner with folded tails, centred on (cx, y)."""
    x0, x1, t = cx - w / 2, cx + w / 2, h * 0.9
    bow = 4
    body = (f"M{x0:.1f},{y - h/2:.1f} Q{cx:.1f},{y - h/2 - bow:.1f} {x1:.1f},{y - h/2:.1f} "
            f"L{x1:.1f},{y + h/2:.1f} Q{cx:.1f},{y + h/2 - bow:.1f} {x0:.1f},{y + h/2:.1f}Z")
    def tail(s, xe):
        xa = xe + s * t * 1.6
        return (f'<path d="M{xe:.1f},{y - h/2 + 4:.1f} L{xa:.1f},{y - h/2 + 4:.1f} L{xa - s*t*0.45:.1f},{y + 2 + 4:.1f} '
                f'L{xa:.1f},{y + h/2 + 4:.1f} L{xe:.1f},{y + h/2 + 4:.1f}Z" fill="{fill}" stroke="{ink}" stroke-width="0.7"/>'
                f'<path d="M{xe:.1f},{y + h/2:.1f} L{xe + s*6:.1f},{y + h/2 + 4:.1f} L{xe:.1f},{y + h/2 + 4:.1f}Z" fill="{ink}" opacity="0.55"/>')
    hatch = " ".join(f"M{x0 + 3 + i*3:.1f},{y + h/2 - 2.5:.1f} l2,-2.5" for i in range(int((w - 6) / 3)))
    return (tail(-1, x0 + 6) + tail(1, x1 - 6) +
            f'<path d="{body}" fill="{fill}" stroke="{ink}" stroke-width="0.8"/>'
            f'<path d="{hatch}" stroke="{ink}" stroke-width="0.3" opacity="0.35"/>')


def leaf_filled(x, y, ang, length, width, ink, paper) -> str:
    ca, sa = math.cos(ang), math.sin(ang)
    def P(u, v):
        return f"{x + u * ca - v * sa:.2f},{y + u * sa + v * ca:.2f}"
    L, W = length, width
    return (f'<path d="M{P(0,0)} Q{P(L*0.45, W)} {P(L,0)} Q{P(L*0.45,-W)} {P(0,0)}Z" fill="{ink}"/>'
            f'<path d="M{P(L*0.1,0)} L{P(L*0.8,0)}" stroke="{paper}" stroke-width="{max(0.3, W*0.18):.2f}" fill="none"/>')


def woodcut_tree(cx, base_y, top_y, half_w, ink, paper, opacity, seed=11) -> str:
    """A procedurally carved oak: tapered solid limbs with paper-coloured gouge lines,
    leaf clusters at the tips, spreading roots and a hatched ground line."""
    import random
    rng = random.Random(seed)
    out = []

    def tapered(x0, y0, x1, y1, w0, w1, bend, carve=0):
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        mx_, my_ = (x0 + x1) / 2 + nx * bend, (y0 + y1) / 2 + ny * bend
        wm = (w0 + w1) / 4
        out.append(
            f'<path d="M{x0 + nx*w0/2:.1f},{y0 + ny*w0/2:.1f} Q{mx_ + nx*wm:.1f},{my_ + ny*wm:.1f} {x1 + nx*w1/2:.1f},{y1 + ny*w1/2:.1f} '
            f'L{x1 - nx*w1/2:.1f},{y1 - ny*w1/2:.1f} Q{mx_ - nx*wm:.1f},{my_ - ny*wm:.1f} {x0 - nx*w0/2:.1f},{y0 - ny*w0/2:.1f}Z" fill="{ink}"/>')
        for k in range(carve):  # gouge lines along the grain
            o = (k + 1) / (carve + 1) - 0.5
            sw = max(0.35, w0 * 0.055)
            out.append(f'<path d="M{x0 + nx*w0*o*0.8 + dx*0.06:.1f},{y0 + ny*w0*o*0.8 + dy*0.06:.1f} '
                       f'Q{mx_ + nx*wm*o*1.6:.1f},{my_ + ny*wm*o*1.6:.1f} {x1 + nx*w1*o*0.6 - dx*0.1:.1f},{y1 + ny*w1*o*0.6 - dy*0.1:.1f}" '
                       f'stroke="{paper}" stroke-width="{sw:.2f}" fill="none" stroke-linecap="round"/>')

    def branch(x, y, ang, length, width, depth):
        x1, y1 = x + math.cos(ang) * length, y - math.sin(ang) * length
        tapered(x, y, x1, y1, width, width * 0.66, rng.uniform(-0.1, 0.1) * length,
                carve=3 if width > 14 else 2 if width > 6 else 1 if width > 3 else 0)
        if depth == 0 or width < 1.4:
            for _ in range(rng.randint(4, 7)):
                a = ang + rng.uniform(-1.4, 1.4)
                d = rng.uniform(0, 8)
                out.append(leaf_filled(x1 + math.cos(a) * d, y1 - math.sin(a) * d, -a + rng.uniform(-0.4, 0.4),
                                       rng.uniform(7, 12), rng.uniform(2.2, 3.4), ink, paper))
            return
        nb = 3 if rng.random() < 0.25 else 2
        spread = rng.uniform(0.32, 0.55)
        for i in range(nb):
            t = (i - (nb - 1) / 2) / ((nb - 1) / 2)
            a = ang + spread * t + rng.uniform(-0.12, 0.12)
            a = min(math.pi - 0.08, max(0.08, a))      # keep limbs above horizontal
            branch(x1, y1, a, length * rng.uniform(0.7, 0.82), width * rng.uniform(0.6, 0.7), depth - 1)

    fork_y = top_y + (base_y - top_y) * 0.55
    trunk_w = half_w * 0.075
    tapered(cx, base_y, cx, fork_y, trunk_w, trunk_w * 0.8, 0, carve=6)
    for k in range(18):  # bark ticks
        yy = fork_y + (base_y - fork_y) * rng.random()
        xx = cx + trunk_w * rng.uniform(-0.38, 0.38)
        out.append(f'<path d="M{xx:.1f},{yy:.1f} q{rng.uniform(2,5):.1f},{rng.uniform(-1,1):.1f} {rng.uniform(4,9):.1f},0" '
                   f'stroke="{paper}" stroke-width="0.6" fill="none"/>')
    reach = (fork_y - top_y)
    for a in (2.75, 2.25, 1.75, 1.39, 0.89, 0.39):
        h = max(0.25, math.sin(a))
        branch(cx + (a - 1.57) * trunk_w * 0.25, fork_y, a, reach * 0.36 / h ** 0.35 * (half_w / reach) ** 0.5 * 0.9,
               trunk_w * 0.42, 6)
    for a in (-0.15, -0.55, -1.2, -1.95, -2.6, -3.0):  # roots
        L = trunk_w * rng.uniform(1.4, 2.4)
        tapered(cx + math.cos(a) * trunk_w * 0.2, base_y, cx + math.cos(a) * L * 1.6, base_y - math.sin(a) * L * 0.35,
                trunk_w * 0.32, 1.2, rng.uniform(-4, 4), carve=1)
    for k in range(60):  # ground hatching
        xx = cx + rng.uniform(-half_w * 0.35, half_w * 0.35)
        yy = base_y + rng.uniform(-2, 6)
        out.append(f'<path d="M{xx:.1f},{yy:.1f} l{rng.uniform(3,7):.1f},{rng.uniform(-0.6,0.6):.1f}" stroke="{ink}" stroke-width="0.8"/>')
    return f'<g opacity="{opacity}">{"".join(out)}</g>'


def glyph(kind, x, y, s, color) -> str:
    """Small drawn event marks: b = six-ray star, d = dagger, m = interlocked rings."""
    if kind == "b":
        r = s * 0.34
        rays = "".join(f"M{x:.2f},{y:.2f} L{x + r * math.cos(a):.2f},{y + r * math.sin(a):.2f} "
                       for a in [k * math.pi / 3 + math.pi / 6 for k in range(6)])
        return f'<path d="{rays}" stroke="{color}" stroke-width="{s * 0.09:.2f}" stroke-linecap="round"/>'
    if kind == "d":
        h = s * 0.4
        return (f'<path d="M{x:.2f},{y - h:.2f} V{y + h:.2f} M{x - h * 0.5:.2f},{y - h * 0.35:.2f} H{x + h * 0.5:.2f}" '
                f'stroke="{color}" stroke-width="{s * 0.09:.2f}" stroke-linecap="round"/>')
    if kind == "m":
        r = s * 0.3
        return (f'<g fill="none" stroke="{color}" stroke-width="{s * 0.08:.2f}"><circle cx="{x - r * 0.55:.2f}" cy="{y:.2f}" r="{r:.2f}"/>'
                f'<circle cx="{x + r * 0.55:.2f}" cy="{y:.2f}" r="{r:.2f}"/></g>')
    return ""


def border(kind, W, H, P) -> str:
    out = []
    if kind == "fine":
        out.append(f'<rect x="18" y="18" width="{W - 36}" height="{H - 36:.2f}" fill="none" stroke="{P["gold"]}" stroke-width="1.1"/>')
        out.append(f'<rect x="23.5" y="23.5" width="{W - 47}" height="{H - 47:.2f}" fill="none" stroke="{P["gold"]}" stroke-width="0.4"/>')
    elif kind == "woodcut":
        ink = P["ink"]
        out.append(f'<rect x="15" y="15" width="{W - 30}" height="{H - 30:.2f}" fill="none" stroke="{ink}" stroke-width="6"/>')
        out.append(f'<rect x="26.5" y="26.5" width="{W - 53}" height="{H - 53:.2f}" fill="none" stroke="{ink}" stroke-width="1.3"/>')
        hatch = []
        for x in range(26, int(W - 26), 5):  # diagonal gouge band between the rules
            hatch.append(f"M{x},19 l4,6 M{x},{H - 19:.1f} l4,-6")
        for y in range(26, int(H - 26), 5):
            hatch.append(f"M19,{y} l6,4 M{W - 19},{y} l-6,4")
        out.append(f'<path d="{" ".join(hatch)}" stroke="{ink}" stroke-width="0.9" opacity="0.75"/>')
        for (x, y) in ((12, 12), (W - 36, 12), (12, H - 36), (W - 36, H - 36)):
            out.append(f'<rect x="{x}" y="{y:.1f}" width="24" height="24" fill="{ink}"/>')
            c = (x + 12, y + 12)
            for a in range(4):
                out.append(leaf_filled(c[0], c[1], a * math.pi / 2 + math.pi / 4, 9, 3.2, P["paper"], ink))
    elif kind == "ornate":
        g, sage = P["gold"], P["sage"]
        out.append(f'<rect x="15" y="15" width="{W - 30}" height="{H - 30:.2f}" fill="none" stroke="{g}" stroke-width="3.2"/>')
        out.append(f'<rect x="20.5" y="20.5" width="{W - 41}" height="{H - 41:.2f}" fill="none" stroke="{g}" stroke-width="0.7"/>')
        out.append(f'<rect x="33.5" y="33.5" width="{W - 67}" height="{H - 67:.2f}" fill="none" stroke="{g}" stroke-width="0.7"/>')
        vine = []
        def run(x0, y0, x1, y1):
            L = math.hypot(x1 - x0, y1 - y0)
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            n = int(L // 15)
            a0 = math.atan2(uy, ux)
            vine.append(f'<path d="M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f}" stroke="{sage}" stroke-width="0.45"/>')
            for i in range(1, n):
                px, py = x0 + ux * i * 15, y0 + uy * i * 15
                side = 1 if i % 2 else -1
                vine.append(leaf(px, py, a0 + side * 0.7, 6.5, 2.1))
        run(52, 27, W - 52, 27); run(52, H - 27, W - 52, H - 27)
        run(27, 52, 27, H - 52); run(W - 27, 52, W - 27, H - 52)
        out.append(f'<g fill="none" stroke="{sage}" stroke-width="0.5">{"".join(vine)}</g>')
        for (x, y) in ((27, 27), (W - 27, 27), (27, H - 27), (W - 27, H - 27)):
            out.append(f'<circle cx="{x}" cy="{y:.1f}" r="13" fill="{P["paper"]}" stroke="{g}" stroke-width="0.8"/>')
            petals = "".join(leaf(x, y, a * math.pi / 4, 10 if a % 2 == 0 else 7, 3) for a in range(8))
            out.append(f'<g fill="none" stroke="{g}" stroke-width="0.6">{petals}</g>'
                       f'<circle cx="{x}" cy="{y:.1f}" r="2" fill="{g}"/>')
    elif kind == "engraved":
        ink, g = P["ink"], P["gold"]
        out.append(f'<rect x="13" y="13" width="{W - 26}" height="{H - 26:.2f}" fill="none" stroke="{ink}" stroke-width="2.4"/>')
        out.append(f'<rect x="17" y="17" width="{W - 34}" height="{H - 34:.2f}" fill="none" stroke="{ink}" stroke-width="0.5"/>')
        out.append(f'<rect x="33" y="33" width="{W - 66}" height="{H - 66:.2f}" fill="none" stroke="{ink}" stroke-width="0.5"/>')
        out.append(f'<rect x="37" y="37" width="{W - 74}" height="{H - 74:.2f}" fill="none" stroke="{ink}" stroke-width="1.4"/>')
        c = 25
        band = (guilloche_band(c + 14, c, W - c - 14, c, 4.2, 18) + " " + guilloche_band(c + 14, H - c, W - c - 14, H - c, 4.2, 18) + " " +
                guilloche_band(c, c + 14, c, H - c - 14, 4.2, 18) + " " + guilloche_band(W - c, c + 14, W - c, H - c - 14, 4.2, 18))
        band2 = (guilloche_band(c + 14, c, W - c - 14, c, 2.2, 9, 2) + " " + guilloche_band(c + 14, H - c, W - c - 14, H - c, 2.2, 9, 2) + " " +
                 guilloche_band(c, c + 14, c, H - c - 14, 2.2, 9, 2) + " " + guilloche_band(W - c, c + 14, W - c, H - c - 14, 2.2, 9, 2))
        out.append(f'<path d="{band}" stroke="{ink}" stroke-width="0.4" fill="none" opacity="0.85"/>')
        out.append(f'<path d="{band2}" stroke="{g}" stroke-width="0.3" fill="none" opacity="0.8"/>')
        for (x, y) in ((c, c), (W - c, c), (c, H - c), (W - c, H - c)):
            out.append(f'<circle cx="{x}" cy="{y:.1f}" r="17" fill="{P["paper"]}" stroke="{ink}" stroke-width="1.2"/>'
                       f'<circle cx="{x}" cy="{y:.1f}" r="14.5" fill="none" stroke="{ink}" stroke-width="0.4"/>'
                       f'<path d="{hypotrochoid(x, y, 5, 3, 5, 1.95, 3)}" stroke="{ink}" stroke-width="0.35" fill="none"/>'
                       f'<path d="{hypotrochoid(x, y, 7, 2, 3.2, 1.0, 2)}" stroke="{g}" stroke-width="0.3" fill="none"/>'
                       f'<circle cx="{x}" cy="{y:.1f}" r="1.6" fill="{ink}"/>')
        for (x, y) in ((W / 2, H - c),):  # medallion at bottom centre
            out.append(f'<ellipse cx="{x}" cy="{y:.1f}" rx="30" ry="9" fill="{P["paper"]}" stroke="{ink}" stroke-width="0.8"/>'
                       f'<path d="{hypotrochoid(x, y, 5, 3, 5, 1.1, 3)}" stroke="{ink}" stroke-width="0.3" fill="none" transform="translate({x} {y}) scale(2.4 0.75) translate({-x} {-y})"/>')
    return "".join(out)


def aged_paper(W, H, P) -> str:
    """Parchment texture, darkened edges and a few foxing spots."""
    import random
    rng = random.Random(3)
    spots = "".join(f'<circle cx="{rng.uniform(40, W - 40):.0f}" cy="{rng.uniform(40, H - 40):.0f}" r="{rng.uniform(4, 16):.1f}" '
                    f'fill="#8A5A2B" opacity="{rng.uniform(0.04, 0.09):.3f}" filter="url(#ft-blur)"/>' for _ in range(14))
    return (f'<g id="ft-aged"><defs><filter id="ft-tex" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="4"/>'
            f'<feColorMatrix values="0 0 0 0 0.35  0 0 0 0 0.24  0 0 0 0 0.12  0 0 0 -1.6 1.15"/></filter>'
            f'<filter id="ft-blot" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="9"/>'
            f'<feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.3  0 0 0 0 0.12  0 0 0 -2.2 1.05"/></filter>'
            f'<filter id="ft-blur"><feGaussianBlur stdDeviation="3"/></filter>'
            f'<radialGradient id="ft-vig" cx="50%" cy="48%" r="72%">'
            f'<stop offset="62%" stop-color="#7A5226" stop-opacity="0"/><stop offset="100%" stop-color="#6B4520" stop-opacity="0.32"/></radialGradient></defs>'
            f'<rect width="{W}" height="{H:.1f}" filter="url(#ft-blot)" opacity="0.35"/>'
            f'<rect width="{W}" height="{H:.1f}" filter="url(#ft-tex)" opacity="0.22"/>'
            f'{spots}<rect width="{W}" height="{H:.1f}" fill="url(#ft-vig)"/></g>')


# ───────────────────────────── renderer ────────────────────────────────

PAGES = {  # name: (width_pt, height_pt) landscape
    "tabloid": (1224, 792), "ledger": (1224, 792), "a3": (1190.55, 841.89),
    "a2": (1683.78, 1190.55), "18x24": (1728, 1296), "24x36": (2592, 1728),
    "letter": (792, 612), "a4": (841.89, 595.28),
}

# Per-generation box geometry at the 1224-pt design width.
GEN = {
    0: dict(h=80, w=214),
    1: dict(h=70, w=196),
    2: dict(h=66, w=176),
    3: dict(h=58, w=126),
    4: dict(h=54, w=None),
    5: dict(h=104, w=None),   # outermost row: cards stand on end
}
GEN_COMPACT = {0: dict(h=72, w=214), 1: dict(h=62, w=196), 2: dict(h=60, w=176), 3: dict(h=54, w=126),
               4: dict(h=50, w=None), 5: dict(h=104, w=None)}


class Renderer:
    def __init__(self, tree: Tree, focus: Person, up=4, down=3, page="tabloid",
                 title=None, subtitle=None, show_ids=True, redact_living=False,
                 background=True, note=None, couple: Family | None = None,
                 style="classic", desc_layout="tree", tree_art=None, bg_image=None, bg_opacity=0.32):
        self.t, self.f = tree, focus
        self.up, self.down = max(1, min(5, up)), max(0, min(3, down))
        pw, ph = PAGES[page]
        self.W = 1224.0                     # design width; everything scales to page
        self.H = self.W * ph / pw
        self.page_pt = (pw, ph)
        self.title, self.subtitle = title, subtitle
        self.ids, self.redact, self.bg, self.note = show_ids, redact_living, background, note
        self.svg: list[str] = []
        self.couple = couple
        self.theme = dict(THEMES[style])
        if tree_art is not None:
            self.theme["tree_art"] = tree_art
        PALETTE.clear(); PALETTE.update(self.theme["palette"])
        self.desc_layout = desc_layout
        self.bg_image, self.bg_opacity = bg_image, bg_opacity
        if bg_image and tree_art is None:
            self.theme["tree_art"] = 0.0   # the photo replaces the drawn tree
        self.warnings: list[str] = []

    # ── helpers ──
    def text(self, x, y, s, size, font=FONT_TEXT, fill=None, anchor="middle", weight=None,
             style=None, track=None, caps=False, opacity=None):
        a = [f'x="{x:.2f}"', f'y="{y:.2f}"', f'font-size="{size:.2f}"', f'font-family="{font}"',
             f'fill="{fill or PALETTE["ink"]}"', f'text-anchor="{anchor}"']
        if weight: a.append(f'font-weight="{weight}"')
        if style: a.append(f'font-style="{style}"')
        if track: a.append(f'letter-spacing="{track}"')
        if opacity: a.append(f'opacity="{opacity}"')
        self.svg.append(f'<text {" ".join(a)}>{esc(s.upper() if caps else s)}</text>')

    def side_color(self, n: int) -> str:
        if n == 1:
            return PALETTE["gold"]
        top = n
        while top > 3:
            top //= 2
        return PALETTE["sage"] if top == 2 else PALETTE["clay"]

    # ── person card ──
    def card(self, cx, y, w, h, p: Person | None, gen: int, color: str, focus=False):
        if gen >= 5:  # narrow outer-row card: draw the frame upright, set the text sideways
            self.card_shape(cx - w / 2, y, w, h, color if p else PALETTE["faint"], False) if p else \
                self.svg.append(f'<rect x="{cx - w/2:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" fill="none" '
                                f'stroke="{PALETTE["faint"]}" stroke-width="0.5" stroke-dasharray="2 2.5"/>')
            cy = y + h / 2
            self.svg.append(f'<g transform="rotate(-90 {cx:.2f} {cy:.2f})">')
            if p is None:
                self.text(cx, cy + 2.5, "not yet identified", 6.0, style="italic", fill=PALETTE["faint"])
            else:
                self.card_text(cx, cy - w / 2, h, w, p, gen)
            self.svg.append("</g>")
            return
        x = cx - w / 2
        S = self.svg
        if p is None:
            S.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" fill="none" '
                     f'stroke="{PALETTE["faint"]}" stroke-width="0.5" stroke-dasharray="2 2.5" opacity="0.8"/>')
            self.text(cx, y + h / 2 + 3, "not yet identified" if gen <= 3 else "unknown",
                      7.2 if gen <= 3 else 6.4, style="italic", fill=PALETTE["faint"])
            return
        self.card_shape(x, y, w, h, color, focus)
        self.card_text(cx, y, w, h, p, gen)

    def card_text(self, cx, y, w, h, p: Person, gen: int):
        pad = 4 if gen >= 5 else 7 if gen >= 3 else 10
        iw = w - 2 * pad
        ls = lifespan(p, self.redact)
        hide = self.redact and is_living(p)
        if gen == 0:
            sizes = dict(given=15.5, sur=10.5, l1=8.6, l2=8.6, id=6.2)
        elif gen <= 2:
            sizes = dict(given=11.6, sur=8.2, l1=7.4, l2=7.4, id=5.6)
        elif gen == 3:
            sizes = dict(given=9.4, sur=7.0, l1=7.0, id=5.4)
        elif gen == 4:
            sizes = dict(given=8.0, sur=6.2, l1=6.3, id=5.0)
        else:
            sizes = dict(given=6.4, sur=5.0, l1=5.3, id=4.4)
        lines = []  # (text, size, kwargs)
        lines.append((fit_given(p.given or "—", iw, sizes["given"]), sizes["given"],
                      dict(font=FONT_DISPLAY, weight="600")))
        trk = sizes["sur"] * 0.12
        lines.append((fit_text(p.surname or "", iw, sizes["sur"], W_CAPS, trk), sizes["sur"],
                      dict(font=FONT_TEXT, caps=True, track=f"{trk:.2f}", fill=PALETTE["ink2"])))
        if gen <= 2 and not hide:
            b = " · ".join(x for x in (long_date(p.birth.date) if gen == 0 else short_date(p.birth.date),
                                       short_place(p.birth.place, 2 if gen == 0 else 2)) if x)
            d = " · ".join(x for x in (long_date(p.death.date) if gen == 0 else short_date(p.death.date),
                                       short_place(p.death.place, 2)) if x)
            if b:
                lines.append((fit_text("b. " + b, iw, sizes["l1"]), sizes["l1"], dict(style="italic", fill=PALETTE["ink2"])))
            if d:
                lines.append((fit_text("d. " + d, iw, sizes["l2"]), sizes["l2"], dict(style="italic", fill=PALETTE["ink2"])))
            if not (p.birth.place or p.death.place) and ls:
                lines = lines[:2] + [(ls, sizes["l1"], dict(style="italic", fill=PALETTE["ink2"]))]
            elif not b and not d and ls:
                lines.append((ls, sizes["l1"], dict(style="italic", fill=PALETTE["ink2"])))
        elif ls:
            lines.append((fit_text(ls, iw, sizes["l1"]), sizes["l1"], dict(fill=PALETTE["ink2"])))
        if self.theme["glyphs"]:
            lines = lines[:2]
            for run in self.date_items(p, gen <= 2):
                lines.append(("", sizes["l1"], dict(_items=run, fill=PALETTE["ink2"])))
        if self.ids and p.fsid:
            lines.append((p.fsid, sizes["id"], dict(fill=PALETTE["faint"], track="0.6")))
        # vertical layout: distribute baselines inside the card
        lf = 1.15 if gen >= 5 else 1.22
        heights = [s * lf for _, s, _ in lines]
        total = sum(heights)
        if total > h - 6:  # drop lowest-priority lines until it fits
            while total > h - 6 and len(lines) > 2:
                drop = 2 if len(lines) > 3 else len(lines) - 1
                lines.pop(drop if not (self.ids and p.fsid) else len(lines) - 2)
                heights = [s * lf for _, s, _ in lines]
                total = sum(heights)
        yy = y + (h - total) / 2
        for (s, size, kw), lh in zip(lines, heights):
            yy += lh
            if "_items" in kw:
                self.glyph_line(cx, yy - lh * 0.24, kw["_items"], size, kw.get("fill"))
            else:
                self.text(cx, yy - lh * 0.24, s, size, **kw)

    def card_shape(self, x, y, w, h, color, focus):
        S, P, kind = self.svg, PALETTE, self.theme["card"]
        cx = x + w / 2
        def cart(x, y, w, h, r):
            return (f"M{x + r:.2f},{y:.2f} H{x + w - r:.2f} A{r},{r} 0 0 0 {x + w:.2f},{y + r:.2f} V{y + h - r:.2f} "
                    f"A{r},{r} 0 0 0 {x + w - r:.2f},{y + h:.2f} H{x + r:.2f} A{r},{r} 0 0 0 {x:.2f},{y + h - r:.2f} "
                    f"V{y + r:.2f} A{r},{r} 0 0 0 {x + r:.2f},{y:.2f}Z")
        if kind == "cartouche":
            r = min(7.0, h * 0.14)
            S.append(f'<path d="{cart(x, y, w, h, r)}" fill="{P["card"]}" stroke="{color}" stroke-width="{1.1 if focus else 0.8}"/>')
            S.append(f'<path d="{cart(x + 3, y + 3, w - 6, h - 6, max(2, r - 2))}" fill="none" stroke="{color}" stroke-width="0.35"/>')
            S.append(f'<path d="M{cx:.2f},{y - 3.4:.2f} l3.4,3.4 l-3.4,3.4 l-3.4,-3.4Z" fill="{color}"/>')
            if focus:
                S.append(f'<path d="{cart(x - 3, y - 3, w + 6, h + 6, r + 2)}" fill="none" stroke="{color}" stroke-width="0.5"/>')
        elif kind == "woodcut":
            S.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{P["card"]}" '
                     f'stroke="{P["ink"]}" stroke-width="{1.6 if focus else 1.0}"/>')
            S.append(f'<rect x="{x + 2.5:.2f}" y="{y + 2.5:.2f}" width="{w - 5:.2f}" height="{h - 5:.2f}" fill="none" '
                     f'stroke="{color}" stroke-width="0.5"/>')
            S.append(f'<rect x="{cx - 8:.2f}" y="{y - 3:.2f}" width="16" height="6" fill="{P["ink"]}"/>'
                     + leaf_filled(cx, y, 0, 6, 1.8, P["paper"], P["ink"]) + leaf_filled(cx, y, math.pi, 6, 1.8, P["paper"], P["ink"]))
        else:
            S.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3.5" '
                     f'fill="{P["card"]}" stroke="{color}" stroke-width="{1.0 if focus else 0.7}"/>')
            if focus:
                S.append(f'<rect x="{x + 3:.2f}" y="{y + 3:.2f}" width="{w - 6:.2f}" height="{h - 6:.2f}" rx="2" '
                         f'fill="none" stroke="{color}" stroke-width="0.4"/>')
            else:
                S.append(f'<path d="M{cx - 9:.2f},{y:.2f} H{cx + 9:.2f}" stroke="{color}" stroke-width="2"/>')

    def glyph_line(self, cx, y, items, size, fill, style=None):
        """Centre a run of (glyph, text) items, e.g. [('b','1886'), ('d','1952')]."""
        gw, gap, sep = size * 0.7, size * 0.28, size * 0.95
        parts = []
        for k, (g, t) in enumerate(items):
            parts.append((g, t, (gw + (gap if t else 0) if g else 0) + tw(t, size)))
        total = sum(p[2] for p in parts) + sep * (len(parts) - 1)
        x = cx - total / 2
        for g, t, wdt in parts:
            if g:
                self.svg.append(glyph(g, x + gw / 2, y - size * 0.32, size, PALETTE["gold"]))
                x += gw + (gap if t else 0)
            if t:
                self.text(x, y, t, size, anchor="start", fill=fill, style=style)
            x += tw(t, size) + sep

    def date_items(self, p: Person, with_places: bool):
        """Event runs for glyph mode: one or two lines of (glyph, text)."""
        if self.redact and is_living(p):
            return [[(None, "Living")]]
        b, d = short_date(p.birth.date), short_date(p.death.date)
        if with_places and (p.birth.place or p.death.place):
            lines = []
            if b or p.birth.place:
                lines.append([("b", " · ".join(x for x in (b, short_place(p.birth.place)) if x))])
            if d or p.death.place:
                lines.append([("d", " · ".join(x for x in (d, short_place(p.death.place)) if x))])
            return lines
        run = []
        if b:
            run.append(("b", b))
        if d:
            run.append(("d", d))
        elif is_living(p):
            run.append((None, "Living"))
        elif p.living is False or b:
            run.append(("d", ""))
        return [run] if run else []

    # ── main ──
    def render(self) -> str:
        W = self.W
        P = PALETTE
        mx = 70.0                       # side margin for tree content
        CW = W - 2 * mx
        cpl = self.couple
        anc = self.t.ahnentafel_family(cpl, self.up) if cpl else self.t.ahnentafel(self.f, self.up)
        depth = self.up
        while depth > 1 and not any(n in anc for n in range(2 ** depth, 2 ** (depth + 1))):
            depth -= 1                  # don't reserve rows for empty generations
        if depth >= 5:                  # five generations: tighten rows so everything fits the sheet
            GEN.update(GEN_COMPACT)
            self.DS = {1: (150.0, 56.0), 2: (134.0, 50.0), 3: (118.0, 46.0)}
        # rows (top = oldest)
        vgap = 26.0
        top = 142.0 if self.theme.get("banner") else 132.0
        def place_rows(vgap):
            row_y, cur = {}, top
            for g in range(depth, 0 if cpl else -1, -1):
                row_y[g] = cur
                cur += GEN[g]["h"] + vgap
            # In couple mode the pair sits on row I; their join point hangs below it.
            return row_y, (row_y[1] + GEN[1]["h"] + 16 if cpl else row_y[0] + GEN[0]["h"])
        row_y, tree_bottom = place_rows(vgap)

        def slot(n):
            g = n.bit_length() - 1
            i = n - 2 ** g
            sw = CW / 2 ** g
            cx = mx + sw * (i + 0.5)
            w = GEN[g]["w"] or (sw - (3 if g >= 5 else 5))
            w = min(w, sw - (3 if g >= 5 else 5 if g >= 4 else 10))
            return g, cx, w

        # ── descendants block (laid out first so the page can grow if needed) ──
        desc_top = tree_bottom + 30
        body_top = desc_top + 30
        footer_y = None
        tplan = None
        if self.down > 0 and self.desc_layout == "tree":
            tplan = self.desc_tree_plan(self.desc_roots(), CW)
        lines = [] if tplan else self.descendant_lines()
        cols_plan = None
        for scale in (1.0, 0.92, 0.85, 0.78):
            avail = self.H - 58 - body_top
            for ncol in (1, 2, 3, 4):
                colw = min(CW / ncol, 440 if ncol == 1 else CW / ncol)
                laid = self.flow(lines, ncol, colw - 22, avail, scale)
                if laid is not None:
                    cols_plan = (ncol, colw, scale, laid)
                    break
            if cols_plan:
                break
        if cols_plan is None and lines:
            # Grow the page downward rather than shrink text below legibility.
            ncol, scale = 4, 0.78
            colw = CW / ncol
            need = self.flow(lines, ncol, colw - 22, 10 ** 6, scale, need_height=True)
            self.H = body_top + need + 58
            self.warnings.append("descendants exceed the page; canvas was extended — print scaled or choose a larger --page")
            cols_plan = (ncol, colw, scale, self.flow(lines, ncol, colw - 22, self.H - 58 - body_top, scale))
        if cols_plan and lines and cols_plan[2] == 1.0:
            # Short descendant list: give the pedigree the spare height instead of leaving a void.
            used = max(sum(l[3] for l in c) for c in cols_plan[3])
            slack = (self.H - 58 - body_top) - used - 24
            if slack > 30:
                vgap += min(30.0, slack * 0.7 / (depth + 1))
                row_y, tree_bottom = place_rows(vgap)
                desc_top = tree_bottom + 30 + min(20.0, slack * 0.1)
                body_top = desc_top + 30
        if tplan:
            avail = self.H - 54 - tree_bottom
            need = tplan["height"] + 8
            rows = depth - 1 if cpl else depth      # number of gaps that sit above tree_bottom
            if need > avail:
                vgap = max(12.0, vgap - (need - avail) / max(1, rows) - 0.01)
                row_y, tree_bottom = place_rows(vgap)
                if need > self.H - 54 - tree_bottom + 0.5:
                    self.H = tree_bottom + need + 54
                    self.warnings.append("descendant tree exceeds the page; canvas was extended")
            else:
                vgap += min(30.0, (avail - need) * 0.75 / max(1, rows))
                row_y, tree_bottom = place_rows(vgap)
        H = self.H
        footer_y = H - (34 if self.theme["border"] == "fine" else 44)

        S = self.svg
        # ── page & border ──
        if self.bg:
            S.append(f'<rect x="0" y="0" width="{W}" height="{H:.2f}" fill="{P["paper"]}"/>')
        if self.theme.get("aged"):
            S.append(aged_paper(W, H, P))
        if self.bg_image:
            import base64, mimetypes
            mime = mimetypes.guess_type(str(self.bg_image))[0] or "image/jpeg"
            data = base64.b64encode(Path(self.bg_image).read_bytes()).decode()
            S.append(f'<defs><clipPath id="ft-photo"><rect x="38" y="38" width="{W - 76}" height="{H - 76:.2f}"/></clipPath>'
                     f'<radialGradient id="ft-photo-fade" cx="50%" cy="50%" r="70%"><stop offset="55%" stop-color="#fff"/>'
                     f'<stop offset="100%" stop-color="#000"/></radialGradient>'
                     f'<mask id="ft-photo-mask"><rect width="{W}" height="{H:.2f}" fill="url(#ft-photo-fade)"/></mask></defs>'
                     f'<g clip-path="url(#ft-photo)" mask="url(#ft-photo-mask)" style="mix-blend-mode:multiply" opacity="{self.bg_opacity}">'
                     f'<image href="data:{mime};base64,{data}" x="38" y="38" width="{W - 76}" height="{H - 76:.2f}" '
                     f'preserveAspectRatio="xMidYMid slice" style="filter:sepia(0.6) contrast(1.05)"/></g>')
        if self.theme["tree_art"]:
            S.append(f'<defs><clipPath id="ft-inner"><rect x="36" y="36" width="{W - 72}" height="{H - 72:.2f}"/></clipPath></defs>'
                     f'<g clip-path="url(#ft-inner)">'
                     + woodcut_tree(W / 2, H - 62, top - 6, CW / 2, P["ink"], P["paper"], self.theme["tree_art"]) + '</g>')
        S.append(border(self.theme["border"], W, H, P))
        if self.theme["sprigs"]:
            for (x, y, sx, sy) in ((30, 30, 1, 1), (W - 30, 30, -1, 1), (30, H - 30, 1, -1), (W - 30, H - 30, -1, -1)):
                S.append(corner(x, y, sx, sy, P["sage"]))
        # ── title ──
        f = self.f
        if cpl:
            hu, wi = anc.get(2), anc.get(3)
            title = self.title or f"The {(hu or wi or f).surname} Family"
            sub = self.subtitle or " & ".join(p.full for p in (hu, wi) if p) + " · their ancestry and descendants"
        else:
            title = self.title or f"The Family of {f.full}"
            sub = self.subtitle or " · ".join(x for x in (lifespan(f, self.redact), short_place(f.birth.place, 2)) if x)
        if self.theme.get("banner"):
            self.text(W / 2, 80, title, 44, font=self.theme["title_font"], fill=P["ink"])
            S.append(swash(W / 2, 92, min(230, tw(title, 44, 0.36) * 0.62), P["ink"]))
            if sub:
                bw = tw(sub.upper(), 7.6, W_CAPS, 2.0) + 46
                S.append(ribbon(W / 2, 110, bw, 15, P["card"], P["ink"]))
                self.text(W / 2, 112.8, sub, 7.6, caps=True, track="2.0", fill=P["ink"])
        else:
            self.text(W / 2, 72, title, 30, font=FONT_DISPLAY, weight="500", style="italic")
            flo_w = min(150, tw(title, 30) * 0.42)
            S.append(flourish(W / 2, 86, flo_w, P["gold"]))
            if sub:
                self.text(W / 2, 104, sub, 8.4, caps=True, track="2.2", fill=P["ink2"])
        # side labels
        if cpl:
            lt = f"Family of {anc[2].full}" if 2 in anc else ""
            rt = f"Family of {anc[3].full}" if 3 in anc else ""
        else:
            lt, rt = "Paternal ancestry", "Maternal ancestry"
        self.text(mx + CW / 4, top - 10, lt, 6.8, caps=True, track="2.4", fill=P["sage"])
        self.text(mx + 3 * CW / 4, top - 10, rt, 6.8, caps=True, track="2.4", fill=P["clay"])
        # generation numerals in the margin
        romans = ["", "I", "II", "III", "IV", "V"]
        for g in range(1, depth + 1):
            yc = row_y[g] + GEN[g]["h"] / 2
            self.text(46, yc + 3, romans[g], 8.5, font=FONT_DISPLAY, fill=P["gold"], weight="600")
            self.text(W - 46, yc + 3, romans[g], 8.5, font=FONT_DISPLAY, fill=P["gold"], weight="600")

        # ── connectors ──
        S.append(f'<g fill="none" stroke="{P["line"]}" stroke-width="0.7" stroke-linecap="round">')
        dots = []
        for n in range(2 if cpl else 1, 2 ** depth):
            if n not in anc:
                continue
            g, cx, w = slot(n)
            if 2 * n not in anc and 2 * n + 1 not in anc:
                continue
            _, fx, _ = slot(2 * n)
            _, mx2, _ = slot(2 * n + 1)
            pb = row_y[g + 1] + GEN[g + 1]["h"]
            mid = pb + vgap / 2
            S.append(f'<path d="M{cx:.2f},{row_y[g]:.2f} V{mid:.2f} M{fx:.2f},{pb:.2f} V{mid:.2f} H{mx2:.2f} V{pb:.2f}"/>')
            dots.append((cx, mid))
        S.append("</g>")
        for (x, y) in dots:
            S.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.5" fill="{P["gold"]}"/>')

        # ── ancestor cards ──
        for n in range(2, 2 ** (depth + 1)):
            g, cx, w = slot(n)
            if n in anc:
                self.card(cx, row_y[g], w, GEN[g]["h"], anc[n], g,
                          P["gold"] if cpl and n < 4 else self.side_color(n), focus=bool(cpl and n < 4))
            elif n // 2 in anc:     # a known person whose parent is missing: show the gap
                self.card(cx, row_y[g], w, GEN[g]["h"], None, g, P["faint"])

        # ── focus + spouses ──
        g0 = GEN[0]
        cx0 = W / 2
        if cpl:
            # join the couple: drops from both cards, a gold link, the marriage year
            pb = row_y[1] + GEN[1]["h"]
            jy = pb + 16
            _, hx, _ = slot(2)
            _, wx, _ = slot(3)
            S.append(f'<path d="M{hx:.2f},{pb:.2f} V{jy - 1.4:.2f} H{wx:.2f} V{pb:.2f} M{hx:.2f},{jy + 1.4:.2f} H{wx:.2f}" '
                     f'stroke="{P["gold"]}" stroke-width="0.6" fill="none"/>')
            S.append(f'<circle cx="{cx0}" cy="{jy}" r="2.2" fill="{P["gold"]}"/>')
            md = short_date(cpl.marr.date)
            if self.theme["glyphs"]:
                S.append(f'<circle cx="{cx0}" cy="{jy - 11}" r="8" fill="{P["paper"]}"/>' + glyph("m", cx0, jy - 11, 13, P["gold"]))
                if md:
                    self.text(cx0 + 14, jy - 7, md, 7.4, anchor="start", style="italic", fill=P["ink2"])
            else:
                self.text(cx0, jy - 6, f"married {md}" if md else "married", 7.4, style="italic", fill=P["ink2"])
            y0, g0 = jy, dict(h=0, w=0)
        else:
            y0 = row_y[0]
        unions = [] if cpl else self.t.unions(f)
        sides = [1, -1, 1, -1]
        for k, (sp, fam, _) in enumerate(unions[:2]):
            sgn = sides[k]
            sw, sh = 176.0, 66.0
            scx = cx0 + sgn * (g0["w"] / 2 + 58 + sw / 2)
            sy = y0 + (g0["h"] - sh) / 2
            ly = y0 + g0["h"] / 2
            x1, x2 = cx0 + sgn * g0["w"] / 2, scx - sgn * sw / 2
            S.append(f'<path d="M{x1:.2f},{ly - 1.4:.2f} H{x2:.2f} M{x1:.2f},{ly + 1.4:.2f} H{x2:.2f}" stroke="{P["gold"]}" stroke-width="0.6" fill="none"/>')
            md = short_date(fam.marr.date)
            self.text((x1 + x2) / 2, ly - 6, f"m. {md}" if md else "m.", 7.2, style="italic", fill=P["ink2"])
            if sp:
                self.card(scx, sy, sw, sh, sp, 2, P["gold"])
        if not cpl:
            self.card(cx0, y0, g0["w"], g0["h"], f, 0, P["gold"], focus=True)

        # ── descendants ──
        if tplan:
            self.draw_desc_tree(tplan, cx0, y0 + g0["h"], tree_bottom)
        elif self.down > 0:
            S.append(f'<path d="M{cx0},{y0 + g0["h"]:.2f} V{desc_top - 9:.2f}" stroke="{P["line"]}" stroke-width="0.7"/>')
            # divider ornament with heading
            label = "Descendants"
            lw = tw(label.upper(), 7.6, W_CAPS, 2.6) / 2 + 18
            S.append(f'<g stroke="{P["gold"]}" stroke-width="0.5" fill="none">'
                     f'<path d="M{mx + 40:.2f},{desc_top:.2f} H{cx0 - lw - 70:.2f} M{cx0 + lw + 70:.2f},{desc_top:.2f} H{W - mx - 40:.2f}"/></g>')
            S.append(f'<g fill="none" stroke="{P["sage"]}" stroke-width="0.55" stroke-linecap="round" opacity="0.8">'
                     f'<g transform="translate({cx0 - lw},{desc_top}) scale(-1,1)">{sprig(64, 4, 0.05, 8, 1)}</g>'
                     f'<g transform="translate({cx0 + lw},{desc_top})">{sprig(64, 4, 0.05, 8, 1)}</g></g>')
            self.text(cx0, desc_top + 2.6, label, 7.6, caps=True, track="2.6", fill=P["ink2"])
            if not lines:
                self.text(cx0, body_top + 10, "No descendants recorded", 9, style="italic", fill=P["faint"])
            else:
                ncol, colw, scale, laid = cols_plan
                if ncol == 1:  # shrink-wrap a single column so it sits visually centred
                    widest = max(self._segw(segs, size) + self.INDENT.get(lvl % 10, 0) + 11
                                 for (lvl, segs, size, _) in laid[0])
                    colw = min(colw, widest + 28)
                bx = W / 2 - ncol * colw / 2
                for ci, col in enumerate(laid):
                    x0 = bx + ci * colw + 14
                    if ci > 0:
                        hgt = max(sum(lh for *_, lh in c) for c in laid)
                        S.append(f'<path d="M{bx + ci * colw:.2f},{body_top - 6:.2f} v{hgt:.2f}" stroke="{P["gold"]}" stroke-width="0.35" opacity="0.6"/>')
                    yy = body_top
                    for (lvl, segs, size, lh) in col:
                        yy += lh
                        self.outline_line(x0, yy - lh * 0.28, lvl, segs, size)

        # ── footer ──
        today = _dt.date.today().strftime("%-d %B %Y")
        foot = self.note or ("Compiled from FamilySearch Family Tree records"
                             + (" · IDs refer to familysearch.org/tree/person/details/ID" if self.ids else "")
                             + f" · Prepared {today}")
        self.text(W / 2, footer_y, foot, 6.6, fill=P["faint"], track="0.4", style="italic")

        pw, ph = self.page_pt
        ph_eff = pw * H / W
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}" '
                f'width="{pw / 72:.3f}in" height="{ph_eff / 72:.3f}in">'
                f'<title>{esc(title)}</title>'
                f'<style>@import url("{FONTS_URL.replace("&", "&amp;")}");</style>')
        out = head + "".join(S) + "</svg>"
        if self.theme.get("fonts"):
            out = out.replace(FONT_DISPLAY, self.theme["fonts"][0]).replace(FONT_TEXT, self.theme["fonts"][1])
        return out

    # ── descendants as a connected tree ──
    DS = {1: (150.0, 64.0), 2: (134.0, 58.0), 3: (118.0, 52.0)}
    SG, HG, VG = 26.0, 18.0, 28.0      # spouse gap, sibling gap, row gap

    def desc_roots(self):
        def build(p, lvl):
            us = self.t.unions(p)
            sp = next((u[0] for u in us if u[0]), None)
            kids = [k for u in us for k in u[2]]
            return dict(p=p, sp=sp, lvl=lvl,
                        kids=[build(k, lvl + 1) for k in kids] if lvl < self.down else [])
        if self.couple:
            fam = self.couple
            kids = sorted((self.t.people[c] for c in fam.children if c in self.t.people),
                          key=lambda c: year(c.birth.date) or 9999)
        else:
            kids = [k for u in self.t.unions(self.f) for k in u[2]]
        return [build(k, 1) for k in kids]

    def desc_tree_plan(self, roots, CW):
        if not roots:
            return None
        def sub(n, sc):
            w = self.DS[n["lvl"]][0] * sc
            n["w"], n["h"] = w, self.DS[n["lvl"]][1]
            n["uw"] = w + (self.SG + w if n["sp"] else 0)
            span = sum(sub(k, sc) for k in n["kids"]) + self.HG * max(0, len(n["kids"]) - 1)
            n["sub"] = max(n["uw"], span)
            n["span"] = span
            return n["sub"]
        for sc in (1.0, 0.9, 0.8, 0.7, 0.62):
            total = sum(sub(r, sc) for r in roots) + self.HG * (len(roots) - 1)
            if total <= CW:
                break
        else:
            return None
        def levels(n):
            return max([n["lvl"]] + [levels(k) for k in n["kids"]])
        nl = max(levels(r) for r in roots)
        height = 26 + sum(self.DS[l][1] for l in range(1, nl + 1)) + self.VG * (nl - 1)
        return dict(roots=roots, total=total, levels=nl, height=height)

    def draw_desc_tree(self, plan, ax, ay, top):
        P, S = PALETTE, self.svg
        ytop = {1: top + 26}
        for l in range(2, plan["levels"] + 1):
            ytop[l] = ytop[l - 1] + self.DS[l - 1][1] + self.VG

        def place(n, left):
            if n["kids"]:
                cl = left + (n["sub"] - n["span"]) / 2
                for k in n["kids"]:
                    place(k, cl)
                    cl += k["sub"] + self.HG
                centre = left + (n["sub"] - n["span"]) / 2 + n["span"] / 2
            else:
                centre = left + n["sub"] / 2
            off = n["w"] + self.SG / 2 if n["sp"] else n["w"] / 2
            ux = min(max(centre - off, left), left + n["sub"] - n["uw"])
            n["x"], n["anchor"] = ux, ux + off

        left = self.W / 2 - plan["total"] / 2
        for r in plan["roots"]:
            place(r, left)
            left += r["sub"] + self.HG

        def drop(kids, ax, ay, lvl):
            if not kids:
                return
            mid = ytop[lvl] - (13 if lvl == 1 else self.VG / 2)
            xs = [k["x"] + k["w"] / 2 for k in kids]
            d = f"M{ax:.2f},{ay:.2f} V{mid:.2f} M{min(xs + [ax]):.2f},{mid:.2f} H{max(xs + [ax]):.2f} "
            d += " ".join(f"M{x:.2f},{mid:.2f} V{ytop[lvl]:.2f}" for x in xs)
            S.append(f'<path d="{d}" fill="none" stroke="{P["line"]}" stroke-width="0.7" stroke-linecap="round"/>')
            S.append(f'<circle cx="{ax:.2f}" cy="{mid:.2f}" r="1.5" fill="{P["gold"]}"/>')

        def draw(n):
            l, w, h = n["lvl"], n["w"], n["h"]
            y = ytop[l]
            gen = 3 if l <= 2 else 4
            if n["sp"]:
                x1, x2, ly = n["x"] + w, n["x"] + w + self.SG, y + h / 2
                S.append(f'<path d="M{x1:.2f},{ly - 1.3:.2f} H{x2:.2f} M{x1:.2f},{ly + 1.3:.2f} H{x2:.2f}" stroke="{P["gold"]}" stroke-width="0.6"/>')
                if self.theme["glyphs"]:
                    S.append(glyph("m", (x1 + x2) / 2, ly - 7, 9, P["gold"]))
                else:
                    self.text((x1 + x2) / 2, ly - 4, "m.", 6.6, style="italic", fill=P["ink2"])
                self.card(n["x"] + w + self.SG + w / 2, y, w, h, n["sp"], gen, P["line"])
            self.card(n["x"] + w / 2, y, w, h, n["p"], gen, P["gold"])
            if n["kids"]:
                if n["sp"]:
                    drop(n["kids"], n["anchor"], y + h / 2 + 1.3, l + 1)
                else:
                    drop(n["kids"], n["anchor"], y + h, l + 1)
                for k in n["kids"]:
                    draw(k)

        drop(plan["roots"], ax, ay, 1)
        for r in plan["roots"]:
            draw(r)

    # ── descendants outline ──
    def descendant_lines(self):
        """Return blocks: list of lists of (level, segments). One block per child of focus."""
        if self.down == 0:
            return []
        blocks = []
        if self.couple:
            fam = self.couple
            kids = sorted((self.t.people[c] for c in fam.children if c in self.t.people),
                          key=lambda c: year(c.birth.date) or 9999)
            unions = [(None, fam, kids)]
        else:
            unions = self.t.unions(self.f)
        multi = sum(1 for u in unions if u[2]) > 1

        def person_segs(p: Person, spouse_of: Person | None = None):
            segs = [("name", p.full)]
            ls = lifespan(p, self.redact)
            if ls:
                segs.append(("date", "  " + ls))
            return segs

        def walk(p: Person, lvl: int, block: list):
            unions_p = self.t.unions(p)
            segs = person_segs(p)
            sp_segs = []
            for sp, fam, _ in unions_p:
                if sp:
                    sp_segs.append([("m", "m. "), ("spouse", sp.full)] +
                                   ([("date", "  " + lifespan(sp, self.redact))] if lifespan(sp, self.redact) else []))
            block.append((lvl, segs, sp_segs))
            if lvl < self.down:
                for sp, fam, kids in unions_p:
                    for k in kids:
                        walk(k, lvl + 1, block)

        for sp, fam, kids in unions:
            if not kids:
                continue
            if multi:
                blocks.append([(0, [("group", f"With {sp.full}" if sp else "With unknown partner")], [])])
            for k in kids:
                b = []
                walk(k, 1, b)
                blocks.append(b)
        return blocks

    SIZES = {0: 8.6, 1: 10.6, 2: 9.4, 3: 8.5}
    INDENT = {0: 0, 1: 0, 2: 15, 3: 30}

    def _expand(self, block, width, scale):
        """Expand a block into concrete lines: (level, segs, size, line_height)."""
        out = []
        for lvl, segs, sp_list in block:
            size = self.SIZES[lvl] * scale
            ind = self.INDENT[lvl] * scale + 11
            first = list(segs)
            rest = []
            for sp in sp_list:
                joined = first + [("sep", "  ·  ")] + sp
                if not rest and self._segw(joined, size) <= width - ind:
                    first = joined
                else:
                    rest.append(sp)
            lh = size * (1.62 if lvl == 1 else 1.42)
            if lvl == 1 and out:
                lh += 3 * scale  # breathing room between children
            if lvl == 0:
                lh = size * 2.0
            out.append((lvl, first, size, lh))
            for sp in rest:
                out.append((lvl + 10, sp, size * 0.94, size * 1.34))  # continuation line
        return out

    @staticmethod
    def _segw(segs, size):
        return sum(tw(t, size, W_CAPS * 0.95 if k == "group" else W_SERIF) for k, t in segs)

    def flow(self, blocks, ncol, width, avail, scale, need_height=False):
        """Greedy column fill keeping each child's family together when possible.
        Returns list of columns (each a list of lines) or None if it doesn't fit."""
        expanded = [self._expand(b, width, scale) for b in blocks]
        if need_height:
            total = sum(sum(l[3] for l in e) for e in expanded)
            target = total / ncol
            best = max(sum(l[3] for l in e) for e in expanded)
            return max(target * 1.25, best) + 20
        # balanced target: try smallest per-column height that works
        total = sum(sum(l[3] for l in e) for e in expanded)
        for target in sorted({min(avail, total / ncol * f) for f in (1.0, 1.08, 1.18, 1.3, 1.5, 2.0, 99)}):
            cols = [[]]
            hcur = 0.0
            ok = True
            for i, e in enumerate(expanded):
                h = sum(l[3] for l in e)
                is_group = e and e[0][0] == 0
                nxt_h = sum(l[3] for l in expanded[i + 1]) if is_group and i + 1 < len(expanded) else 0
                if hcur > 0 and hcur + h + nxt_h > target + 0.01:
                    if len(cols) == ncol:
                        ok = False
                        break
                    cols.append([])
                    hcur = 0.0
                if h > avail + 0.01:   # single family taller than the column: split it
                    for l in e:
                        if hcur + l[3] > avail:
                            if len(cols) == ncol:
                                ok = False
                                break
                            cols.append([])
                            hcur = 0.0
                        cols[-1].append(l)
                        hcur += l[3]
                    if not ok:
                        break
                    continue
                cols[-1].extend(e)
                hcur += h
            if ok and all(sum(l[3] for l in c) <= avail + 0.01 for c in cols):
                # A lone level-1 entry at the top of a column needs no extra top gap.
                return cols
        return None

    def outline_line(self, x, y, lvl, segs, size):
        P = PALETTE
        cont = lvl >= 10
        base = lvl - 10 if cont else lvl
        ind = self.INDENT.get(base, 0) * (size / self.SIZES.get(base, size)) if not cont else \
            self.INDENT.get(base, 0) + 11 + 12
        xx = x + ind
        S = self.svg
        if base == 0:
            S.append(f'<text x="{xx:.2f}" y="{y:.2f}" font-family="{FONT_TEXT}" font-size="{size:.2f}" '
                     f'fill="{P["gold"]}" letter-spacing="1.6">{esc(segs[0][1].upper())}</text>')
            return
        if not cont:
            if base == 1:
                S.append(f'<g fill="none" stroke="{P["sage"]}" stroke-width="0.5">{leaf(xx + 1, y - size * 0.32, -0.35, 7.5, 2.4)}</g>')
            elif base == 2:
                S.append(f'<circle cx="{xx + 3:.2f}" cy="{y - size * 0.32:.2f}" r="1.4" fill="{P["clay"]}" opacity="0.85"/>')
            else:
                S.append(f'<path d="M{xx + 1:.2f},{y - size * 0.32:.2f} h5" stroke="{P["gold"]}" stroke-width="0.7"/>')
            xx += 11
        spans = []
        for kind, t in segs:
            if kind == "name":
                spans.append(f'<tspan font-family="{FONT_DISPLAY}" font-weight="600" fill="{P["ink"]}">{esc(t)}</tspan>')
            elif kind == "spouse":
                spans.append(f'<tspan font-family="{FONT_DISPLAY}" font-weight="500" fill="{P["ink"]}">{esc(t)}</tspan>')
            elif kind == "m":
                spans.append(f'<tspan font-style="italic" fill="{P["ink2"]}">{esc(t)}</tspan>')
            elif kind == "date":
                spans.append(f'<tspan fill="{P["ink2"]}" font-size="{size * 0.88:.2f}">{esc(t)}</tspan>')
            else:
                spans.append(f'<tspan fill="{P["faint"]}">{esc(t)}</tspan>')
        S.append(f'<text x="{xx:.2f}" y="{y:.2f}" font-family="{FONT_TEXT}" font-size="{size:.2f}" '
                 f'xml:space="preserve">{"".join(spans)}</text>')


# ───────────────────────────── verification ────────────────────────────

def audit(tree: Tree, focus: Person, anc: dict[int, Person], up: int, down: int) -> list[str]:
    """Sanity checks on the extracted relationships — flags likely data errors."""
    issues = []
    for n, p in anc.items():
        if n == 1 or n // 2 not in anc:
            continue
        child = anc[n // 2]
        cy, py = year(child.birth.date), year(p.birth.date)
        if cy and py:
            gap = cy - py
            if gap < 13:
                issues.append(f"{p.full} born {py}, only {gap} yrs before child {child.full} ({cy})")
            if gap > (48 if p.sex == "F" or n % 2 else 75):
                issues.append(f"{p.full} born {py}, {gap} yrs before child {child.full} ({cy})")
        pd = year(p.death.date)
        if pd and cy and pd < cy - (1 if n % 2 == 0 else 0):
            issues.append(f"{p.full} died {pd}, before child {child.full} was born ({cy})")
        if n % 2 == 0 and p.sex == "F" or n % 2 == 1 and p.sex == "M":
            issues.append(f"{p.full} is in a {'father' if n % 2 == 0 else 'mother'} position but recorded as {p.sex}")
        if p.birth.date and p.death.date and year(p.death.date) and year(p.birth.date) and year(p.death.date) < year(p.birth.date):
            issues.append(f"{p.full}: death year precedes birth year")
    seen = {}
    for n, p in anc.items():
        if p.id in seen:
            issues.append(f"{p.full} appears at two pedigree positions ({seen[p.id]} and {n}) — pedigree collapse or a merge error")
        seen[p.id] = n
    # descendants
    def walk(p, lvl):
        if lvl >= down:
            return
        for sp, fam, kids in tree.unions(p):
            for k in kids:
                ky, py = year(k.birth.date), year(p.birth.date)
                if ky and py and not (13 <= ky - py <= 75):
                    issues.append(f"{k.full} born {ky}; parent {p.full} born {py} — check relationship")
                walk(k, lvl + 1)
    walk(focus, 0)
    missing_ids = [p.full for p in anc.values() if not p.fsid]
    if missing_ids:
        issues.append(f"{len(missing_ids)} ancestor(s) have no FamilySearch ID in the export (cannot be cross-checked): "
                      + ", ".join(missing_ids[:6]) + ("…" if len(missing_ids) > 6 else ""))
    return issues


# ───────────────────────────── outputs ─────────────────────────────────

def to_pdf_png(svg: str, svg_w_in: float, svg_h_in: float, pdf: Path | None, png: Path | None):
    """Print through headless Chromium (Node Playwright) so web fonts are embedded in the PDF."""
    import os, subprocess, tempfile
    page_html = (f'<!doctype html><html><head><meta charset="utf-8">'
                 f'<link rel="stylesheet" href="{FONTS_URL}">'
                 f'<style>@page{{size:{svg_w_in}in {svg_h_in}in;margin:0}}html,body{{margin:0;padding:0}}'
                 f'svg{{display:block;width:{svg_w_in}in;height:{svg_h_in}in}}</style></head>'
                 f'<body>{svg}</body></html>')
    js = r"""
const {chromium} = require('playwright');
const fs = require('fs');
const [htmlPath, w, h, pdf, png, mode] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch();
  if (mode === 'texture') {   // render a filter-only layer to JPEG at ~150 dpi
    const pg = await b.newPage({viewport: {width: Math.round(w*150), height: Math.round(h*150)}});
    await pg.setContent(fs.readFileSync(htmlPath, 'utf8'));
    await pg.screenshot({path: pdf, type: 'jpeg', quality: 82});
    await b.close(); return;
  }
  const pg = await b.newPage({viewport: {width: Math.round(w*96), height: Math.round(h*96)}, deviceScaleFactor: 2});
  await pg.setContent(fs.readFileSync(htmlPath, 'utf8'), {waitUntil: 'networkidle'});
  await pg.evaluate(() => document.fonts.ready);
  if (pdf) await pg.pdf({path: pdf, width: w + 'in', height: h + 'in', printBackground: true});
  if (png) await pg.screenshot({path: png, fullPage: true});
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
"""
    env = {**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", "") + ":" +
           subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()}
    with tempfile.TemporaryDirectory() as td:
        hp, jp = Path(td, "page.html"), Path(td, "print.js")
        jp.write_text(js, encoding="utf-8")
        m = re.search(r'<g id="ft-aged">.*?</g>(?=<)', svg, re.S)
        if m:  # filters print as enormous bitmaps; bake that one layer into a compressed image
            vb = re.search(r'viewBox="([^"]+)"', svg)[1]
            layer = (f'<!doctype html><html><body style="margin:0"><svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
                     f'style="display:block;width:100vw;height:100vh" preserveAspectRatio="none">'
                     f'<rect width="100%" height="100%" fill="{PALETTE["paper"]}"/>{m[0]}</svg></body></html>')
            lp, tj = Path(td, "layer.html"), Path(td, "tex.jpg")
            lp.write_text(layer, encoding="utf-8")
            subprocess.run(["node", str(jp), str(lp), f"{svg_w_in:.4f}", f"{svg_h_in:.4f}", str(tj), "", "texture"],
                           check=True, env=env)
            import base64
            _, _, vw, vh = vb.split()
            img = (f'<image href="data:image/jpeg;base64,{base64.b64encode(tj.read_bytes()).decode()}" '
                   f'x="0" y="0" width="{vw}" height="{vh}" preserveAspectRatio="none"/>')
            page_html = page_html.replace(m[0], img)
        hp.write_text(page_html, encoding="utf-8")
        subprocess.run(["node", str(jp), str(hp), f"{svg_w_in:.4f}", f"{svg_h_in:.4f}",
                        str(pdf.resolve()) if pdf else "", str(png.resolve()) if png else ""],
                       check=True, env=env)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="GEDCOM (.ged) or JSON export")
    ap.add_argument("--focus", required=True, help="FamilySearch ID, GEDCOM xref, or unique name fragment")
    ap.add_argument("--up", type=int, default=4, help="ancestor generations (1–5, default 4)")
    ap.add_argument("--down", type=int, default=3, help="descendant generations (0–3, default 3)")
    ap.add_argument("--page", default="tabloid", choices=sorted(PAGES), help="paper size, landscape (default tabloid 17×11 in)")
    ap.add_argument("--title")
    ap.add_argument("--subtitle")
    ap.add_argument("--note", help="replace the footer line")
    ap.add_argument("--couple", action="store_true",
                    help="centre on the focus person and their first spouse as a pair (both family lines above)")
    ap.add_argument("--style", default="classic", choices=sorted(THEMES), help="visual theme")
    ap.add_argument("--descendants", default="tree", choices=["tree", "list"],
                    help="draw descendants as connected cards (tree) or an indented outline (list)")
    ap.add_argument("--tree-art", type=float, help="opacity of the background woodcut tree (0 to hide)")
    ap.add_argument("--bg-image", type=Path, help="photo or engraving to fade in behind the chart")
    ap.add_argument("--bg-opacity", type=float, default=0.32, help="strength of --bg-image (default 0.32)")
    ap.add_argument("--no-ids", action="store_true", help="hide FamilySearch IDs")
    ap.add_argument("--redact-living", action="store_true", help="show 'Living' instead of dates for living people")
    ap.add_argument("--no-background", action="store_true", help="white paper (saves ink)")
    ap.add_argument("-o", "--out", type=Path, default=Path("family-tree.svg"))
    ap.add_argument("--pdf", type=Path)
    ap.add_argument("--png", type=Path)
    a = ap.parse_args(argv)

    tree = Tree.from_json(a.source) if a.source.suffix.lower() == ".json" else Tree.from_gedcom(a.source)
    focus = tree.find(a.focus)
    couple = None
    if a.couple:
        couple = next((fam for sp, fam, _ in tree.unions(focus) if sp), None)
        if couple is None:
            sys.exit("error: --couple needs the focus person to have a spouse")
    r = Renderer(tree, focus, a.up, a.down, a.page, a.title, a.subtitle,
                 not a.no_ids, a.redact_living, not a.no_background, a.note, couple,
                 a.style, a.descendants, a.tree_art, a.bg_image, a.bg_opacity)
    svg = r.render()
    a.out.write_text(svg, encoding="utf-8")
    if couple:
        anc = tree.ahnentafel_family(couple, r.up)
        known, slots = len(anc), 2 ** (r.up + 1) - 2
    else:
        anc = tree.ahnentafel(focus, r.up)
        known, slots = len(anc) - 1, 2 ** (r.up + 1) - 2
    print(f"focus: {focus.full} {lifespan(focus)} [{focus.fsid or focus.id}]")
    print(f"ancestors found: {known}/{slots} positions · wrote {a.out}")
    for w in r.warnings:
        print("warning:", w)
    issues = audit(tree, focus, anc, r.up, r.down)
    if issues:
        print("checks to review against FamilySearch:")
        for i in issues:
            print("  •", i)
    if a.pdf or a.png:
        pw, ph = r.page_pt
        to_pdf_png(svg, pw / 72, (pw * r.H / r.W) / 72, a.pdf, a.png)
        for x in (a.pdf, a.png):
            if x:
                print("wrote", x)


if __name__ == "__main__":
    main()
