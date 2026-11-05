# Nutrition & weight review: 2026-11-05

Source: app export `macro-log-2026-11-05` (covers 2026-10-13 to 2026-11-04, 23 days).
Kept in the repo as a backup of this review.

## Numbers from the app (as exported)

| Metric | Value |
|---|---|
| Days logged | 22 / 23 (missed 2026-10-20) |
| Days weighed | 14 / 23 (weigh-ins started 2026-10-22, none missed since) |
| Current trend weight | 207.0 lb (93.9 kg) |
| Weight rate (last 14 days, 10-22 to 11-04) | +0.36 lb/week |
| Avg intake, last 14 days | 2,716 kcal |
| Estimated maintenance | 2,535 kcal |
| Implied surplus | 181 kcal/day |
| Avg intake, all logged days | 2,557 kcal · P 163.1 · F 88.4 · C 223.9 |
| Targets in effect (since 2026-10-13) | 2,399 kcal · P 180 · F 75 · C 251 |
| Protein per lb trend weight | 0.79 g/lb (1.74 g/kg) |

The app's maintenance window is 28 days but is clipped to the first weigh-in, so this estimate rests on 14 days.

### By week (app)

| Week of | Avg kcal | Avg protein | Trend change |
|---|---|---|---|
| 2026-11-02 | 2,645 | 185 g | +0.2 |
| 2026-10-26 | 2,754 | 158 g | −0.8 |
| 2026-10-19 | 2,653 | 161 g | – |
| 2026-10-12 | 2,188 | 160 g | – |

## Findings

### 1. Weight is roughly flat to slightly up; the trend line's "drop" is mostly startup settling
- Trend reads 208.1 → 207.0, but the EMA was seeded with the first weigh-in (208.1 on 10-22), a high day. It has been settling toward the true average since. The −0.8 for the week of 10-26 is mostly this, not fat loss.
- Plain weekly averages: week 1 (10-22 to 10-28) **206.2 lb**, week 2 (10-29 to 11-04) **206.7 lb**, i.e. +0.5 lb, consistent with the app's +0.36 lb/wk.
- Daily range 204.6–208.7 lb: ~4 lb of normal water/sodium noise.
- The trend line becomes trustworthy after a few more weeks of weigh-ins.

### 2. Maintenance estimate (~2,535) is believable
- Mifflin-St Jeor for male, 48, 93.9 kg, 180 cm: BMR ≈ 1,829. × ~1.4 (desk job + 4 lifting days) ≈ **2,550**.
- App's data-driven value lands within ~20 kcal of that, so logging looks fairly honest despite heavy Quick add use.
- Still early (14 days); expect it to move as the 28-day window fills.

### 3. Old target (2,399) was below maintenance, so it didn't match the lean-bulk goal
- Hitting 2,399 exactly would have meant ~−0.25 lb/wk.
- Profile goal said Lean bulk, but program notes said "near maintenance or a modest deficit" and "reduce belly fat" (a recomp). Conflict.
- History per notes: 193 lb (~2026-07-13) → 207 lb now = +14 lb in ~16 weeks ≈ 0.9 lb/wk, which is fast for a lean bulk at 48 (typical 0.25–0.5 lb/wk), so likely a good share was fat.

### 4. Alcohol is the biggest single lever
- 59 × "Captain n diet" (86 kcal each) + 1 Moscow mule in 22 logged days ≈ **5,100 kcal ≈ 235 kcal/day**, ~9% of intake.
- By weekday (avg drinks): Mon 0, Tue 0.3, Wed 1, Thu 3, Fri 3.3, **Sat 6, Sun 5.7**.
- Heaviest days had drinks + big late meals: 11-01 (4,000, 7 drinks), 10-29 (3,910), 10-25 (3,422, 7 drinks).
- Lowest-protein days were drinking days: 10-24 (102 g, 7 drinks), 10-31 (122 g, 6 drinks).
- Alcohol logs as calories with ~0 macros, so on drinking days the macro bars understate how close you are to the calorie target.
- Also blunts muscle protein synthesis and sleep.

### 5. Big day-to-day swings
- Range 1,645–4,000 kcal; SD ≈ 640; median 2,509.
- Within ±200 of target on only 7 / 22 days; over target on 12 / 22.
- Avg kcal by weekday: Mon 2,521 · Tue 2,462 · Wed 2,280 · **Thu 3,040** · Fri 2,282 · Sat 2,185 · **Sun 3,225**. Thu and Sun are training days.
- Possibly incomplete days: 10-24 (1,645 kcal, mostly drinks/snacks) and 10-30 (1,751 kcal, 19.5 g fat).

### 6. Protein: adequate, slightly under target
- Avg 163 g = 0.79 g/lb (1.74 g/kg), inside the evidence-based 1.6–2.2 g/kg range.
- Hit 180 g on 8 / 22 days. Min 102 g (10-24).
- Distribution is good: ~3.9 feedings of ≥25 g per day (ISO100 shakes, tuna packs, chicken).
- Fix the low drinking days rather than adding more on normal days.

### 7. Logging detail
- 58 "Quick add" entries ≈ 1,205 kcal/day ≈ 47% of intake. Accuracy seems OK (see #2), but naming repeats would help analysis (e.g. the 534 kcal lunch, the 190 kcal item paired with the Chipotle bowl).
- Top named items: Chipotle chicken bowl (7×, ~207 kcal/day avg), ISO100 shake (34×), Ritz peanut butter (10×), tuna pack (11×).

## Decision (2026-11-05): lean bulk

New targets, effective 2026-11-05:

| | Old | New | Change |
|---|---|---|---|
| Calories | 2,399 | **2,700** | +301 |
| Protein | 180 g | **180 g** | 0 |
| Fat | 75 g | **80 g** | +5 |
| Carbs | 251 g | **315 g** | +64 |

Reasoning:
- Maintenance ~2,535 + ~165 surplus ≈ 2,700 → expected **+0.3 to 0.45 lb/wk**, the slow end of a lean bulk given age and the fast gain since July.
- The last 14 days averaged 2,716 and produced +0.36 lb/wk, so 2,700 is effectively "what you ate, but consistently" instead of swinging 1,645–4,000.
- Protein 180 g ≈ 0.87 g/lb; fat 80 g ≈ 27% of calories; carbs fill the rest to fuel training. Macros sum to exactly 2,700 (4/4/9).
- Drinks count against the 2,700 calories. Aim for ≤2–3 on weekend days.

Profile updates: goal stays Lean bulk; Training and Notes text rewritten to match a lean bulk (Notes previously said "near maintenance or modest deficit").

## What to watch / when to adjust

- Keep weighing in daily; track waist (at the navel, morning) weekly.
- Judge the rate on the app's 4-week number, not daily weights.
- 4-week rate **> +0.5 lb/wk**, or waist up > ~0.5 in/month → drop 150 kcal (from carbs).
- 4-week rate **< +0.2 lb/wk** → add 150 kcal (from carbs).
- Re-export around **2026-11-26 to 2026-12-01** (≥28 days of weigh-ins) and compare against this note.
