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
             "&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap")


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
}


class Renderer:
    def __init__(self, tree: Tree, focus: Person, up=4, down=3, page="tabloid",
                 title=None, subtitle=None, show_ids=True, redact_living=False,
                 background=True, note=None):
        self.t, self.f = tree, focus
        self.up, self.down = max(1, min(4, up)), max(0, min(3, down))
        pw, ph = PAGES[page]
        self.W = 1224.0                     # design width; everything scales to page
        self.H = self.W * ph / pw
        self.page_pt = (pw, ph)
        self.title, self.subtitle = title, subtitle
        self.ids, self.redact, self.bg, self.note = show_ids, redact_living, background, note
        self.svg: list[str] = []
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
        x = cx - w / 2
        S = self.svg
        if p is None:
            S.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" fill="none" '
                     f'stroke="{PALETTE["faint"]}" stroke-width="0.5" stroke-dasharray="2 2.5" opacity="0.8"/>')
            self.text(cx, y + h / 2 + 3, "not yet identified" if gen <= 3 else "unknown",
                      7.2 if gen <= 3 else 6.4, style="italic", fill=PALETTE["faint"])
            return
        S.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3.5" '
                 f'fill="{PALETTE["card"]}" stroke="{color}" stroke-width="{1.0 if focus else 0.7}"/>')
        if focus:
            S.append(f'<rect x="{x + 3:.2f}" y="{y + 3:.2f}" width="{w - 6:.2f}" height="{h - 6:.2f}" rx="2" '
                     f'fill="none" stroke="{color}" stroke-width="0.4"/>')
        else:  # small accent tick on the top edge
            S.append(f'<path d="M{cx - 9:.2f},{y:.2f} H{cx + 9:.2f}" stroke="{color}" stroke-width="2"/>')
        pad = 7 if gen >= 3 else 10
        iw = w - 2 * pad
        ls = lifespan(p, self.redact)
        hide = self.redact and is_living(p)
        if gen == 0:
            sizes = dict(given=15.5, sur=10.5, l1=8.6, l2=8.6, id=6.2)
        elif gen <= 2:
            sizes = dict(given=11.6, sur=8.2, l1=7.4, l2=7.4, id=5.6)
        elif gen == 3:
            sizes = dict(given=9.4, sur=7.0, l1=7.0, id=5.4)
        else:
            sizes = dict(given=8.0, sur=6.2, l1=6.3, id=5.0)
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
            if not b and not d and ls:
                lines.append((ls, sizes["l1"], dict(style="italic", fill=PALETTE["ink2"])))
        elif ls:
            lines.append((fit_text(ls, iw, sizes["l1"]), sizes["l1"], dict(fill=PALETTE["ink2"])))
        if self.ids and p.fsid:
            lines.append((p.fsid, sizes["id"], dict(fill=PALETTE["faint"], track="0.6")))
        # vertical layout: distribute baselines inside the card
        heights = [s * 1.22 for _, s, _ in lines]
        total = sum(heights)
        if total > h - 6:  # drop lowest-priority lines until it fits
            while total > h - 6 and len(lines) > 2:
                drop = 2 if len(lines) > 3 else len(lines) - 1
                lines.pop(drop if not (self.ids and p.fsid) else len(lines) - 2)
                heights = [s * 1.22 for _, s, _ in lines]
                total = sum(heights)
        yy = y + (h - total) / 2
        for (s, size, kw), lh in zip(lines, heights):
            yy += lh
            self.text(cx, yy - lh * 0.24, s, size, **kw)

    # ── main ──
    def render(self) -> str:
        W = self.W
        P = PALETTE
        mx = 70.0                       # side margin for tree content
        CW = W - 2 * mx
        anc = self.t.ahnentafel(self.f, self.up)
        depth = self.up
        while depth > 1 and not any(n in anc for n in range(2 ** depth, 2 ** (depth + 1))):
            depth -= 1                  # don't reserve rows for empty generations
        # rows (top = oldest)
        vgap = 26.0
        top = 132.0
        row_y = {}
        cur = top
        for g in range(depth, -1, -1):
            row_y[g] = cur
            cur += GEN[g]["h"] + vgap
        tree_bottom = row_y[0] + GEN[0]["h"]

        def slot(n):
            g = n.bit_length() - 1
            i = n - 2 ** g
            sw = CW / 2 ** g
            cx = mx + sw * (i + 0.5)
            w = GEN[g]["w"] or (sw - 5)
            w = min(w, sw - (5 if g >= 4 else 10))
            return g, cx, w

        # ── descendants block (laid out first so the page can grow if needed) ──
        desc_top = tree_bottom + 30
        body_top = desc_top + 30
        footer_y = None
        lines = self.descendant_lines()
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
        H = self.H
        footer_y = H - 34

        S = self.svg
        # ── page & border ──
        if self.bg:
            S.append(f'<rect x="0" y="0" width="{W}" height="{H:.2f}" fill="{P["paper"]}"/>')
        S.append(f'<rect x="18" y="18" width="{W - 36}" height="{H - 36:.2f}" fill="none" stroke="{P["gold"]}" stroke-width="1.1"/>')
        S.append(f'<rect x="23.5" y="23.5" width="{W - 47}" height="{H - 47:.2f}" fill="none" stroke="{P["gold"]}" stroke-width="0.4"/>')
        for (x, y, sx, sy) in ((30, 30, 1, 1), (W - 30, 30, -1, 1), (30, H - 30, 1, -1), (W - 30, H - 30, -1, -1)):
            S.append(corner(x, y, sx, sy, P["sage"]))
        # ── title ──
        f = self.f
        title = self.title or f"The Family of {f.full}"
        sub = self.subtitle or " · ".join(x for x in (lifespan(f, self.redact), short_place(f.birth.place, 2)) if x)
        self.text(W / 2, 72, title, 30, font=FONT_DISPLAY, weight="500", style="italic")
        flo_w = min(150, tw(title, 30) * 0.42)
        S.append(flourish(W / 2, 86, flo_w, P["gold"]))
        if sub:
            self.text(W / 2, 104, sub, 8.4, caps=True, track="2.2", fill=P["ink2"])
        # side labels
        self.text(mx + CW / 4, top - 10, "Paternal ancestry", 6.8, caps=True, track="2.4", fill=P["sage"])
        self.text(mx + 3 * CW / 4, top - 10, "Maternal ancestry", 6.8, caps=True, track="2.4", fill=P["clay"])
        # generation numerals in the margin
        romans = ["", "I", "II", "III", "IV"]
        for g in range(1, depth + 1):
            yc = row_y[g] + GEN[g]["h"] / 2
            self.text(46, yc + 3, romans[g], 8.5, font=FONT_DISPLAY, fill=P["gold"], weight="600")
            self.text(W - 46, yc + 3, romans[g], 8.5, font=FONT_DISPLAY, fill=P["gold"], weight="600")

        # ── connectors ──
        S.append(f'<g fill="none" stroke="{P["line"]}" stroke-width="0.7" stroke-linecap="round">')
        dots = []
        for n in range(1, 2 ** depth):
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
                self.card(cx, row_y[g], w, GEN[g]["h"], anc[n], g, self.side_color(n))
            elif n // 2 in anc:     # a known person whose parent is missing: show the gap
                self.card(cx, row_y[g], w, GEN[g]["h"], None, g, P["faint"])

        # ── focus + spouses ──
        g0 = GEN[0]
        cx0 = W / 2
        y0 = row_y[0]
        unions = self.t.unions(f)
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
        self.card(cx0, y0, g0["w"], g0["h"], f, 0, P["gold"], focus=True)

        # ── descendants ──
        if self.down > 0:
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
        return head + "".join(S) + "</svg>"

    # ── descendants outline ──
    def descendant_lines(self):
        """Return blocks: list of lists of (level, segments). One block per child of focus."""
        if self.down == 0:
            return []
        blocks = []
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
        if n == 1:
            continue
        child = anc[n // 2]
        cy, py = year(child.birth.date), year(p.birth.date)
        if cy and py:
            gap = cy - py
            if gap < 13:
                issues.append(f"{p.full} born {py}, only {gap} yrs before child {child.full} ({cy})")
            if gap > (60 if p.sex == "F" or n % 2 else 80):
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
const [htmlPath, w, h, pdf, png] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({viewport: {width: Math.round(w*96), height: Math.round(h*96)}, deviceScaleFactor: 2});
  await pg.setContent(fs.readFileSync(htmlPath, 'utf8'), {waitUntil: 'networkidle'});
  await pg.evaluate(() => document.fonts.ready);
  if (pdf) await pg.pdf({path: pdf, width: w + 'in', height: h + 'in', printBackground: true});
  if (png) await pg.screenshot({path: png, fullPage: true});
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
"""
    with tempfile.TemporaryDirectory() as td:
        hp, jp = Path(td, "page.html"), Path(td, "print.js")
        hp.write_text(page_html, encoding="utf-8")
        jp.write_text(js, encoding="utf-8")
        subprocess.run(["node", str(jp), str(hp), f"{svg_w_in:.4f}", f"{svg_h_in:.4f}",
                        str(pdf.resolve()) if pdf else "", str(png.resolve()) if png else ""],
                       check=True, env={**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", "") + ":" +
                                        subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="GEDCOM (.ged) or JSON export")
    ap.add_argument("--focus", required=True, help="FamilySearch ID, GEDCOM xref, or unique name fragment")
    ap.add_argument("--up", type=int, default=4, help="ancestor generations (1–4, default 4)")
    ap.add_argument("--down", type=int, default=3, help="descendant generations (0–3, default 3)")
    ap.add_argument("--page", default="tabloid", choices=sorted(PAGES), help="paper size, landscape (default tabloid 17×11 in)")
    ap.add_argument("--title")
    ap.add_argument("--subtitle")
    ap.add_argument("--note", help="replace the footer line")
    ap.add_argument("--no-ids", action="store_true", help="hide FamilySearch IDs")
    ap.add_argument("--redact-living", action="store_true", help="show 'Living' instead of dates for living people")
    ap.add_argument("--no-background", action="store_true", help="white paper (saves ink)")
    ap.add_argument("-o", "--out", type=Path, default=Path("family-tree.svg"))
    ap.add_argument("--pdf", type=Path)
    ap.add_argument("--png", type=Path)
    a = ap.parse_args(argv)

    tree = Tree.from_json(a.source) if a.source.suffix.lower() == ".json" else Tree.from_gedcom(a.source)
    focus = tree.find(a.focus)
    r = Renderer(tree, focus, a.up, a.down, a.page, a.title, a.subtitle,
                 not a.no_ids, a.redact_living, not a.no_background, a.note)
    svg = r.render()
    a.out.write_text(svg, encoding="utf-8")
    anc = tree.ahnentafel(focus, r.up)
    known = len(anc) - 1
    slots = 2 ** (r.up + 1) - 2
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
