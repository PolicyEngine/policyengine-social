"""Tests for the card renderer.

Invariants, for every input:
- wrap() keeps every word, in order, and no line it returns is wider than
  the space it was given; when it can't fit the text it raises CardError.
- A rendered card is the layout's size, and rendering it again gives the
  same bytes.
- Our logo sits alone at the bottom right. A funder's credit sits at the top
  right, smaller than our logo, never beside it (Max, 28 October 2026).
- Text either fits without overlapping anything or the card is refused:
  no card is written with clipped or colliding text.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import make_cards  # noqa: E402
import sharecard  # noqa: E402
from sharecard import DOT, CardError, Style, TEAL, line_width, plain, words, wrap  # noqa: E402

CAMPAIGNS = sorted(p for p in (HERE / "campaigns").iterdir() if (p / "cards.toml").exists())
NUFFIELD = sharecard.FUNDERS["nuffield"]

needs_rsvg = pytest.mark.skipif(not shutil.which("rsvg-convert"), reason="needs rsvg-convert (librsvg)")


# --------------------------------------------------------------------------
# Line breaking
# --------------------------------------------------------------------------

WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEF£%0123456789,.-", min_size=1, max_size=12)


@settings(max_examples=200, deadline=None)
@given(st.lists(st.one_of(WORD, st.just(DOT)), min_size=1, max_size=9), st.integers(60, 900))
def test_wrap_keeps_words_and_fits(tokens, width):
    style = Style("bold", 20, TEAL)
    line = words(" ".join(tokens), style)
    try:
        lines = wrap(line, width)
    except CardError:
        # Refused only when some single word, or the text in six lines, can't fit.
        return
    assert all(line_width(part) <= width for part in lines)
    kept = [plain(w) for part in lines for w in part]
    # Every word survives in order; only a separator dot at a break may go.
    assert [t for t in tokens if t != DOT] == [t for t in kept if t != DOT]


def test_wrap_refuses_a_word_too_wide():
    style = Style("bold", 20, TEAL)
    with pytest.raises(CardError):
        wrap(words("supercalifragilistic expialidocious", style), 40)


# --------------------------------------------------------------------------
# Every campaign card
# --------------------------------------------------------------------------


def all_cards():
    for folder in CAMPAIGNS:
        campaign = make_cards.load(folder)
        for card in campaign.cards:
            yield pytest.param(campaign, card, id=f"{folder.name}/{card['id']}")


@needs_rsvg
@pytest.mark.parametrize(("campaign", "card"), list(all_cards()))
def test_campaign_card_renders(campaign, card):
    for layout in make_cards.LAYOUTS:
        image, _ = make_cards.render(layout, card, campaign.funder)
        assert image.size == (layout.w, layout.h)


@needs_rsvg
def test_rendering_is_deterministic():
    campaign = make_cards.load(CAMPAIGNS[0])
    card = campaign.cards[0]
    for layout in make_cards.LAYOUTS:
        first, _ = make_cards.render(layout, card, campaign.funder)
        second, _ = make_cards.render(layout, card, campaign.funder)
        assert first.tobytes() == second.tobytes()


def test_documents_name_real_cards():
    for folder in CAMPAIGNS:
        campaign = make_cards.load(folder)
        ids = {c["id"] for c in campaign.cards}
        for doc in campaign.documents:
            assert set(doc["cards"]) <= ids


# --------------------------------------------------------------------------
# Logos: ours alone at the bottom right, the funder small at the top right
# --------------------------------------------------------------------------


def corners(card, funder, layout):
    canvas_holder = {}
    original = make_cards.check

    def capture(canvas, layout_, card_id):
        canvas_holder["boxes"] = dict(canvas.boxes)
        return original(canvas, layout_, card_id)

    make_cards.check = capture
    try:
        make_cards.render(layout, card, funder)
    finally:
        make_cards.check = original
    return canvas_holder["boxes"]


@needs_rsvg
@pytest.mark.parametrize(("campaign", "card"), list(all_cards()))
def test_funder_and_logo_in_different_corners(campaign, card):
    for layout in make_cards.LAYOUTS:
        boxes = corners(card, campaign.funder, layout)
        logo = boxes["logo"]
        assert logo.y0 > layout.h / 2, "our logo sits in the bottom half"
        assert logo.x1 > layout.w * 0.75, "our logo sits at the right"
        if campaign.funder is None:
            assert "funder" not in boxes
            continue
        funder = boxes["funder"]
        assert funder.y1 < layout.h / 4, "the funder credit sits at the top"
        assert funder.x1 > layout.w * 0.75, "the funder credit sits at the right"
        assert funder.y1 - funder.y0 < logo.y1 - logo.y0, "the funder credit is smaller than our logo"


@needs_rsvg
def test_card_without_funder_has_no_credit():
    campaign = make_cards.load(CAMPAIGNS[0])
    for layout in make_cards.LAYOUTS:
        boxes = corners(campaign.cards[0], None, layout)
        assert "funder" not in boxes


@needs_rsvg
def test_altered_funder_logo_is_refused(tmp_path):
    altered = tmp_path / "logo.svg"
    altered.write_bytes(NUFFIELD.svg.read_bytes() + b"\n")
    with pytest.raises(CardError, match="SHA-256"):
        sharecard.funder_mark(replace(NUFFIELD, svg=altered), 30)


# --------------------------------------------------------------------------
# Any text: it fits cleanly or the card is refused
# --------------------------------------------------------------------------

PHRASE = st.lists(WORD, min_size=1, max_size=14).map(" ".join)


@needs_rsvg
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(kicker=PHRASE, headline=PHRASE, label=PHRASE, note=st.one_of(st.just(""), PHRASE))
def test_any_text_fits_or_is_refused(kicker, headline, label, note):
    card = {
        "id": "generated",
        "kicker": kicker,
        "headline": headline,
        "footer": "policyengine.org/uk/research",
        "stats": [{"value": "£135", "label": label, "source": "test"}, {"value": "£10", "label": "x", "source": "test"}],
        "note": note,
    }
    for layout in make_cards.LAYOUTS:
        try:
            boxes = corners(card, NUFFIELD, layout)
        except CardError:
            continue  # refused, so nothing would be written
        # Accepted: every block is inside the card and in order down the page.
        for box in boxes.values():
            assert layout.margin - 2 <= box.x0 and box.x1 <= layout.w - layout.margin + 2
        order = ["kicker", "headline", "stats"] + (["note"] if "note" in boxes else []) + ["footer"]
        for above, below in zip(order, order[1:]):
            assert boxes[below].y0 - boxes[above].y1 >= 10
