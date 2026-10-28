"""Fitting checks for individual stat components and editable text fields."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_cards  # noqa: E402
from sharecard import Card, CardError  # noqa: E402


def fitting_card(stats=None):
    return {
        "id": "known-fit",
        "kicker": "Budget changes",
        "headline": "What changes for households",
        "footer": "policyengine.org",
        "note": "Annual household income.",
        "stats": stats or [
            {"value": "£135", "tag": "Households", "label": "Average increase", "source": "test"},
            {"value": "12%", "tag": "Adults", "label": "Share affected", "source": "test"},
        ],
    }


def render_boxes(monkeypatch, layout, card):
    captured = {}
    original = make_cards.check

    def capture(canvas, layout_, card_id):
        captured.update(canvas.boxes)
        original(canvas, layout_, card_id)

    with monkeypatch.context() as patch:
        patch.setattr(make_cards, "check", capture)
        make_cards.render(layout, card, None)
    return captured


def assert_components_separate(boxes, stats):
    components = []
    for index, stat in enumerate(stats, 1):
        for field in ("value", "tag", "label"):
            if not stat.get(field):
                continue
            name = f"stat {index} {field}"
            assert name in boxes
            components.append(boxes[name])
    for index, first in enumerate(components):
        for second in components[index + 1:]:
            assert (
                first.x1 <= second.x0 or second.x1 <= first.x0
                or first.y1 <= second.y0 or second.y1 <= first.y0
            ), f"{first.name} overlaps {second.name}"


@pytest.mark.parametrize("layout", make_cards.LAYOUTS, ids=lambda layout: layout.suffix or "landscape")
@pytest.mark.parametrize("count", (2, 3))
def test_known_fit_two_and_three_stats_are_accepted(monkeypatch, layout, count):
    stats = [
        {"value": "£135", "tag": "Households", "label": "Average increase", "source": "test"},
        {"value": "12%", "tag": "Adults", "label": "Share affected", "source": "test"},
        {"value": "£1,250", "tag": "Children", "label": "Annual support", "source": "test"},
    ][:count]
    boxes = render_boxes(monkeypatch, layout, fitting_card(stats))
    assert_components_separate(boxes, stats)


STAT = st.fixed_dictionaries({
    "value": st.sampled_from(("£9", "£135", "12%", "£1,250", "1.2m", "£2,000")),
    "tag": st.sampled_from(("", "Households", "Adults", "Children")),
    "label": st.sampled_from(("Annual income", "Average increase", "Share affected")),
    "source": st.just("test"),
})


@settings(max_examples=12, deadline=None)
@given(stats=st.lists(STAT, min_size=2, max_size=3))
def test_varied_stats_have_separate_components(stats):
    # These short, independently known-fit phrases must be accepted, so a
    # blanket refusal cannot make the no-overlap assertion pass vacuously.
    for layout in make_cards.LAYOUTS:
        with pytest.MonkeyPatch.context() as patch:
            boxes = render_boxes(patch, layout, fitting_card(stats))
        assert_components_separate(boxes, stats)


def test_landscape_refuses_value_still_too_wide_at_minimum():
    card = fitting_card()
    card["stats"].append({"value": "£8", "label": "Annual support", "source": "test"})
    card["stats"][0]["value"] = "£123456789012345678901234567890"
    with pytest.raises(CardError, match=r"known-fit: the stat 1 value.*minimum 36px"):
        make_cards.render(make_cards.LAYOUTS[0], card, None)


@pytest.mark.parametrize("layout", make_cards.LAYOUTS, ids=lambda layout: layout.suffix or "landscape")
@pytest.mark.parametrize("field", ("kicker", "headline", "footer", "note", "stat 1 tag", "stat 1 label"))
def test_wrapping_errors_name_card_layout_and_field(layout, field):
    card = deepcopy(fitting_card())
    if field.startswith("stat "):
        card["stats"][0][field.split()[-1]] = "W" * 200
    else:
        card[field] = "W" * 200
    with pytest.raises(CardError) as caught:
        make_cards.render(layout, card, None)
    message = str(caught.value)
    assert f"{card['id']}{layout.suffix}:" in message
    assert field in message


@pytest.mark.parametrize(("first", "second"), (
    ("stat 1 value", "stat 2 value"),
    ("stat 1 tag", "stat 2 value"),
    ("stat 1 label", "stat 2 value"),
    ("stat 1 tag", "stat 1 label"),
    ("stat 1 label", "stat 2 label"),
))
def test_check_rejects_overlapping_stat_components(first, second):
    layout = make_cards.LAYOUTS[0]
    canvas = Card(layout.w, layout.h)
    for name, bounds in {
        "kicker": (56, 50, 180, 70),
        "headline": (56, 100, 800, 140),
        "footer": (56, 600, 500, 620),
        "logo": (950, 590, 1144, 630),
        first: (56, 220, 400, 260),
        second: (350, 240, 650, 280),
    }.items():
        canvas.note(name, *bounds)
    make_cards.record_stats_box(canvas)
    with pytest.raises(CardError, match=f"{first} overlaps {second}"):
        make_cards.check(canvas, layout, "collision")
