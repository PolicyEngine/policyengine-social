"""Drawing primitives for PolicyEngine share cards: type, line breaking, logos.

make_cards.py lays cards out with these. They come from the Budget-day webinar
share card (October 2026), which matched the 15 September 2026 webinar card
(PolicyEngine/newsletters, assets/images/cpid-webinar-2026-09-15.png): navy
background with two corner glows, Roboto Serif headlines, Roboto for the rest.
The fonts and their weights were identified by fitting renders to that card.

Text is drawn at three times the card's size and averaged down, so edges
match unhinted browser text. Running the same inputs twice gives the same
files, byte for byte.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "policyengine-white.png"

# Colours. The teal and greys are tokens from @policyengine/ui-kit
# (src/theme/tokens.css). The navy and its two glows have no token; they are
# measured from the September card.
NAVY = (12, 26, 39)  # #0C1A27
GLOW_BLUE = (26, 59, 89)  # #1A3B59 at the top-left corner
GLOW_TEAL = (19, 55, 64)  # #133740 just below the bottom-right corner
TEAL = (79, 209, 197)  # teal-300 #4FD1C5
WHITE = (255, 255, 255)
SOFT = (226, 232, 240)  # gray-200 #E2E8F0
MUTED = (203, 213, 225)  # gray-300 #CBD5E1

FACES = {
    "serif": "RobotoSerif.ttf",  # variable; drawn at weight 400
    "sans": "Roboto-Regular.ttf",
    "bold": "Roboto-Bold.ttf",
}

SS = 3  # draw at 3x and average down


class CardError(SystemExit):
    """A problem the person running the script can fix."""

    def __init__(self, message: str):
        super().__init__(f"make_cards: {message}")


@dataclass(frozen=True)
class Funder:
    """A funder's logo, drawn from the file the funder supplied, unaltered."""

    label: str  # the words before the logo
    svg: Path
    sha256: str  # a changed file is refused, so no colour, shape or proportion changes
    aspect: float  # the SVG's own width over height


FUNDERS = {
    # The Nuffield Foundation's official white logo, from nuffieldfoundation.org's
    # theme assets, at its communications team's request (22 October 2026).
    "nuffield": Funder(
        label="Funded by",
        svg=ASSETS / "funders" / "nuffield" / "logo-white.svg",
        sha256="b3727385be9295f8daa3938c745f87b2e00e5675130354f6394ae6b3fec5654c",
        aspect=117.862 / 70,
    ),
}


