# Where these files came from

Copied on 28 October 2026 from the Budget-day webinar share card's assets, which were collected on 13 and 22 October 2026.

| File | From | Licence and notes |
|---|---|---|
| `fonts/RobotoSerif.ttf` | The old PolicyEngine app's social card tool | Roboto Serif 1.008, a variable font, drawn at weight 400. SIL Open Font License 1.1: `fonts/OFL-robotoserif.txt`. |
| `fonts/Roboto-Regular.ttf`, `fonts/Roboto-Bold.ttf` | PolicyEngine's grant document template | Roboto 3.009 (2024). SIL Open Font License 1.1: `fonts/OFL-roboto.txt`. |
| `fonts/OFL-*.txt` | `ofl/roboto/OFL.txt` and `ofl/robotoserif/OFL.txt` in google/fonts on GitHub, 28 October 2026 | The licence texts, which travel with the fonts. |
| `policyengine-white.png` | `app/public/assets/logos/policyengine/white.png` in PolicyEngine/policyengine-app-v2 | 996×207, last changed there on 24 November 2025. |
| `funders/nuffield/logo-white.svg` | nuffieldfoundation.org's theme assets, 22 October 2026, at the Foundation's communications team's request | 3,432 bytes, SHA-256 `b3727385be9295f8daa3938c745f87b2e00e5675130354f6394ae6b3fec5654c`. Never recoloured or altered: `sharecard.py` refuses a file with a different hash, and rasterises it with `rsvg-convert` (librsvg). |

## Why Roboto and not Inter

`@policyengine/ui-kit` sets Inter as its sans font, with Roboto as a fallback, and has no serif. The 15 September 2026 webinar card, which these cards follow, uses Roboto and Roboto Serif: its text was matched by rendering the same words in each font and correlating the pixels.

## Colours

The teal (`#4FD1C5`, teal-300) and the two greys (`#E2E8F0`, `#CBD5E1`) are ui-kit tokens. The navy `#0C1A27` and its two corner glows are measured from the September card; ui-kit has no navy.
