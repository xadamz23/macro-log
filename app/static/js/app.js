// Global UI glue: HTMX error toasts and the Alpine components used by the templates.

function showToast(message, isError) {
  const slot = document.getElementById("toast");
  if (!slot) return;
  const el = document.createElement("div");
  el.className = "toast glass-strong is-popover" + (isError ? " error" : "");
  el.textContent = message;
  slot.replaceChildren(el);
  setTimeout(() => el.remove(), 4000);
}

document.addEventListener("htmx:responseError", (event) => {
  const { xhr } = event.detail;
  showToast(xhr.getResponseHeader("X-Error-Message") || `Something went wrong (${xhr.status})`, true);
});
document.addEventListener("htmx:sendError", () => {
  showToast("Network error, check your connection", true);
});

// A smaller JPEG copy of a photo, used for both the preview and the upload. A full-size camera photo (12 MP is ~48 MB
// decoded) inside the blurred sheet made iOS drop and repaint it, so the sheet flickered. Claude doesn't use more
// detail than this, and it converts formats the API won't take, such as HEIC.
async function shrinkPhoto(file, maxSide = 1568) {
  const full = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = full;
    await img.decode();
    const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob || file;
  } catch {
    return file; // couldn't decode it here; send the original and let the server decide
  } finally {
    URL.revokeObjectURL(full);
  }
}

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

  // Log sheet's "Log from a photo": camera or library → preview → POST /entries/photo, where Claude estimates the
  // macros and the entry is logged. Shown only when the server has an API key; the sheet closes on entry-logged, and
  // on failure the photo and description stay so a retry is one tap.
  Alpine.data("photoLog", () => ({
    step: null,
    picked: null,
    upload: null,
    url: "",
    what: "",
    fork: true,
    busy: false,
    destroy() {
      if (this.url) URL.revokeObjectURL(this.url);
    },
    async choose(event) {
      const file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      this.picked = file;
      const upload = await shrinkPhoto(file);
      if (this.picked !== file) return; // another photo was picked meanwhile
      if (this.url) URL.revokeObjectURL(this.url);
      this.upload = upload;
      this.url = URL.createObjectURL(upload);
      this.step = "preview";
    },
    // The file inputs have no name, so htmx leaves them out and the shrunk copy is added here instead.
    attach(event) {
      event.detail.formData.set("photo", this.upload, this.upload.name || "meal.jpg");
    },
    // The sheet shows its old body until the reload lands, so clear the photo before it slides back up.
    reset() {
      if (this.url) URL.revokeObjectURL(this.url);
      Object.assign(this, { step: null, picked: null, upload: null, url: "", what: "", fork: true, busy: false });
    },
    back() {
      this.step = this.step === "preview" ? "pick" : null;
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

  // Weight chart: daily weigh-ins as dots, the smoothed trend as a line.
  Alpine.data("weightChart", (initialDays) => {
    let chart = null;
    return {
      days: initialDays,
      init() {
        this.load();
      },
      destroy() {
        chart?.destroy();
        chart = null;
      },
      setRange(days) {
        this.days = days;
        this.load();
      },
      async load() {
        const response = await fetch(`/weight/data?days=${this.days}`);
        if (!response.ok) {
          showToast("Couldn't load chart", true);
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
        const monthDay = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
        chart = new Chart(this.$refs.chart, {
          type: "line",
          data: {
            labels: data.labels.map((iso) => monthDay.format(new Date(iso))),
            datasets: [
              {
                label: "Daily weigh-in", data: data.weights, showLine: false,
                pointRadius: 2.5, pointBackgroundColor: color("--muted") + "80", pointBorderWidth: 0,
              },
              {
                label: "Trend", data: data.trend, borderColor: color("--accent"), backgroundColor: color("--accent"),
                borderWidth: 2.5, pointRadius: 0, tension: 0.3, spanGaps: true,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8, boxHeight: 8 } } },
            scales: {
              x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 5 } },
              y: { grace: 1, ticks: { precision: 0, maxTicksLimit: 6 } },
            },
          },
        });
      },
    };
  });
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}
