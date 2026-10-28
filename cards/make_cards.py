#!/usr/bin/env python3
"""Render PolicyEngine social cards from a campaign's cards.toml.

    uv run make_cards.py                                   # every campaign
    uv run make_cards.py campaigns/uk-autumn-budget-2026   # one campaign
    uv run make_cards.py campaigns/uk-autumn-budget-2026 p1-energy   # one card

For each card in a campaign's cards.toml it writes rendered/<id>.png
(1200x675, for X and Bluesky) and rendered/<id>-square.png (1080x1080, for
LinkedIn), and for each [[document]] a PDF of square cards, one per page
(a LinkedIn document post). It draws with Pillow and NumPy; nothing is
uploaded or sent.

The look: navy with two corner glows, a teal line above the headline (the
kicker, in sentence case as cards.toml writes it), a Roboto Serif headline,
Roboto for the rest, and the PolicyEngine logo bottom right. A campaign with a
funder (`funder = "nuffield"` under [campaign]) also gets "Funded by" and the
funder's logo, small, at the top right, level with the kicker. The card is
PolicyEngine's, so the credit sits in a different corner from our logo and
smaller: side by side at the same size they read as a partnership, and
stacked under our logo they crowded the note (Max, 28 October 2026).

The words are not in this script. It reads them from cards.toml and prints
every line it draws. It stops, and writes nothing for that card, if any text
would be clipped, overlap other text or run into a logo, or if a character is
missing from the font.
"""

from __future__ import annotations

import argparse
import tomllib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

import sharecard as base
from sharecard import (
    MUTED, SOFT, TEAL, WHITE, Card, CardError, Funder, Style,
    line_width, logo_height, metrics, shown, words, wrap,
)  # fmt: skip

HERE = Path(__file__).resolve().parent
CAMPAIGNS = HERE / "campaigns"


@dataclass(frozen=True)
class Layout:
    suffix: str
    w: int
    h: int
    margin: int
    top: float
    kicker: float
    headline: float
    headline_min: float
    headline_lines: int
    headline_gap: float
    stats_gap: float  # headline baseline to the first stat's top
    tag: float
    value: float
    label: float
    columns: bool  # stats side by side (landscape) or stacked (square)
    note: float
    footer: float
    logo_w: float
    bottom: float
    funder_h: float
    funder_label: float
    funder_gap: float
    cluster_gap: float


LAYOUTS = (
    Layout(
        suffix="", w=1200, h=675, margin=56, top=52,
        kicker=20, headline=46, headline_min=34, headline_lines=2, headline_gap=22,
        stats_gap=44, tag=17, value=64, label=19, columns=True,
        note=16, footer=18, logo_w=172, bottom=40,
        funder_h=24, funder_label=14, funder_gap=8, cluster_gap=24,
    ),
    Layout(
        suffix="-square", w=1080, h=1080, margin=72, top=80,
        kicker=24, headline=54, headline_min=40, headline_lines=3, headline_gap=28,
        stats_gap=56, tag=20, value=72, label=24, columns=False,
        note=19, footer=21, logo_w=218, bottom=64,
        funder_h=30, funder_label=17, funder_gap=10, cluster_gap=30,
    ),
)  # fmt: skip


def vet(card_id: str, what: str, text: str, faces: tuple[str, ...]) -> None:
    for face in faces:
        absent = base.missing_glyphs(text.upper() + text, face)
        if absent:
            raise CardError(f"{card_id}: the {what} uses {' '.join(absent)}, which {base.FACES[face]} cannot draw.")


@dataclass(frozen=True)
class Campaign:
    folder: Path
    funder: Funder | None
    cards: list[dict]
    documents: list[dict]


