---
name: presentation
description: Use when the user asks to create a presentation, slide deck, or pitch. Also use when they say "make slides", "presentation for", "slide deck", or want to present updates, features, or a product overview.
---

# Presentation

Create distinctive, fullscreen HTML slide decks. Light editorial aesthetic with one strong accent color, real brand assets (logos, photos), polished motion, and Vercel-ready deployment. No dependencies.

## Aesthetic direction (default)

The default look is **light editorial with a single mint-green accent** — inspired by near.com and editorial fintech. White-cream background, dark text, generous whitespace, big bold headlines, dark callout panels for terminals and code, real product/brand assets when relevant.

If the user wants a different vibe (dark, brutalist, terminal, glass-vibrant, magazine), build options first — see "Options pass" below.

## Design system

```css
:root {
    /* Surfaces */
    --bg: #fafaf7;          /* main bg */
    --bg-2: #ffffff;         /* cards */
    --bg-cream: #f5f3ee;     /* secondary cards, panels */
    --bg-dark: #0a0a0a;      /* dark callouts, code, terminals */

    /* Type */
    --text: #0a0a0a;
    --dim: #6b6b6b;
    --muted: #a0a0a0;

    /* Lines */
    --line: rgba(0,0,0,0.08);
    --line-2: rgba(0,0,0,0.16);

    /* Accent — pick ONE color, use it sparingly */
    --mint: #00ec97;
    --mint-deep: #00b370;
    --mint-soft: rgba(0,236,151,0.12);
    --mint-line: rgba(0,236,151,0.35);

    /* Type families */
    --display: 'Inter', system-ui, sans-serif;
    --mono: 'JetBrains Mono', ui-monospace, monospace;
}
```

**Typography rules**
- Display: Inter, weight 700 or 800, letter-spacing -0.045em, line-height 0.85–0.9
- Body: Inter, weight 400
- Mono: JetBrains Mono for labels, eyebrows, status indicators, code
- Headlines are sentence-case ("The stack for agents is NEAR.") — never all caps for display
- Eyebrow labels are mono uppercase letter-spacing 0.16em

**Color rules**
- Bg, surfaces, cards: warm light tones
- Text: pure black for body
- Accent (mint): only for emphasis, callouts, active states, layer markers, status dots, separators, NEAR-style "flip" highlights
- Dark `#0a0a0a` panels for: code blocks, terminal panels, stats bars, the final "thank you" slide
- Never split the deck visually — keep light overall, let dark panels create rhythm

## Headline pattern

Two-line headlines with mint emphasis on the second line. This is the deck's signature move.

```html
<h2 class="display lg">
    The stack for<br>
    agents is <span class="mint">NEAR.</span>
</h2>
```

The mint line carries the punchline. The first line sets up the thought. Use this on chapter title slides, hero slides, and anywhere you want a beat.

## Slide layouts (pick from this menu)

### 1. Title slide
Center-aligned: speaker label, two-line display headline with mint, lede, speaker chip with profile picture.

### 2. Chapter title (big single name)
Pill eyebrow ("CHAPTER 01 · LAYER 3 · RUNTIME"), massive single-word display in mint ("IronClaw."), short lede, optional split with a square image on the right (`.ironclaw-art`).

### 3. Problem grid + arrow target
Four small cards in a row, then a mint arrow target card that "concludes" the problem. Used for "the web is broken" → AI Operating System pattern. Every card has eyebrow + bold name + optional subtitle, all centered vertically.

### 4. Three-layer stack
Vertical stack of 3 layers (L1/L2/L3), each layer a card. Live layers get dark fill or mint fill, others stay white/cream.

### 5. Pillar grid (3 or 4 cards)
3 or 4 small cards with eyebrow + bold name + short paragraph. Used for "key principles" / "what changes" / "pillars" beats.

### 6. Stats hero
Three or four giant numbers (`clamp(3rem, 9vw, 7rem)`) with mono labels underneath. The standout number is mint.

### 7. Comparison table
Two-column compare. Light side / dark side. Mono eyebrow on each row, bold value on the right. Cap rows at 4 — five is too many.

### 8. Five-step process
Five horizontal cards each with step number, icon (custom small SVG), bold name, paragraph. Step 4 is mint to highlight settlement / climax.

### 9. Code panel
Dark `#0a0a0a` rounded panel, mac-style window dots in the header, mint live-dot, mono code with subtle syntax highlighting (mint for keywords, white for strings, gray for comments).

### 10. Chat simulation
A chat window styled like a messaging app: header with avatar + status, alternating user (dark, right-aligned) and bot (light bordered, left-aligned) messages. Inline action cards for flight bookings, payments, transactions. Messages animate in sequentially with staggered delays.

### 11. Terminal panels (live demo)
Dark terminal cards with mac-style header dots, mono content with timestamps, mint events, status indicators. Used for showing logs, agent reasoning, policy YAML.

### 12. Real chain icons grid
Pull official logos from CoinMarketCap. Each chain in a rounded chip with image + uppercase mono name. Featured chain (NEAR) has mint fill + concentric pulse rings.

## Real assets

