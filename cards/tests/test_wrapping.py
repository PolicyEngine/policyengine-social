"""Line wrapping accepts known fits and agrees with a small exhaustive oracle."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sharecard
from sharecard import DOT, CardError, Style, TEAL, line_width, plain, shown, words, wrap


STYLE = Style("bold", 20, TEAL)


def exhaustive_wrap(line, width, max_lines):
    """The former partition search, kept small and independent of wrap()."""
    if line_width(line) <= width:
        return [line]
    for count in range(2, min(len(line), max_lines) + 1):
        best = None
        for cuts in itertools.combinations(range(1, len(line)), count - 1):
            edges = (0, *cuts, len(line))
            parts = []
            for start, end in zip(edges, edges[1:]):
                part = line[start:end]
                while part and plain(part[0]) == DOT:
                    part = part[1:]
                while part and plain(part[-1]) == DOT:
                    part = part[:-1]
                parts.append(part)
            if not all(parts):
                continue
            widths = [line_width(part) for part in parts]
            if max(widths) > width:
                continue
            penalties = []
            for cut in cuts:
                before, after = plain(line[cut - 1]), plain(line[cut])
                if DOT in (before, after) or before[-1] in ".:;?!":
                    penalties.append(-0.5)
                elif before[-1] == ",":
                    penalties.append(-0.15)
                elif any(ch.isdigit() for ch in before):
                    penalties.append(0.3)
                else:
                    penalties.append(0.0)
            cost = (1.25 * max(widths) - 0.25 * min(widths)) / width + sum(penalties)
            if best is None or cost < best[0]:
                best = (cost, parts)
        if best:
            return best[1]
    raise CardError("oracle: no partition fits")


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.sampled_from(["one", "two,", "three.", "28", "October", "£135", DOT]), min_size=1, max_size=9),
    st.integers(65, 300),
    st.integers(1, 6),
)
def test_wrap_matches_exhaustive_balancing(tokens, width, max_lines):
    line = words(" ".join(tokens), STYLE)
    try:
        expected = exhaustive_wrap(line, width, max_lines)
    except CardError:
        with pytest.raises(CardError):
            wrap(line, width, max_lines=max_lines)
    else:
        actual = wrap(line, width, max_lines=max_lines)
        assert [shown(part) for part in actual] == [shown(part) for part in expected]


@pytest.mark.parametrize("max_lines", [1, 2, 3, 4, 6])
def test_known_fit_is_accepted_with_callers_line_limit(max_lines):
    # Each line can contain exactly one word; this is a constructive fit,
    # independently of the wrapper's choice of breaks or its failure path.
    line = words(" ".join(["October"] * max_lines), STYLE)
    width = line_width(line[:1]) + 1
    if max_lines > 1:
        assert line_width(line[:2]) > width
    actual = wrap(line, width, max_lines=max_lines)
    assert len(actual) == max_lines
    assert [shown(part) for part in actual] == ["October"] * max_lines


def test_callers_line_limit_refuses_a_known_nonfit():
    line = words("October October October", STYLE)
    width = line_width(line[:1]) + 1
    with pytest.raises(CardError, match="within 2 lines"):
        wrap(line, width, max_lines=2)
    assert len(wrap(line, width, max_lines=3)) == 3


def test_styled_spans_keep_the_same_balanced_breaks():
    accent = Style("serif", 25, TEAL)
    line = words("The **£100 payment** · zero VAT on electricity", STYLE, accent)
    for width in [150, 225, 300]:
        expected = exhaustive_wrap(line, width, 6)
        actual = wrap(line, width)
        assert [shown(part) for part in actual] == [shown(part) for part in expected]


@pytest.mark.parametrize("limit", [0, -1, 1.5, True])
def test_invalid_line_limit_is_actionable(limit):
    with pytest.raises(CardError, match="line limit must be a positive integer"):
        wrap(words("October", STYLE), 200, max_lines=limit)


def test_oversized_word_is_refused_before_partition_search(monkeypatch):
    line = words(" ".join(["small"] * 39 + ["oversized" * 40]), STYLE)
    original = sharecard.line_width
    calls = 0

    def measured(part):
        nonlocal calls
        calls += 1
        return original(part)

    monkeypatch.setattr(sharecard, "line_width", measured)
    with pytest.raises(CardError, match='word "oversized'):
        wrap(line, 200)
    assert calls <= len(line)


def test_long_known_fit_measures_each_span_at_most_once(monkeypatch):
    # Forty words require six lines. The former exhaustive search considered
    # hundreds of thousands of partitions; width measurements now stay O(n²).
    line = words(" ".join(["word"] * 40), STYLE)
    calls = 0

    def measured(part):
        nonlocal calls
        calls += 1
        return len(shown(part))

    monkeypatch.setattr(sharecard, "line_width", measured)
    actual = wrap(line, 35, max_lines=6)
    assert calls <= len(line) + 1 + len(line) * (len(line) + 1) // 2
    assert len(actual) == 6
    assert [plain(word) for part in actual for word in part] == ["word"] * 40
    assert all(len(shown(part)) <= 35 for part in actual)
