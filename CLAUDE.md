# Macro Log

See README.md for setup, tests and deploy.

## UI Conventions

Dark glassmorphism, dark-only. All styling lives in `app/static/css/app.css`, which is served as-is: there is no
Tailwind or build step, so a new class works as soon as it's in that file.

- **Aurora:** `.aurora` (three blurred glows on a near-black fixed layer) is rendered once in `base.html`. Glass only
  reads as glass over it, so don't remove it or give pages an opaque background.
- **Component classes** are defined once, in the "Glass components" block at the top of `app.css`. Use them in
  templates instead of one-off surface/button styles:
  - `.glass`: cards (`card glass`), quick-food tiles, the nudge, segmented controls.
  - `.glass-strong`: chrome (bottom nav, log sheet). Add `.is-popover` for things that sit over text (header
    menu, toasts) so the text underneath doesn't show through.
  - `.glass-chip`: small badges, e.g. the servings ×2 on an entry.
  - `.glass-input`: every text input, select and textarea, or a wrapper around one (`.weigh-input`, uses
    `:focus-within`).
  - `.accent`: primary buttons (`btn accent`), the + log button, the active range pill. The current nav item, a
    checked `.pill-radio` and an on toggle get the same style through the `.accent` selector list. Add state-driven
    selectors there rather than copying the gradient.
  - `.btn-glass`: secondary buttons (`btn btn-glass`); add `btn-danger` for destructive ones, which fill red on hover.
  - `.pill-radio`: radio groups as pills: `<label class="pill-radio"><input type="radio" …>Label</label>` inside a
    `.pills` row with `role="radiogroup"`.
  - `.glass-card`: hover lift for grid cards; off under `prefers-reduced-motion` and on touch.
  - Don't stack backdrop blurs: `.glass` inside a `.glass-strong` panel has its blur turned off. Each blurred element
    is re-blurred every frame while its container moves or scrolls, and a dozen of them in the log sheet made it
    stutter on phones. Nested glass on an already-blurred tint looks the same without it.
- **Range/filter tabs:** `.segmented.glass` holding buttons; the active one gets `accent` (via Alpine `:class`).
- **Bottom nav** floats clear of the screen edges and is no wider than the page column. Mark the current item with
  `aria-current="page"` (the `nav_item` macro in `base.html` does this); don't add an `active` class.
- **Colors:** use the `:root` tokens. `--accent` is the light tint for text, lines and focus rings; the
  `--accent-from`/`--accent-to` gradient is only for filled controls. Macro colors (`--cal`, `--protein`, `--fat`,
  `--carbs`) are data colors: keep the accent visually distinct from them. `app.js` reads `--muted`, `--border`,
  `--accent` and the macro colors for Chart.js, and appends a hex alpha to `--muted`, so keep that one a 6-digit hex.
- **Contrast:** white text on the accent gradient and `--muted` on glass both need to stay at or above 4.5:1. Check
  new color pairs before using them.
- Write only the standard `backdrop-filter`. There's no prefixer, and Safari 18+ supports it unprefixed.
