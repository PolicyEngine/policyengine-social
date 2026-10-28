# Share cards

The images that go with PolicyEngine's social posts. Each campaign is a folder under `campaigns/` holding one text file, `cards.toml`. The PNGs and PDFs in the campaign's `rendered/` folder are drawn from that file, so to change a card you change its text and the card is drawn again.

| Campaign | Cards |
|---|---|
| [UK Autumn Budget 2026](campaigns/uk-autumn-budget-2026/cards.toml) | [rendered/](campaigns/uk-autumn-budget-2026/rendered/) |

Each card comes in two sizes: `<id>.png` (1200×675) for X and Bluesky, and `<id>-square.png` (1080×1080) for LinkedIn. A campaign can also list documents: PDFs of square cards, one per page, for a LinkedIn document post.

## Change a card on GitHub (nothing to install)

1. Open the campaign's `cards.toml` on GitHub and click the pencil icon (Edit this file).
2. Change the words. Keep the quotation marks around each piece of text.
3. Click **Commit changes** to open the commit dialog. Choose **Create a new branch**, give the branch a name, and click **Propose changes**. On the next page, click **Create pull request** so someone can review the change.
4. To commit directly to the current branch instead, choose that option in the commit dialog and click **Commit changes**.
5. The **Render cards** action runs (see the Actions tab, or the yellow dot then green tick beside the commit). When it finishes, it commits the new images to the campaign's `rendered/` folder on the same branch. Open an image on GitHub and click **Download raw file**. The run's Summary page also has every card as one zip, named `cards`.
6. If some text doesn't fit, the action fails (a red cross) and draws nothing for that card. Its log names the card and the problem, for example `p1-energy-square: the headline needs more than 3 lines`. Shorten that text and commit again.

The action never posts anything. Posting only happens from `posts/queue/` (see the main README).

## What each part of a card is

```
UK Autumn Budget 2026 · Energy bills          Funded by [Nuffield Foundation]   ← kicker; funder credit
The £100 payment and zero VAT on electricity                                     ← headline
£135   England, bands A to D                                                     ← stats: value, tag,
       the £100 payment plus the VAT cut                                           label
Change in net income, 2026-27 and 2027-28 combined.                              ← note
policyengine.org/uk/research/budget-2026-energy-bills          POLICY ENGINE     ← footer; our logo
```

| Field | What it is |
|---|---|
| `id` | The file name: `p1-energy` gives `p1-energy.png` and `p1-energy-square.png`. |
| `kicker` | The small teal line at the top. |
| `headline` | The large serif text. It shrinks to fit its lines (two on the wide card, three on the square) or the card is refused. |
| `stats` | Two or three figures. Each has a `value` (large), a `label` (under or beside it), an optional `tag` (small, above the label) and a `source`, which isn't drawn: it says where the figure comes from, so anyone can check it. |
| `note` | Optional small print above the footer. |
| `footer` | The link, bottom left. |
| `post`, `gate` | Where the card goes and what it waits on. Printed when the cards are drawn, never drawn on the card. |

At the top of the file, `[campaign]` sets the funder: `funder = "nuffield"` draws "Funded by" and the Nuffield Foundation's logo; `funder = ""` draws none. Each `[[document]]` lists the cards to put in one PDF, in page order.

To add a card, copy a whole `[[card]]` block, give it a new `id` and change its text. To start a campaign, make a folder under `campaigns/` with its own `cards.toml`.

## The rules the cards follow

- **Sentence case** for every line, kicker included: capitalise only the first word and proper nouns.
- **No emoji.** The renderer refuses a character the fonts can't draw.
- **Every figure names its source.** Change a figure only with its source, and say what changed.
- **The card is PolicyEngine's.** Our wordmark sits alone at the bottom right. A funder's credit is small, at the top right, in a different corner: side by side at the same size the two logos read as a partnership (Max Ghenis, 28 October 2026). The funder's logo is drawn from the file they supplied; the renderer refuses an altered copy.
- **In the posts themselves**, credit the funder once per thread, in the first post, and once in each LinkedIn post. The credit on every card is enough for the replies.

## Draw the cards on your own computer

On a Mac with [Homebrew](https://brew.sh):

```bash
brew install librsvg fribidi uv
```

Then, from this `cards` folder:

```bash
DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib" uv run make_cards.py campaigns/uk-autumn-budget-2026
```

Add card ids after the folder to draw only those, for example `… campaigns/uk-autumn-budget-2026 p1-energy`. With no folder it draws every campaign. It prints every line it draws, so you can check the wording.

A Mac draws the same cards with slightly different anti-aliasing from the action's Linux runner, so the files differ by a few bytes while looking the same. When you push, the action redraws the cards and commits its own versions, so the files on GitHub are always the action's.

Run the tests with:

```bash
DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib" uv run --group dev pytest
```

## Where things come from

`sharecard.py` draws the type, logos and background; `make_cards.py` lays out each card and checks that nothing is clipped or overlapping. The fonts, logos and colours, and where each came from, are listed in [assets/SOURCES.md](assets/SOURCES.md).
