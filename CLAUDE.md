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
  - `.accent`: primary buttons (`btn accent`), the active range pill. The current nav item, a
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
- **Bottom nav** floats clear of the screen edges and is no wider than the page column. The + log button is a flat
  44px accent-outline ring (`.log-btn`), not `.accent`, so it doesn't read as a second current-page pill. Mark the current item with
  `aria-current="page"` (the `nav_item` macro in `base.html` does this); don't add an `active` class.
- **Desktop (1100px and up) must not change phones.** Phones keep exactly the layout they have. Markup for desktop
  only gets `desktop-only` (hidden below 1100px), markup for phones only gets `mobile-only`, and desktop layout rules
  live inside `@media (min-width: 1100px)`. Before committing a desktop change, screenshot every page (and the open
  log sheet) at 390px and 1000px on the old and new code and check they're identical.
  - **Shell:** a fixed `.side` sidebar (in `base.html`) replaces the bottom nav and the header menu, which hide. Its
    Log food button (`side_log_button` block) opens the sheet on the day page and links to `/?log=1` elsewhere. The
    log sheet opens as a right-hand drawer that slides in and out (240ms; the Alpine `x-transition` classes on it
    only have CSS on desktop, so phones stay instant); it stays closed until asked for. `app.js` adds desktop-only
    shortcuts: N or / opens the sheet with the food search focused, ← / → step through days.
  - **Day page:** same 1240px column and gutters as the History/Weight dashboards, date flush left and a
    ‹ Today › pill (`.day-step`) on the right in place of the title's arrows (those stay in the markup, hidden, for the
    ← / → shortcut). Below: a week strip (`partials/week_strip.html`), the macros as four KPI cards (`#day-kpis`,
    rendered next to the phone-only `#bars` in `macro_bars.html`; both refresh out of band after each write), and
    entries as table columns (`.entry-cols` inside the row's button), each with a share-of-target bar sized from
    `--kcal` on the row and `--kcal-target` on `#entries`.
  - **History, Weight:** `.dash` turns each page into a 12-column grid (`grid-template-areas` in the "Desktop
    dashboards" block of `app.css`). Each `.charts` card becomes `display: contents` so its `.chart-panel`s and range
    control are grid items; on phones the panels are flattened back into the one glass card.
  - **Foods, Settings:** two columns (`page_class` block on `<main>`). Settings places its cards on the grid by id
    rather than wrapping them, so phones keep the card order.
  - **Equal heights:** cards that share a grid row stretch to it (`align-self: stretch`). A chart or scrolling list
    that should follow the row rather than set it gets `contain: size` and a `min-height`.
- **Colors:** use the `:root` tokens. `--accent` is the light tint for text, lines and focus rings; the
  `--accent-from`/`--accent-to` gradient is only for filled controls. Macro colors (`--cal`, `--protein`, `--fat`,
  `--carbs`) are data colors: keep the accent visually distinct from them. `app.js` reads `--muted`, `--border`,
  `--accent` and the macro colors for Chart.js, and appends a hex alpha to `--muted`, so keep that one a 6-digit hex.
- **Contrast:** white text on the accent gradient and `--muted` on glass both need to stay at or above 4.5:1. Check
  new color pairs before using them.
- Write only the standard `backdrop-filter`. There's no prefixer, and Safari 18+ supports it unprefixed.

## Parked features

- **Recent foods:** the log sheet's "Recent" grid (named entries from the last 30 days, top 8, each removable) is
  switched off, not deleted. Still in the code: the `HiddenRecentFood` model and migration 0005, `recent_foods` and
  `hide_recent_food` in `app/services/foods.py`, `POST /recent-foods/hide`, the unreferenced
  `partials/recent_foods.html`, and their tests. To bring it back, add `"recent": recent_foods(db, today)` to
  `sheet_context` in `app/views.py`, include the partial after the quick foods in `log_sheet.html` and make its outer
  check `{% if quick_foods or recent %}`; or revert the commit that parked it (`git log --grep "park the Recent"`).
  Last commit with it on: `924f8a1`.
- **Undo on the logged toast:** the Undo button on the "Logged <name>" toast is commented out in
  `partials/day_refresh.html`, at the user's request because it was annoying them. The toast itself stays, shortened
  from 6s to 2s (12s to 4s when it carries a detail line). To bring Undo back, remove the `{# … #}` around the button.
  Last commit with Undo: `1bc00c0`.