def need_raqm() -> None:
    """Stop unless Pillow can kern.

    Kerning and the "fi" ligature come from Pillow's Raqm layout, which needs
    the FriBiDi library. Python as uv installs it on a Mac does not look in
    Homebrew's folder, so when Raqm is off and Homebrew has FriBiDi, start
    again with that folder on the library path. Without Raqm the line breaks
    and letter spacing change.
    """
    if features.check("raqm"):
        return
    folders = [d for d in ("/opt/homebrew/lib", "/usr/local/lib") if list(Path(d).glob("libfribidi*"))]
    if sys.platform == "darwin" and folders and "SHARE_CARD_RETRIED" not in os.environ:
        fallback = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "/usr/local/lib:/usr/lib")
        env = dict(os.environ, SHARE_CARD_RETRIED="1")
        env["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join([*folders, fallback])
        sys.stdout.flush()
        sys.stderr.flush()
        # orig_argv keeps "-m pytest" and the like, which argv loses.
        os.execve(sys.executable, [sys.executable, *sys.orig_argv[1:]], env)
    raise CardError(
        "this Pillow has no Raqm text layout, so it cannot kern. Raqm needs the "
        "FriBiDi library: `brew install fribidi` on a Mac, `apt-get install libfribidi0` on Linux."
    )


# --------------------------------------------------------------------------
# Type
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Style:
    face: str
    size: float  # px on the finished card
    colour: tuple[int, int, int]
    tracking: float = 0.0  # em
    leading: float = 1.5  # line pitch as a multiple of size


@lru_cache(maxsize=None)
def font(face: str, size: float) -> ImageFont.FreeTypeFont:
    path = ASSETS / "fonts" / FACES[face]
    if not path.exists():
        raise CardError(f"missing font file {path}.")
    loaded = ImageFont.truetype(str(path), size * SS, layout_engine=ImageFont.Layout.RAQM)
    if face == "serif":
        # Axes in file order: width, optical size, weight, grade. Optical size
        # follows the pixel size, as a browser's automatic optical sizing does.
        loaded.set_variation_by_axes([100, min(max(size, 8), 144), 400, 0])
    return loaded


@lru_cache(maxsize=None)
def metrics(face: str, size: float) -> tuple[float, float, float]:
    """Cap height, ascender height and descender depth, in card px."""
    loaded = font(face, size)
    cap = -loaded.getbbox("H", anchor="ls")[1] / SS
    ascent = -loaded.getbbox("bdfhkl", anchor="ls")[1] / SS
    descent = loaded.getbbox("gjpqy", anchor="ls")[3] / SS
    return cap, ascent, descent


@lru_cache(maxsize=None)
def advance(text: str, face: str, size: float) -> float:
    return font(face, size).getlength(text) / SS


@lru_cache(maxsize=None)
def glyph(face: str, char: str) -> bytes:
    image = Image.new("L", (72, 72), 0)
    ImageDraw.Draw(image).text((12, 54), char, font=font(face, 13.0), fill=255, anchor="ls")
    return image.tobytes()


def missing_glyphs(text: str, face: str) -> list[str]:
    """Characters the font would draw as its empty "no such glyph" box."""
    empty = glyph(face, "￿")
    return sorted({ch for ch in text if not ch.isspace() and glyph(face, ch) == empty})


def offsets(text: str, style: Style) -> list[float]:
    """Left edge of each character under tracking, keeping pair kerning."""
    xs = [0.0]
    for i in range(len(text) - 1):
        pair = advance(text[i : i + 2], style.face, style.size)
        nxt = advance(text[i + 1], style.face, style.size)
        xs.append(xs[-1] + pair - nxt + style.tracking * style.size)
    return xs


def run_width(text: str, style: Style) -> float:
    if not text:
        return 0.0
    if style.tracking:
        return offsets(text, style)[-1] + advance(text[-1], style.face, style.size)
    return advance(text, style.face, style.size)


Fragment = tuple[str, Style]
Word = tuple[Fragment, ...]  # one unbreakable word; its style may change inside


def words(text: str, style: Style, accent: Style | None = None) -> list[Word]:
    """Split text into words. **Marked** spans take the accent style."""
    out: list[Word] = []
    current: list[Fragment] = []
    for i, span in enumerate(text.split("**")):
        chosen = accent if (accent and i % 2) else style
        for piece in re.split(r"(\s+)", span):
            if piece.isspace():
                if current:
                    out.append(tuple(current))
                    current = []
            elif piece:
                current.append((piece, chosen))
    if current:
        out.append(tuple(current))
    return out


def plain(word: Word) -> str:
    return "".join(text for text, _ in word)


def shown(line: list[Word]) -> str:
    return " ".join(plain(word) for word in line)


def runs(line: list[Word]) -> list[Fragment]:
    """Join neighbouring text of one style; a word's last piece carries the space."""
    merged: list[Fragment] = []
    for i, word in enumerate(line):
        for j, (text, style) in enumerate(word):
            if j == len(word) - 1 and i < len(line) - 1:
                text += " "
            if merged and merged[-1][1] == style:
                merged[-1] = (merged[-1][0] + text, style)
            else:
                merged.append((text, style))
    return merged


def line_width(line: list[Word]) -> float:
    return sum(run_width(text, style) for text, style in runs(line))


DOT = "·"  # the only separator a line break may replace


def break_cost(before: str, after: str) -> float:
    """How much a line break between two words costs; negative is welcome."""
    if DOT in (before, after) or before[-1] in ".:;?!":
        return -0.5
    if before[-1] == ",":
        return -0.15
    if any(ch.isdigit() for ch in before):
        return 0.3  # keep "28 October" on one line
    return 0.0


def trim(line: list[Word]) -> list[Word]:
    while line and plain(line[0]) == DOT:
        line = line[1:]
    while line and plain(line[-1]) == DOT:
        line = line[:-1]
    return line


def wrap(line: list[Word], max_width: float, max_lines: int = 6) -> list[list[Word]]:
    """Fewest lines that fit, balanced, preferring breaks after punctuation.

    Dynamic programming keeps the original cost (widest/narrowest line and
    punctuation), without enumerating every partition. For each possible
    narrowest width, retain the smallest widest width at each break point and
    punctuation score. Scores are multiples of 1/20, so the number of states
    is bounded by the line limit, rather than the number of partitions.
    """
    if isinstance(max_lines, bool) or not isinstance(max_lines, int) or max_lines < 1:
        raise CardError("the line limit must be a positive integer.")
    if max_width <= 0:
        raise CardError("the available text width must be positive.")
    for word in line:
        if plain(word) != DOT and line_width([word]) > max_width:
            raise CardError(f'word "{plain(word)}" does not fit in {max_width:.0f}px.')
    if line_width(line) <= max_width:
        return [line]

    n = len(line)
    limit = min(n, max_lines)
    failure = f'"{shown(line)}" does not fit in {max_width:.0f}px within {max_lines} lines.'
    if limit < 2:
        raise CardError(failure)

    # Cache each possible line once, including the removable separator dots.
    spans: dict[tuple[int, int], float] = {}
    following: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for start in range(n):
        for end in range(start + 1, n + 1):
            part = trim(line[start:end])
            if part:
                width = line_width(part)
                if width <= max_width:
                    spans[start, end] = width
                    following[start].append((end, width))

    # First find the fewest feasible lines. Impossible long paragraphs stop
    # here, before any balancing work.
    reachable = {0}
    for count in range(1, limit + 1):
        reachable = {end for start in reachable if start < n for end, _ in following[start]}
        if count >= 2 and n in reachable:
            break
    else:
        raise CardError(failure)

    pauses = [0.0] + [break_cost(plain(line[i - 1]), plain(line[i])) for i in range(1, n)]
    scores = [round(pause * 20) for pause in pauses]
    # A state holds (widest width, cuts). Lexicographic cuts preserve the
    # former left-to-right tie breaking when two partitions have equal cost.
    best: tuple[float, tuple[int, ...]] | None = None
    seen: set[tuple[int, ...]] = set()
    for narrowest in sorted(set(spans.values())):
        states: dict[int, dict[int, tuple[float, tuple[int, ...]]]] = {0: {0: (0.0, ())}}
        for used in range(count):
            next_states: dict[int, dict[int, tuple[float, tuple[int, ...]]]] = {}
            for start, penalties in states.items():
                if start == n:
                    continue
                for end, width in following[start]:
                    if width < narrowest or n - end < count - used - 1:
                        continue
                    if (used == count - 1) != (end == n):
                        continue
                    target = next_states.setdefault(end, {})
                    for penalty, (widest, cuts) in penalties.items():
                        candidate = (max(widest, width), cuts + ((start,) if start else ()))
                        score = penalty + scores[start]
                        if score not in target or candidate < target[score]:
                            target[score] = candidate
            states = next_states
            if not states:
                break
        for _, cuts in states.get(n, {}).values():
            if cuts in seen:
                continue
            seen.add(cuts)
            edges = (0, *cuts, n)
            widths = [spans[a, b] for a, b in zip(edges, edges[1:])]
            cost = (1.25 * max(widths) - 0.25 * min(widths)) / max_width
            cost += sum(pauses[cut] for cut in cuts)
            candidate = (cost, cuts)
            if best is None or candidate < best:
                best = candidate
    assert best is not None  # the reachability check found a feasible partition
    edges = (0, *best[1], n)
    return [trim(line[a:b]) for a, b in zip(edges, edges[1:])]


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------


@dataclass
class Box:
    name: str
    x0: float
    y0: float
    x1: float
    y1: float

    def add(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.x0, self.y0 = min(self.x0, x0), min(self.y0, y0)
        self.x1, self.y1 = max(self.x1, x1), max(self.y1, y1)


def logo_height(width: float) -> float:
    with Image.open(LOGO) as mark:
        return width * mark.height / mark.width


def funder_mark(funder: Funder, height_px: int) -> Image.Image:
    """The funder's logo at this pixel height, rendered from its SVG as supplied."""
    data = funder.svg.read_bytes()
    if hashlib.sha256(data).hexdigest() != funder.sha256:
        raise CardError(
            f"{funder.svg.name} is not the file the funder supplied (SHA-256 changed). "
            "Use their file unaltered."
        )
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        raise CardError(
            "drawing a funder's logo needs rsvg-convert: `brew install librsvg` on a Mac, "
            "`apt-get install librsvg2-bin` on Linux."
        )
    png = subprocess.run(
        [rsvg, "--height", str(height_px), "--format", "png"],
        input=data, capture_output=True, check=True,
    ).stdout  # fmt: skip
    return Image.open(io.BytesIO(png)).convert("RGBA")


def background(w: int, h: int) -> Image.Image:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    navy = np.array(NAVY, np.float32)
    pixels = np.empty((h, w, 3), np.float32)
    pixels[:] = navy

    def glow(cx: float, cy: float, rx: float, ry: float, colour: tuple) -> None:
        reach = np.clip(1 - np.hypot((xx - cx) / rx, (yy - cy) / ry), 0, 1)
        pixels[:] += reach[..., None] * (np.array(colour, np.float32) - navy)

    glow(0, 0, 0.35 * w, 0.43 * h, GLOW_BLUE)
    glow(0.85 * w, 1.07 * h, 0.46 * w, 0.44 * h, GLOW_TEAL)
    return Image.fromarray(np.clip(pixels + 0.5, 0, 255).astype(np.uint8), "RGB")


class Card:
    """A canvas that records the ink box of everything it draws, by name."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.image = background(w, h).resize((w * SS, h * SS), Image.BICUBIC).convert("RGBA")
        self.draw = ImageDraw.Draw(self.image)
        self.boxes: dict[str, Box] = {}

    def note(self, name: str, x0: float, y0: float, x1: float, y1: float) -> None:
        if name in self.boxes:
            self.boxes[name].add(x0, y0, x1, y1)
        else:
            self.boxes[name] = Box(name, x0, y0, x1, y1)

    def text(self, line: list[Word], x: float, baseline: float, name: str) -> None:
        for text, style in runs(line):
            loaded = font(style.face, style.size)
            fill = (*style.colour, 255)
            pieces = zip(text, offsets(text, style)) if style.tracking else [(text, 0.0)]
            for piece, dx in pieces:
                if piece.isspace():
                    continue
                at = ((x + dx) * SS, baseline * SS)
                self.draw.text(at, piece, font=loaded, fill=fill, anchor="ls")
                ink = self.draw.textbbox(at, piece, font=loaded, anchor="ls")
                self.note(name, *(edge / SS for edge in ink))
            x += run_width(text, style)

    def paragraph(self, lines: list[list[Word]], x: float, baseline: float, pitch: float, name: str) -> float:
        """Draw lines downward from the first baseline; return the last baseline."""
        for i, line in enumerate(lines):
            self.text(line, x, baseline + i * pitch, name)
        return baseline + (len(lines) - 1) * pitch

    def logo(self, x: float, y: float, width: float) -> None:
        mark = Image.open(LOGO).convert("RGBA")
        size = (round(width * SS), round(logo_height(width) * SS))
        if size[0] > mark.width:
            raise CardError("the logo file is too small for this size.")
        self.image.alpha_composite(mark.resize(size, Image.LANCZOS), (round(x * SS), round(y * SS)))
        self.note("logo", x, y, x + width, y + logo_height(width))

    def funder(self, funder: Funder, right: float, bottom: float, height: float, label_size: float, gap: float) -> float:
        """The funder's label and logo, ending at `right` with the logo's bottom
        at `bottom`. Returns the block's left edge."""
        width = height * funder.aspect
        x, y = right - width, bottom - height
        self.image.alpha_composite(funder_mark(funder, round(height * SS)), (round(x * SS), round(y * SS)))
        self.note("funder", x, y, x + width, y + height)
        label = words(funder.label, Style("sans", label_size, MUTED))
        cap = metrics("sans", label_size)[0]
        lx = x - gap - line_width(label)
        self.text(label, lx, y + height / 2 + cap / 2, "funder")
        return lx

    def finish(self) -> Image.Image:
        return self.image.convert("RGB").reduce(SS)
