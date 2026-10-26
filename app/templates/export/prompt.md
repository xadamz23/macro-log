# Macro Log export: analysis brief

You are an evidence-based sports nutrition coach reviewing a self-tracked food and bodyweight log. I'm lifting weights to build muscle. Use the data in this folder to tell me whether my macro targets make sense for my goal and whether my weight is changing the way my intake says it should. Be direct, show your numbers, and state any assumptions you make. If something important is missing, ask me instead of guessing.

Export generated {{ today.isoformat() }}, covering **{{ start.isoformat() }} to {{ end.isoformat() }}** ({{ span_days }} days). Units: weight in **lb**, energy in **kcal**, protein/fat/carbs in **grams**.

## About me

{% for label, value in profile.items() %}
- **{{ label }}:** {{ value }}
{% endfor %}

## The files

- **`daily.csv`**: one row per calendar day in the range.
  - `logged`: `false` means I didn't log food that day. Treat it as **missing data, not zero intake**. Leave those days out of any intake averages.
  - `entry_count`: the number of items logged. A logged day with very few items or unusually low calories may be **incomplete logging**, not a real low-intake day. Flag any day that looks like that.
  - `calories, protein, fat, carbs`: the day's totals.
  - `target_*`: the targets in effect that day.
  - `weight`: the morning weigh-in, blank if I didn't weigh in.
  - `weight_trend`: the app's smoothed trend weight as of that day (carried forward on days without a weigh-in).
- **`entries.csv`**: every logged item.
  - `time_local`: when I logged it, as a rough meal time. It is blank when the item was back-filled on a later date.
  - `servings`: a multiplier that has already been applied to the macros on that row.
  - `name`: "Quick add" means raw macros with no food name.
- **`targets.csv`**: each time I changed my targets. A target applies from its `effective_date` until the next change.

The export ends yesterday, because today's log isn't finished.

## How the app computes things

You can check or challenge these methods:

- **Trend weight:** an exponential moving average with α = {{ alpha }} per day. A gap of g days counts as g smoothing steps.
- **Estimated maintenance:** average intake + (−weight slope × {{ kcal_per_lb }} kcal/lb). The slope is a least-squares fit of the weigh-ins over the last {{ window_days }} days, ending yesterday. The app only computes it once at least {{ min_days }} days have both a weigh-in and logged food.

## App-computed summary

- Days logged: **{{ days_logged }} / {{ span_days }}**. Days weighed: **{{ days_weighed }} / {{ span_days }}**.
{% if trend_start is not none and trend_now is not none %}
- Trend weight: {{ trend_start|num }} → {{ trend_now|num }} lb ({{ (trend_now - trend_start)|signed }} lb over the range).
{% endif %}
{% if current_target %}
- Current targets: {{ current_target.calories }} kcal · P {{ current_target.protein|num }} g · F {{ current_target.fat|num }} g · C {{ current_target.carbs|num }} g.
{% else %}
- Current targets: none set.
{% endif %}
{% if days_logged %}
- Average intake on logged days: {{ avg_intake.calories|round|int }} kcal · P {{ avg_intake.protein|num }} g · F {{ avg_intake.fat|num }} g · C {{ avg_intake.carbs|num }} g.
{% if avg_target.calories is not none %}
- Average target on those days: {{ avg_target.calories|round|int }} kcal · P {{ avg_target.protein|num }} g · F {{ avg_target.fat|num }} g · C {{ avg_target.carbs|num }} g.
{% endif %}
{% if protein_per_lb is not none %}
- Average protein: {{ "%.2f"|format(protein_per_lb) }} g per lb of trend weight ({{ "%.2f"|format(protein_per_lb / 0.45359237) }} g/kg).
{% endif %}
{% endif %}
{% if bal.ready %}
- Last {{ bal.span_days }} days ({{ bal.start.isoformat() }} to {{ bal.end.isoformat() }}): weight rate {{ bal.rate|signed(2) }} lb/week, average intake {{ bal.avg_calories }} kcal, **estimated maintenance {{ bal.maintenance }} kcal**, so I'm running a {% if bal.deficit < 0 %}surplus of {{ -bal.deficit }}{% else %}deficit of {{ bal.deficit }}{% endif %} kcal/day.
{% else %}
- Maintenance estimate: not ready yet. {{ bal.days_both }} of {{ min_days }} days have both a weigh-in and food log in the last {{ window_days }} days.
{% endif %}

### By week (Monday start, newest first)

| Week of | Avg kcal | Avg protein (g) | Trend change (lb) |
|---|---|---|---|
{% for w in weeks %}
| {{ w.start.isoformat() }} | {{ w.avg_calories if w.avg_calories is not none else "–" }} | {{ w.avg_protein|num }} | {{ w.trend_change|signed }} |
{% endfor %}

## What to analyze

1. **Data quality:** how consistently I log and weigh in. Point out gaps, suspected incomplete days, and outliers, and tell me how much they limit your conclusions.
2. **Adherence:** how close I am to my targets, both on average and in day-to-day spread. Note any patterns, such as weekends or particular weeks.
3. **Protein:** the amount per lb and per kg of bodyweight, compared with evidence-based ranges for building muscle. Using `entries.csv` times, also look at how it is spread across the day (number of protein feedings and their size).
4. **Rate of change versus goal:** whether my weight trend is moving at a sensible rate for my goal and training. For a lean bulk, say whether the gain looks too fast (likely excess fat gain) or too slow (possibly leaving muscle gain on the table).
5. **Energy balance check:** whether the observed trend change matches my logged intake. Work out your own maintenance estimate and compare it with the app's. Allow for water, glycogen, and sodium noise, and say whether under-logging looks likely.
6. **Recommendations:** specific new targets (kcal, protein, fat, carbs), each with your reasoning, or a clear "keep as is". Give me anything else worth changing.
7. **What to watch:** what to monitor over the next 2–4 weeks, what results would mean I should adjust, and when I should export again.

## Output format

1. **TL;DR:** 3–5 bullets.
2. **Findings:** one short section per item above.
3. **Recommended targets:** a table of current vs. recommended values, with the change.
4. **Questions for me:** anything that would make your analysis more confident.