def load(folder: Path) -> Campaign:
    path = folder / "cards.toml"
    if not path.exists():
        raise CardError(f"{folder} has no cards.toml.")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    funder_name = data.get("campaign", {}).get("funder", "")
    if funder_name and funder_name not in base.FUNDERS:
        raise CardError(f"{path}: unknown funder {funder_name!r}; known: {', '.join(base.FUNDERS)}.")
    funder = base.FUNDERS[funder_name] if funder_name else None
    cards = data.get("card", [])
    seen = set()
    for card in cards:
        for key in ("id", "kicker", "headline", "footer", "stats"):
            if key not in card:
                raise CardError(f"a card in {path} has no {key}.")
        if card["id"] in seen:
            raise CardError(f"two cards are called {card['id']}.")
        seen.add(card["id"])
        if not 2 <= len(card["stats"]) <= 3:
            raise CardError(f"{card['id']} has {len(card['stats'])} stats; draw two or three.")
        for stat in card["stats"]:
            if "source" not in stat:
                raise CardError(f"{card['id']}: the stat {stat.get('value')} names no source.")
        vet(card["id"], "kicker", card["kicker"], ("bold",))
        vet(card["id"], "headline", card["headline"], ("serif",))
        vet(card["id"], "note", card.get("note", ""), ("sans",))
        vet(card["id"], "footer", card["footer"], ("bold",))
        for stat in card["stats"]:
            vet(card["id"], f"stat {stat['value']}", stat["value"], ("serif",))
            vet(card["id"], f"label of {stat['value']}", stat["label"] + stat.get("tag", ""), ("sans", "bold"))
    documents = data.get("document", [])
    for doc in documents:
        for key in ("id", "title", "cards"):
            if key not in doc:
                raise CardError(f"a document in {path} has no {key}.")
        unknown = [c for c in doc["cards"] if c not in seen]
        if unknown:
            raise CardError(f"document {doc['id']} names cards that {path} doesn't have: {', '.join(unknown)}.")
    return Campaign(folder, funder, cards, documents)


def render(layout: Layout, card: dict, funder: Funder | None):
    canvas = Card(layout.w, layout.h)
    left, content = layout.margin, layout.w - 2 * layout.margin
    used: dict[str, list[str]] = {}

    # The funder credit, if any, is small and sits top right, level with the
    # kicker, away from our logo (see the docstring).
    kicker = Style("bold", layout.kicker, TEAL, tracking=0.02)
    y = layout.top + metrics("bold", layout.kicker)[0]
    kicker_right = left + content
    if funder:
        cap = metrics("bold", layout.kicker)[0]
        bottom = y - cap / 2 + layout.funder_h / 2
        funder_left = canvas.funder(
            funder, layout.w - layout.margin, bottom, layout.funder_h, layout.funder_label, layout.funder_gap
        )
        used["funder"] = [f"{funder.label} [{funder.svg.parent.name} logo]"]
        kicker_right = funder_left - layout.cluster_gap
    lines = wrap(words(card["kicker"], kicker), kicker_right - left)
    y = canvas.paragraph(lines, left, y, layout.kicker * 1.5, "kicker")
    used["kicker"] = [shown(line) for line in lines]

    size = layout.headline
    while True:
        headline = Style("serif", size, WHITE, leading=1.15)
        try:
            lines = wrap(words(card["headline"], headline), content)
        except CardError:
            lines = []
        if lines and len(lines) <= layout.headline_lines:
            break
        size -= 2
        if size < layout.headline_min:
            raise CardError(f"{card['id']}: the headline needs more than {layout.headline_lines} lines.")
    y += layout.headline_gap + metrics("serif", size)[1]
    y = canvas.paragraph(lines, left, y, size * headline.leading, "headline")
    used[f"headline {size:.0f}px"] = [shown(line) for line in lines]
    top_of_stats = y + metrics("serif", size)[2] + layout.stats_gap

    # Bottom band: the PolicyEngine logo right, footer (and note above it) left.
    logo_top = layout.h - layout.bottom - logo_height(layout.logo_w)
    logo_x = layout.w - layout.margin - layout.logo_w
    canvas.logo(logo_x, logo_top, layout.logo_w)

    # A link is one word, so it shrinks to fit on one line rather than wrapping.
    fsize = layout.footer
    while line_width(words(card["footer"], Style("bold", fsize, TEAL))) > logo_x - left - 32:
        fsize -= 0.5
        if fsize < 14:
            raise CardError(f"{card['id']}{layout.suffix}: the footer link is too long for the space beside the logos.")
    footer = Style("bold", fsize, TEAL)
    flines = wrap(words(card["footer"], footer), logo_x - left - 32)
    fpitch = fsize * 1.45
    first = layout.h - layout.bottom - (len(flines) - 1) * fpitch
    canvas.paragraph(flines, left, first, fpitch, "footer")
    used["footer"] = [shown(line) for line in flines]
    band_top = min(logo_top, first - metrics("bold", fsize)[1])

    if card.get("note"):
        note = Style("sans", layout.note, MUTED)
        nlines = wrap(words(card["note"], note), content)
        npitch = layout.note * 1.45
        nlast = band_top - 22 - metrics("sans", layout.note)[2]
        nfirst = nlast - (len(nlines) - 1) * npitch
        canvas.paragraph(nlines, left, nfirst, npitch, "note")
        used["note"] = [shown(line) for line in nlines]
        stats_bottom = nfirst - metrics("sans", layout.note)[1] - 18
    else:
        stats_bottom = band_top - 18

    draw_stats(canvas, layout, card, top_of_stats, stats_bottom, used)
    check(canvas, layout, card["id"])
    return canvas.finish(), used