**Chain logos (CoinMarketCap):**
```bash
mkdir img
curl -sL -o img/btc.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/1.png"
curl -sL -o img/eth.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/1027.png"
curl -sL -o img/sol.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/5426.png"
curl -sL -o img/usdc.png "https://s2.coinmarketcap.com/static/img/coins/64x64/3408.png"
curl -sL -o img/near.png "https://s2.coinmarketcap.com/static/img/coins/64x64/6535.png"
curl -sL -o img/arb.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/11841.png"
curl -sL -o img/base.png "https://s2.coinmarketcap.com/static/img/coins/64x64/27716.png"
curl -sL -o img/tron.png "https://s2.coinmarketcap.com/static/img/coins/64x64/1958.png"
curl -sL -o img/xrp.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/52.png"
curl -sL -o img/avax.png "https://s2.coinmarketcap.com/static/img/coins/64x64/5805.png"
curl -sL -o img/pol.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/28321.png"
curl -sL -o img/apt.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/21794.png"
curl -sL -o img/sui.png  "https://s2.coinmarketcap.com/static/img/coins/64x64/20947.png"
```

**Profile pictures:** ask the user for an image URL or local file. Save to `img/profile.jpg`. Use it in the title slide speaker chip and the thank-you slide. Verify which image is the speaker — Twitter URLs aren't always self-evident.

**All images must be local.** pywebview and offline previews break with remote URLs.

## Delight (built into the template)

- **Cursor-follow radial glow** on all cards (`--mx`, `--my` CSS variables wired up via JS)
- **3D tilt on hover** for cards (subtle, 4° max)
- **Card lift on hover** with soft drop shadow
- **Gradient mesh background** (`.mesh-bg`) drifts slowly behind chapter title slides
- **Floating mint sparkles** (`.sparkles` container with empty `<span>` children)
- **Pulsing live dots** on status indicators
- **Concentric burst rings** on the featured NEAR chip
- **Slide enter scale-in** transition (0.985 → 1)
- **Progress orbit** (small SVG ring in the bottom-right showing current slide)
- **Confetti on the final slide** (60 mint/white pieces fall on entry)
- **Stat count-up** animation when a stats slide enters view
- **Headline reveal stagger** with `.r` + `.d1`–`.d6` classes

Don't add: cursor trail dots, animated underlines on headlines (both look amateur — the user explicitly killed them).

## Responsive guards

The template includes media queries for:
- 16:9 / short heights (≤900px, ≤720px) — tighter padding, smaller display
- Narrow (≤1100px) — smaller display, IronClaw split tightens
- Below 900px wide — splits stack, grids → 2 cols
- Below 600px — single column
- Portrait — splits stack
- Ultrawide (≥21:9) — content capped at 1500px so layout doesn't stretch

`.inner` is capped at `max-width: 1680px` and centered. Test on the real screen.

## Process

1. **Gather content.** What's the talk about? What slides? Who's speaking? What real assets are available?
2. **Outline 12–18 slides.** One idea per slide. Show outline to the user before building.
3. **Download images locally.** Chain logos, profile pictures, screenshots.
4. **Build the deck.** Copy `template.html` to a new project dir as `index.html`. Replace example slides one by one.
5. **Vary layouts.** Never use the same layout for two adjacent slides. Mix chapter titles, problem grids, stats heros, comparison tables, code, chat sims, etc.
6. **Add a chat sim somewhere.** If the talk involves a product doing something for the user, simulate a real conversation. It's the highest-impact slide format in this style.
7. **Launch with pywebview** for fullscreen review.
8. **Iterate** based on the user's feedback.
9. **Deploy to Vercel** if the user has the CLI:
   ```bash
   cd path/to/deck && vercel deploy --prod --yes
   ```

## Options pass (when the aesthetic isn't clear)

If the user's aesthetic preference isn't clear, build a separate `options.html` with **5 distinct directions** applied to two slides each (title + a content slide). Aesthetics that work well as comparison points:
- **Editorial cream** (warm dark brown bg, Fraunces serif, amber accent)
- **Brutalist mono** (pure black, Space Mono, red accent, heavy borders)
- **Phosphor terminal** (CRT green, scanlines, retro)
- **Glass vibrant** (deep navy, frosted glass cards, gradient text)
- **NEAR pure** (white, Inter, mint accent — this skill's default)

Then ship the chosen direction across all slides. Don't iterate on five at once.

## Launching

Fullscreen pywebview window:
```bash
python3 -c "
import webview
webview.create_window('Title', '/abs/path/to/index.html', fullscreen=True)
webview.start()
" &
```
Requires: `pip3 install pywebview`.

To reload after edits: `pkill -f "your-deck-folder/" 2>/dev/null; sleep 0.6;` then re-run.

## Script generation (final pass)

After the deck is solid, offer to write a **cue-card version** of the script. For each slide:
- 🎯 hook (opening line, exact words)
- 3 short beats
- → bridge to next slide

Save as `cuecards.md` next to the deck. Memorize the opening 15s and closing 30s verbatim; the rest hits beats not words.

## What NOT to do

- Don't use Plus Jakarta Sans, Roboto, Arial, or stock fonts. Inter + JetBrains Mono is the default.
- Don't put text at the bottom of cards via `space-between` — center it.
- Don't use em dashes (`—`) in slide text. Periods or middle dots (`·`) instead.
- Don't add corner metadata clutter (LIVE TALK · APR 2026 · SEOUL · 17 SLIDES). Title slides should breathe.
- Don't make cards five-column dense if four works.
- Don't use the same diagram pattern for every architecture slide.
- Don't put stats and dashboards on every slide. Vary cadence: chapter title → content → callout → demo → quote.

## Template

See `template.html` in this directory for the full boilerplate with the design system, component CSS, JS controller, and example slides. Copy it as the starting point.
