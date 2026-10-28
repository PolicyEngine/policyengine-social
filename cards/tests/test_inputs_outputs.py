"""Editor-facing failures and campaign output lifecycle regressions."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import make_cards
from sharecard import CardError


HERE = Path(make_cards.__file__).parent
VALID = {
    "campaign": {"name": "Test campaign", "funder": ""},
    "card": [{
        "id": "one", "kicker": "Budget changes", "headline": "Household income",
        "footer": "policyengine.org", "note": "Annual income.",
        "stats": [
            {"value": "£135", "tag": "Adults", "label": "Average increase", "source": "Research"},
            {"value": "12%", "label": "Share affected", "source": "Research"},
        ],
    }],
    "document": [{"id": "document-one", "title": "Household examples", "cards": ["one"]}],
}


def inline(value):
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key} = {inline(item)}" for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(inline(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def write_campaign(folder, data):
    folder.mkdir(exist_ok=True)
    (folder / "cards.toml").write_text(
        "\n".join(f"{key} = {inline(value)}" for key, value in data.items()), encoding="utf-8",
    )
    return folder


MISSING = object()
# Accent marks, spaces and format characters: a zero-width space, a word
# joiner, a byte order mark and a soft hyphen.
BLANK_LOOKING = ("**", "** ** ", "\u200b", "**\u200b**", "\u2060", "\ufeff", "\u00ad", "\u00a0\u3000")


@pytest.mark.parametrize(("keys", "value", "scope", "field"), [
    (("card",), MISSING, "campaign", "card"),
    (("card",), [], "campaign", "card"),
    (("card",), "wrong", "campaign", "card"),
    (("card", 0), "wrong", "card #1", "card"),
    *[(("card", 0, field), value, "card", field)
      for field in ("id", "kicker", "headline", "footer") for value in (MISSING, "", " ", 135)],
    # A field of nothing but accent marks, spaces or invisible characters draws
    # nothing, so it counts as blank.
    *[(("card", 0, field), value, "card", field)
      for field in ("kicker", "headline", "footer", "note") for value in BLANK_LOOKING],
    (("card", 0, "id"), "../escape", "card", "id"),
    (("card", 0, "note"), 1, "card", "note"),
    (("card", 0, "post"), 1, "card", "post"),
    (("card", 0, "gate"), "", "card", "gate"),
    (("card", 0, "stats"), MISSING, "card 'one'", "stats"),
    (("card", 0, "stats"), "wrong", "card 'one'", "stats"),
    (("card", 0, "stats"), [], "card 'one'", "stats"),
    (("card", 0, "stats", 0), 1, "card 'one'", "stats[1]"),
    *[(("card", 0, "stats", 0, field), value, "card 'one'", field)
      for field in ("value", "label", "source") for value in (MISSING, "", " ", 135)],
    *[(("card", 0, "stats", 0, field), value, "card 'one'", field)
      for field in ("value", "label", "tag") for value in BLANK_LOOKING],
    (("card", 0, "stats", 0, "tag"), 1, "card 'one'", "tag"),
    (("campaign",), "wrong", "campaign", "campaign"),
    (("campaign", "name"), "", "campaign", "name"),
    (("campaign", "funder"), 1, "campaign", "funder"),
    (("campaign", "funder"), "unknown", "campaign", "funder"),
    (("document",), "wrong", "campaign", "document"),
    (("document", 0), "wrong", "document #1", "document"),
    *[(("document", 0, field), value, "document", field)
      for field in ("id", "title") for value in (MISSING, "", " ", 1)],
    (("document", 0, "cards"), MISSING, "document 'document-one'", "cards"),
    (("document", 0, "cards"), [], "document 'document-one'", "cards"),
    (("document", 0, "cards"), "one", "document 'document-one'", "cards"),
    (("document", 0, "cards"), [""], "document 'document-one'", "cards[1]"),
    (("document", 0, "cards"), [1], "document 'document-one'", "cards[1]"),
    (("document", 0, "cards"), ["unknown"], "document 'document-one'", "cards[1]"),
])
def test_invalid_input_names_file_section_and_field(tmp_path, keys, value, scope, field):
    data = deepcopy(VALID)
    table = data
    for key in keys[:-1]:
        table = table[key]
    if value is MISSING:
        del table[keys[-1]]
    else:
        table[keys[-1]] = value
    write_campaign(tmp_path, data)
    with pytest.raises(CardError) as caught:
        make_cards.load(tmp_path)
    message = str(caught.value)
    assert str(tmp_path / "cards.toml") in message
    assert scope in message
    assert field in message


@pytest.mark.parametrize("section", ["card", "document"])
def test_duplicate_ids_are_actionable(tmp_path, section):
    data = deepcopy(VALID)
    data[section].append(deepcopy(data[section][0]))
    write_campaign(tmp_path, data)
    with pytest.raises(CardError, match=rf"cards.toml: {section}.*field id: duplicate"):
        make_cards.load(tmp_path)


def test_card_output_filename_collision_is_refused(tmp_path):
    data = deepcopy(VALID)
    data["card"].append(dict(deepcopy(data["card"][0]), id="one-square"))
    write_campaign(tmp_path, data)
    with pytest.raises(CardError, match="output 'one-square.png' collides"):
        make_cards.load(tmp_path)


@pytest.mark.parametrize(("section", "field", "broken"), [
    ("card", "headline", '"unterminated'),
    ("document", "cards", '["one",'),
])
def test_toml_syntax_errors_name_file_section_id_and_field(tmp_path, section, field, broken):
    (tmp_path / "cards.toml").write_text(f'[[{section}]]\nid = "broken"\n{field} = {broken}')
    with pytest.raises(CardError) as caught:
        make_cards.load(tmp_path)
    message = str(caught.value)
    assert all(part in message for part in (str(tmp_path / "cards.toml"), section, "broken", field, "invalid TOML"))


@pytest.mark.parametrize("problem", ["missing-file", "syntax", "numeric-value", "unknown-card"])
def test_cli_failures_are_actionable_without_tracebacks(tmp_path, problem):
    args = []
    if problem != "missing-file":
        data = deepcopy(VALID)
        if problem == "numeric-value":
            data["card"][0]["stats"][0]["value"] = 135
        write_campaign(tmp_path, data)
        if problem == "syntax":
            (tmp_path / "cards.toml").write_text('[[card]]\nid = "broken"\nheadline = "')
        if problem == "unknown-card":
            args.append("absent")
    result = subprocess.run(
        [sys.executable, str(HERE / "make_cards.py"), str(tmp_path), *args],
        # Cold Pillow/NumPy imports can exceed 20 seconds on a loaded Mac
        # while four rendering workers run. This tests diagnostics, not speed.
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode != 0
    assert "make_cards:" in result.stderr
    assert str(tmp_path / "cards.toml") in result.stderr
    assert "Traceback" not in result.stderr
    if problem == "unknown-card":
        assert "absent" in result.stderr and "ids" in result.stderr


def two_card_campaign(tmp_path):
    data = deepcopy(VALID)
    data["card"].append(dict(deepcopy(data["card"][0]), id="two", headline="Current second page"))
    data["document"][0]["cards"] = ["one", "two"]
    return make_cards.load(write_campaign(tmp_path, data))


@pytest.mark.parametrize("stale", [False, True])
def test_partial_render_uses_current_toml_for_every_document_page(tmp_path, monkeypatch, stale):
    campaign = two_card_campaign(tmp_path)
    out = tmp_path / "rendered"
    out.mkdir()
    if stale:
        Image.new("RGB", (10, 10), "black").save(out / "two-square.png")
    calls = []

    def current_render(layout, card, funder):
        calls.append((card["id"], layout.suffix, card["headline"]))
        return Image.new("RGB", (10, 10), "white"), {}

    monkeypatch.setattr(make_cards, "render", current_render)
    make_cards.render_campaign(campaign, ["one"])
    assert ("two", "-square", "Current second page") in calls
    assert (out / "document-one.pdf").is_file()
    assert b"/Count 2" in (out / "document-one.pdf").read_bytes()
    assert (out / "two-square.png").exists() == stale  # dependency drawn in memory
    if stale:
        assert Image.open(out / "two-square.png").getpixel((0, 0)) == (0, 0, 0)


def test_full_render_removes_obsolete_outputs_but_partial_render_preserves_them(tmp_path, monkeypatch):
    campaign = two_card_campaign(tmp_path)
    out = tmp_path / "rendered"
    out.mkdir()
    for name in ("renamed.png", "renamed-square.png", "deleted-document.pdf", "README.txt"):
        (out / name).write_text("old")
    monkeypatch.setattr(make_cards, "render", lambda *args: (Image.new("RGB", (10, 10)), {}))
    make_cards.render_campaign(campaign, ["one"])
    assert (out / "renamed.png").exists()
    make_cards.render_campaign(campaign, [])
    assert {path.name for path in out.iterdir()} == {
        "one.png", "one-square.png", "two.png", "two-square.png", "document-one.pdf", "README.txt",
    }


@pytest.mark.skipif(not shutil.which("rsvg-convert"), reason="needs rsvg-convert")
@pytest.mark.parametrize("folder", sorted(make_cards.CAMPAIGNS.iterdir()), ids=lambda folder: folder.name)
def test_all_campaign_encoded_outputs_are_deterministic_across_dates(folder, tmp_path, monkeypatch):
    campaign = replace(make_cards.load(folder), folder=tmp_path)
    make_cards.render_campaign(campaign, [])
    out = tmp_path / "rendered"
    first = {path.name: path.read_bytes() for path in out.iterdir()}
    expected = {f"{card['id']}{layout.suffix}.png" for card in campaign.cards for layout in make_cards.LAYOUTS}
    expected.update(f"{doc['id']}.pdf" for doc in campaign.documents)
    assert set(first) == expected
    tomorrow = time.gmtime(time.time() + 86400)
    monkeypatch.setattr(time, "gmtime", lambda *args: tomorrow)
    make_cards.render_campaign(campaign, [])
    assert first == {path.name: path.read_bytes() for path in out.iterdir()}
    for name, data in first.items():
        if name.endswith(".pdf"):
            assert b"/CreationDate" not in data and b"/ModDate" not in data