def draw_stats(canvas: Card, layout: Layout, card: dict, top: float, bottom: float, used: dict) -> None:
    stats = card["stats"]
    left, content = layout.margin, layout.w - 2 * layout.margin
    tag_style = Style("bold", layout.tag, SOFT, tracking=0.02)
    label_style = Style("sans", layout.label, SOFT, leading=1.35)

    if layout.columns:
        gutter = 40
        width = (content - gutter * (len(stats) - 1)) / len(stats)
        blocks = []
        for i, stat in enumerate(stats):
            x = left + i * (width + gutter)
            blocks.append((x, width, stat))
        # All columns share the tag row and the value baseline, so they align.
        has_tag = any(stat.get("tag") for stat in stats)
        tag_lines = {i: wrap(words(s["tag"], tag_style), width) if s.get("tag") else [] for i, (_, _, s) in enumerate(blocks)}
        tag_rows = max((len(v) for v in tag_lines.values()), default=0)
        value_size = layout.value
        for i, (x, w, stat) in enumerate(blocks):
            while line_width(words(stat["value"], Style("serif", value_size, TEAL))) > w and value_size > 36:
                value_size -= 2
        # Measure the block first, then sit it a little above the middle of its space.
        label_rows = max(len(wrap(words(s["label"], label_style), width)) for s in stats)
        height = (
            (metrics("bold", layout.tag)[0] + (tag_rows - 1) * layout.tag * 1.35 + 14 if has_tag else 0)
            + metrics("serif", value_size)[0] + 16 + metrics("sans", layout.label)[1]
            + (label_rows - 1) * layout.label * label_style.leading + metrics("sans", layout.label)[2]
        )
        y = top + max(0.0, (bottom - top - height) * 0.4)
        if has_tag:
            y += metrics("bold", layout.tag)[0]
            for i, (x, w, stat) in enumerate(blocks):
                canvas.paragraph(tag_lines[i], x, y, layout.tag * 1.35, "stats")
                used[f"stat {i + 1} tag"] = [shown(line) for line in tag_lines[i]]
            y += (tag_rows - 1) * layout.tag * 1.35 + 14
        y += metrics("serif", value_size)[0]
        for i, (x, w, stat) in enumerate(blocks):
            value = Style("serif", value_size, TEAL)
            canvas.text(words(stat["value"], value)[0:], x, y, "stats")
            used[f"stat {i + 1} value"] = [stat["value"]]
            lines = wrap(words(stat["label"], label_style), w)
            ly = y + 16 + metrics("sans", layout.label)[1]
            canvas.paragraph(lines, x, ly, layout.label * label_style.leading, "stats")
            used[f"stat {i + 1} label"] = [shown(line) for line in lines]
        if canvas.boxes["stats"].y1 > bottom:
            raise CardError(f"{card['id']}{layout.suffix}: the stats run {canvas.boxes['stats'].y1 - bottom:.0f}px into the note.")
        return

    # Square: one stat per row, value on the left, tag and label on the right.
    value_w = max(line_width(words(s["value"], Style("serif", layout.value, TEAL))) for s in stats)
    label_x = left + value_w + 36
    label_w = left + content - label_x
    rows = []
    for stat in stats:
        tag = wrap(words(stat["tag"], tag_style), label_w) if stat.get("tag") else []
        label = wrap(words(stat["label"], label_style), label_w)
        height = max(
            metrics("serif", layout.value)[0],
            (len(tag) * layout.tag * 1.35 + 6 if tag else 0) + metrics("sans", layout.label)[0]
            + (len(label) - 1) * layout.label * label_style.leading + metrics("sans", layout.label)[2],
        )
        rows.append((stat, tag, label, height))
    total = sum(r[3] for r in rows)
    gap = min(64.0, (bottom - top - total) / max(len(rows) - 1, 1))
    if gap < 28:
        raise CardError(f"{card['id']}{layout.suffix}: the stats need {28 * (len(rows) - 1) + total - (bottom - top):.0f}px more.")
    spare = bottom - top - total - gap * (len(rows) - 1)
    y = top + max(0.0, spare * 0.4)
    for i, (stat, tag, label, height) in enumerate(rows):
        cap = metrics("serif", layout.value)[0]
        block = (
            (len(tag) * layout.tag * 1.35 + 6 if tag else 0) + metrics("sans", layout.label)[0]
            + (len(label) - 1) * layout.label * label_style.leading + metrics("sans", layout.label)[2]
        )
        # The value and the words beside it share a centre line.
        vy, ly0 = y + (height - cap) / 2, y + (height - block) / 2
        canvas.text(words(stat["value"], Style("serif", layout.value, TEAL)), left, vy + cap, "stats")
        used[f"stat {i + 1} value"] = [stat["value"]]
        ty = ly0 + metrics("bold", layout.tag)[0]
        if tag:
            canvas.paragraph(tag, label_x, ty, layout.tag * 1.35, "stats")
            used[f"stat {i + 1} tag"] = [shown(line) for line in tag]
            ty += (len(tag) - 1) * layout.tag * 1.35 + 6 + layout.label * 1.1
        else:
            ty = ly0 + metrics("sans", layout.label)[0]
        canvas.paragraph(label, label_x, ty, layout.label * label_style.leading, "stats")
        used[f"stat {i + 1} label"] = [shown(line) for line in label]
        if i < len(rows) - 1:
            rule_y = y + height + gap / 2
            canvas.draw.line(
                ((left * base.SS, rule_y * base.SS), ((left + content) * base.SS, rule_y * base.SS)),
                fill=(*MUTED, 60), width=max(1, round(base.SS)),
            )
        y += height + gap


