// Global UI glue: HTMX error toasts and the Alpine components used by the templates.

function showToast(message, isError) {
  const slot = document.getElementById("toast");
  if (!slot) return;
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " error" : "");
  el.textContent = message;
  slot.replaceChildren(el);
  setTimeout(() => el.remove(), 4000);
}

document.addEventListener("htmx:responseError", (event) => {
  showToast(`Something went wrong (${event.detail.xhr.status})`, true);
});
document.addEventListener("htmx:sendError", () => {
  showToast("Network error, check your connection", true);
});

// Native date picker in the day header; an empty value means the picker was cleared.
function jumpToDay(value, today) {
  if (!value) return;
  window.location.assign(value >= today ? "/" : `/day/${value}`);
}

document.addEventListener("alpine:init", () => {
  // Calories follow 4P + 4C + 9F until the user types their own number.
  Alpine.data("macroForm", () => ({
    caloriesTouched: false,
    init() {
      const value = this.field("calories").value;
      this.caloriesTouched = value !== "" && Number(value) !== this.computed();
    },
    field(name) {
      return this.$root.querySelector(`[name=${name}]`);
    },
    num(name) {
      const value = parseFloat((this.field(name).value || "0").replace(",", "."));
      return Number.isFinite(value) ? value : 0;
    },
    computed() {
      return Math.round(4 * this.num("protein") + 4 * this.num("carbs") + 9 * this.num("fat"));
    },
    autofill() {
      if (this.caloriesTouched) return;
      const calories = this.computed();
      this.field("calories").value = calories ? calories : "";
    },
  }));

  // Filters the log sheet's tiles by name; names arrive lowercased from the template.
  Alpine.data("foodSearch", () => ({
    q: "",
    matches(name) {
      const query = this.q.trim().toLowerCase();
      return !query || name.includes(query);
    },
    any(names) {
      return names.some((name) => this.matches(name));
    },
  }));

  // Bottom sheet; its body is (re)loaded from the server every time it opens.
  // htmx.ajax rather than an hx-trigger: after a boosted navigation Alpine can run
  // init() before htmx has processed the swapped-in nodes, so a trigger would be lost.
  Alpine.data("logSheet", (autoOpen) => ({
    open: false,
    init() {
      if (autoOpen) this.show();
      // Returning from another app can leave the focused field hidden under the keyboard.
      document.addEventListener("visibilitychange", () => {
        const el = document.activeElement;
        if (this.open && !document.hidden && this.$root.contains(el)) {
          setTimeout(() => el.scrollIntoView({ block: "center" }), 300);
        }
      });
    },
    show() {
      this.open = true;
      const body = this.$refs.body;
      htmx.ajax("GET", body.dataset.url, { target: body, swap: "innerHTML" });
    },
    hide() {
      this.open = false;
    },
  }));

  // Chart instances live outside Alpine's reactive proxy (Chart.js breaks when proxied).
  Alpine.data("historyCharts", (initialDays) => {
    let charts = [];
    return {
      days: initialDays,
      init() {
        this.load();
      },
      destroy() {
        charts.forEach((chart) => chart.destroy());
        charts = [];
      },
      setRange(days) {
        this.days = days;
        this.load();
      },
      async load() {
        const response = await fetch(`/history/data?days=${this.days}`);
        if (!response.ok) {
          showToast("Couldn't load charts", true);
          return;
        }
        this.render(await response.json());
      },
      render(data) {
        this.destroy();
        const css = getComputedStyle(document.documentElement);
        const color = (name) => css.getPropertyValue(name).trim();
        Chart.defaults.color = color("--muted");
        Chart.defaults.borderColor = color("--border");
        const labels = data.labels.map((iso) => iso.slice(5));
        const base = {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
        };
        const legend = { labels: { boxWidth: 12, filter: (item) => !item.text.endsWith("target") } };
        const targetLine = (label, values, lineColor) => ({
          type: "line", label, data: values, borderColor: lineColor, borderDash: [6, 4],
          borderWidth: 1.5, pointRadius: 0, stepped: true, spanGaps: true,
        });
        charts = [
          new Chart(this.$refs.calories, {
            type: "bar",
            data: {
              labels,
              datasets: [
                { type: "bar", label: "Calories", data: data.series.calories, backgroundColor: color("--cal"), borderRadius: 4 },
                targetLine("Calories target", data.targets.calories, color("--muted")),
              ],
            },
            options: { ...base, plugins: { legend } },
          }),
          new Chart(this.$refs.macros, {
            type: "line",
            data: {
              labels,
              datasets: ["protein", "fat", "carbs"].flatMap((key) => [
                {
                  label: key[0].toUpperCase() + key.slice(1), data: data.series[key],
                  borderColor: color(`--${key}`), backgroundColor: color(`--${key}`),
                  tension: 0.25, pointRadius: 2, spanGaps: false,
                },
                targetLine(`${key} target`, data.targets[key], color(`--${key}`)),
              ]),
            },
            options: { ...base, plugins: { legend } },
          }),
        ];
      },
    };
  });
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}