def check(canvas: Card, layout: Layout, card_id: str) -> None:
    boxes, problems = canvas.boxes, []
    for box in boxes.values():
        if box.x0 < layout.margin - 2 or box.x1 > layout.w - layout.margin + 2:
            problems.append(f"{box.name} runs past the side margin")
        if box.y0 < 30 or box.y1 > layout.h - 30:
            problems.append(f"{box.name} runs past the top or bottom")
    order = ["kicker", "headline", "stats"] + (["note"] if "note" in boxes else []) + ["footer"]
    for above, below in zip(order, order[1:]):
        room = boxes[below].y0 - boxes[above].y1
        if room < 10:
            problems.append(f"{above} and {below} are {room:.0f}px apart")
    if boxes["logo"].x0 - boxes["footer"].x1 < 24:
        problems.append("the footer runs into the logo")
    if "funder" in boxes:
        if boxes["funder"].x0 - boxes["kicker"].x1 < 24:
            problems.append("the kicker runs into the funder credit")
        if boxes["headline"].y0 - boxes["funder"].y1 < 10:
            problems.append("the funder credit runs into the headline")
    if "note" in boxes and boxes["note"].y1 > boxes["logo"].y0 - 8:
        problems.append("the note runs into the logos")
    if problems:
        raise CardError(f"{card_id}{layout.suffix}: " + "; ".join(problems))


def render_campaign(campaign: Campaign, ids: list[str]) -> None:
    chosen = [c for c in campaign.cards if not ids or c["id"] in ids]
    if ids and len(chosen) != len(set(ids)):
        known = {c["id"] for c in campaign.cards}
        raise CardError(f"{campaign.folder.name} has no card {', '.join(sorted(set(ids) - known))}.")
    out = campaign.folder / "rendered"
    out.mkdir(exist_ok=True)
    for card in chosen:
        rendered = [(layout, *render(layout, card, campaign.funder)) for layout in LAYOUTS]  # both fit before either is written
        for layout, image, used in rendered:
            path = out / f"{card['id']}{layout.suffix}.png"
            image.save(path, format="PNG", optimize=True)
            where = "; ".join(f"{k}: {card[k]}" for k in ("post", "gate") if k in card)
            print(f"\n{path.relative_to(HERE)}  {layout.w}x{layout.h}" + (f"  ({where})" if where else ""))
            for part, lines in used.items():
                for line in lines:
                    print(f"  {part:16} | {line}")
    for doc in campaign.documents:
        if ids and not set(doc["cards"]) & set(ids):
            continue
        pages = [Image.open(out / f"{c}-square.png").convert("RGB") for c in doc["cards"]]
        path = out / f"{doc['id']}.pdf"
        pages[0].save(path, save_all=True, append_images=pages[1:], resolution=144, title=doc["title"], author="PolicyEngine")
        print(f"\n{path.relative_to(HERE)}  {len(pages)} pages: {', '.join(doc['cards'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("campaign", nargs="?", help="a campaign folder (default: every folder in campaigns/)")
    parser.add_argument("ids", nargs="*", help="card ids to render (default: all in the campaign)")
    args = parser.parse_args()
    base.need_raqm()
    if args.campaign:
        folders = [Path(args.campaign).resolve()]
    else:
        folders = sorted(p for p in CAMPAIGNS.iterdir() if (p / "cards.toml").exists())
        if args.ids:
            raise CardError("name a campaign folder before card ids.")
    for folder in folders:
        render_campaign(load(folder), args.ids)


if __name__ == "__main__":
    main()
