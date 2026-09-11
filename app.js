"use strict";

/* =========================================================================
 * Slide type definitions — field schemas drive the builder UI.
 * ========================================================================= */

const SLIDE_TYPES = {
  hero: {
    label: "Hero / cover",
    fields: [
      { key: "kicker", label: "Kicker (small label)", type: "text" },
      { key: "title", label: "Title", type: "text", required: true, placeholder: "Presentation title" },
      { key: "subtitle", label: "Subtitle", type: "text" },
      { key: "presenter", label: "Presenter", type: "text" },
      { key: "date", label: "Date", type: "text", placeholder: "e.g. March 2025" },
    ],
  },
  statement: {
    label: "Statement",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Statement", type: "textarea", required: true, placeholder: "One bold idea, one slide." },
      { key: "caption", label: "Caption", type: "text" },
    ],
  },
  cards: {
    label: "Cards",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Section title", type: "text" },
      { key: "cards", label: "Cards", type: "list", max: 6, singular: "card",
        itemFields: [
          { key: "title", label: "Card title", type: "text", required: true },
          { key: "text", label: "Card text", type: "textarea" },
        ],
        newItem: () => ({ title: "New card", text: "" }) },
    ],
  },
  process: {
    label: "Process",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Section title", type: "text" },
      { key: "steps", label: "Steps", type: "list", max: 6, singular: "step",
        itemFields: [
          { key: "title", label: "Step title", type: "text", required: true },
          { key: "text", label: "Step detail", type: "textarea" },
        ],
        newItem: () => ({ title: "New step", text: "" }) },
    ],
  },
  timeline: {
    label: "Timeline",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Section title", type: "text" },
      { key: "milestones", label: "Milestones", type: "list", max: 6, singular: "milestone",
        itemFields: [
          { key: "when", label: "When", type: "text", placeholder: "e.g. Q1 2025" },
          { key: "title", label: "Title", type: "text", required: true },
          { key: "text", label: "Detail", type: "textarea" },
        ],
        newItem: () => ({ when: "2025", title: "Milestone", text: "" }) },
    ],
  },
  comparison: {
    label: "Comparison",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Section title", type: "text" },
      { key: "columns", label: "Columns", type: "columns" },
      { key: "verdict", label: "Verdict (footer bar)", type: "text" },
    ],
  },
  quote: {
    label: "Quote",
    fields: [
      { key: "quote", label: "Quote", type: "textarea", required: true, placeholder: "\u201cThe quote goes here.\u201d" },
      { key: "author", label: "Author", type: "text" },
      { key: "role", label: "Role / context", type: "text" },
    ],
  },
  metrics: {
    label: "Metrics",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Section title", type: "text" },
      { key: "metrics", label: "Metrics", type: "list", max: 8, singular: "metric",
        itemFields: [
          { key: "value", label: "Value", type: "text", required: true, placeholder: "42%" },
          { key: "label", label: "Label", type: "text", required: true, placeholder: "Growth" },
          { key: "sub", label: "Sub-note", type: "text" },
        ],
        newItem: () => ({ value: "99%", label: "Uptime", sub: "" }) },
    ],
  },
  image: {
    label: "Image",
    fields: [
      { key: "kicker", label: "Kicker", type: "text" },
      { key: "title", label: "Section title", type: "text" },
      { key: "image", label: "Image URL (optional — embedded if reachable)", type: "text", placeholder: "https://example.com/photo.jpg" },
      { key: "caption", label: "Caption", type: "text" },
    ],
  },
  closing: {
    label: "Closing",
    fields: [
      { key: "title", label: "Headline", type: "text", placeholder: "Thank you" },
      { key: "message", label: "Message", type: "text" },
      { key: "email", label: "Email", type: "text" },
      { key: "website", label: "Website", type: "text" },
    ],
  },
};

const DEFAULT_SLIDES = {
  hero:      () => ({ kicker: "PRESENTATION", title: deck.title || "Title", subtitle: "", presenter: "", date: "" }),
  statement: () => ({ kicker: "", title: "", caption: "" }),
  cards:     () => ({ kicker: "", title: "", cards: [{ title: "First card", text: "" }] }),
  process:   () => ({ kicker: "", title: "", steps: [{ title: "First step", text: "" }] }),
  timeline:  () => ({ kicker: "", title: "", milestones: [{ when: "", title: "", text: "" }] }),
  comparison:() => ({ kicker: "", title: "", columns: [{ heading: "", items: [""] }, { heading: "", items: [""] }], verdict: "" }),
  quote:     () => ({ quote: "", author: "", role: "" }),
  metrics:   () => ({ kicker: "", title: "", metrics: [{ value: "", label: "", sub: "" }] }),
  image:     () => ({ kicker: "", title: "", image: "", caption: "" }),
  closing:   () => ({ title: "Thank you", message: "", email: "", website: "" }),
};

/* =========================================================================
 * State
 * ========================================================================= */

let deck = createSampleDeck();
let activeTab = "builder";
let statusTimer = null;

const $ = (id) => document.getElementById(id);

function createSampleDeck() {
  return {
    title: "Product Launch Plan",
    slides: [
      {
        type: "hero",
        kicker: "PRESENTATION",
        title: "Product Launch Plan",
        subtitle: "How we ship v2.0 this quarter",
        presenter: "Product Team",
        date: "March 2025",
      },
      {
        type: "cards",
        kicker: "OVERVIEW",
        title: "Three pillars of the launch",
        cards: [
          { title: "Performance", text: "2x faster load times and a rebuilt rendering pipeline." },
          { title: "Design", text: "A refreshed interface with a modern component library." },
          { title: "Reliability", text: "99.9% uptime target with automated failover." },
        ],
      },
      {
        type: "metrics",
        kicker: "TRACTION",
        title: "Where we stand today",
        metrics: [
          { value: "42k", label: "Active users", sub: "+18% MoM" },
          { value: "4.8", label: "App store rating", sub: "" },
          { value: "$1.2M", label: "ARR", sub: "" },
        ],
      },
      {
        type: "closing",
        title: "Thank you",
        message: "Questions? Let's talk.",
        email: "team@example.com",
        website: "example.com",
      },
    ],
  };
}

/* =========================================================================
 * Builder rendering
 * ========================================================================= */

function renderSlides() {
  const list = $("slide-list");
  list.innerHTML = "";
  deck.slides.forEach((slide, index) => {
    list.appendChild(slideCard(slide, index));
  });
  $("deck-title").value = deck.title;
  renderPreview();
}

function slideCard(slide, index) {
  const def = SLIDE_TYPES[slide.type];
  const card = document.createElement("article");
  card.className = "slide-card";

  const head = document.createElement("header");
  head.className = "slide-card-head";
  head.innerHTML = `
    <span class="slide-index">${index + 1}</span>
    <span class="type-badge type-${slide.type}">${def.label}</span>
    <span class="slide-preview-title"></span>
    <div class="slide-tools">
      <button class="icon-btn" data-act="up" title="Move up" ${index === 0 ? "disabled" : ""}>&#8593;</button>
      <button class="icon-btn" data-act="down" title="Move down" ${index === deck.slides.length - 1 ? "disabled" : ""}>&#8595;</button>
      <button class="icon-btn danger" data-act="remove" title="Delete slide">&#10005;</button>
    </div>`;

  head.querySelector(".slide-tools").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn || btn.disabled) return;
    const act = btn.dataset.act;
    if (act === "up" && index > 0) {
      [deck.slides[index - 1], deck.slides[index]] = [deck.slides[index], deck.slides[index - 1]];
    } else if (act === "down" && index < deck.slides.length - 1) {
      [deck.slides[index + 1], deck.slides[index]] = [deck.slides[index], deck.slides[index + 1]];
    } else if (act === "remove") {
      deck.slides.splice(index, 1);
    }
    renderSlides();
  });

  card.appendChild(head);

  const body = document.createElement("div");
  body.className = "slide-card-body";
  def.fields.forEach((field) => body.appendChild(fieldControl(slide, field)));
  card.appendChild(body);
  return card;
}

function fieldControl(slide, field) {
  if (field.type === "list") return listControl(slide, field);
  if (field.type === "columns") return columnsControl(slide);
  return simpleControl(slide, field);
}

function simpleControl(obj, field) {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const label = document.createElement("label");
  label.textContent = field.label + (field.required ? " *" : "");
  wrap.appendChild(label);

  let input;
  if (field.type === "textarea") {
    input = document.createElement("textarea");
    input.rows = 2;
  } else {
    input = document.createElement("input");
    input.type = "text";
  }
  if (field.placeholder) input.placeholder = field.placeholder;
  input.value = obj[field.key] ?? "";
  input.addEventListener("input", () => {
    obj[field.key] = input.value;
    renderPreview();
  });
  wrap.appendChild(input);
  return wrap;
}

function listControl(slide, field) {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const label = document.createElement("label");
  label.textContent = field.label + " (" + (slide[field.key] || []).length + "/" + field.max + ")";
  wrap.appendChild(label);

  if (!Array.isArray(slide[field.key])) slide[field.key] = [];
  const items = slide[field.key];

  const box = document.createElement("div");
  box.className = "item-list";

  const rerender = () => {
    box.innerHTML = "";
    label.textContent = field.label + " (" + items.length + "/" + field.max + ")";
    items.forEach((item, i) => box.appendChild(listItem(item, i)));
    const add = document.createElement("button");
    add.className = "btn tiny ghost";
    add.type = "button";
    add.textContent = "+ Add " + (field.singular || "item");
    add.disabled = items.length >= field.max;
    add.addEventListener("click", () => {
      items.push(field.newItem());
      rerender();
      renderPreview();
    });
    box.appendChild(add);
  };

  const listItem = (item, i) => {
    const el = document.createElement("div");
    el.className = "list-item";
    const itemHead = document.createElement("div");
    itemHead.className = "list-item-head";
    itemHead.innerHTML = `<span class="list-item-index">${i + 1}</span>
      <button class="icon-btn danger" type="button" title="Remove">&#10005;</button>`;
    itemHead.querySelector("button").addEventListener("click", () => {
      items.splice(i, 1);
      rerender();
      renderPreview();
    });
    el.appendChild(itemHead);
    field.itemFields.forEach((f) => el.appendChild(simpleControl(item, f)));
    return el;
  };

  rerender();
  wrap.appendChild(box);
  return wrap;
}

function columnsControl(slide) {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const label = document.createElement("label");
  label.textContent = "Columns (one point per line)";
  wrap.appendChild(label);

  if (!Array.isArray(slide.columns) || slide.columns.length !== 2) {
    slide.columns = [{ heading: "", items: [""] }, { heading: "", items: [""] }];
  }

  const grid = document.createElement("div");
  grid.className = "columns-grid";

  slide.columns.forEach((col) => {
    const box = document.createElement("div");
    box.className = "column-box";

    const heading = document.createElement("input");
    heading.type = "text";
    heading.placeholder = "Column heading";
    heading.value = col.heading || "";
    heading.addEventListener("input", () => {
      col.heading = heading.value;
      renderPreview();
    });

    const items = document.createElement("textarea");
    items.rows = 4;
    items.placeholder = "One point per line";
    items.value = (col.items || []).join("\n");
    items.addEventListener("input", () => {
      col.items = items.value.split("\n");
      renderPreview();
    });

    box.append(heading, items);
    grid.appendChild(box);
  });

  wrap.appendChild(grid);
  return wrap;
}

/* =========================================================================
 * Preview / summary
 * ========================================================================= */

function previewTitle(slide) {
  return (
    slide.title || slide.quote || slide.message || slide.subtitle ||
    (Array.isArray(slide.cards) && slide.cards[0] && (slide.cards[0].title || "")) || ""
  ).toString().trim();
}

function renderPreview() {
  const n = deck.slides.length;
  $("preview-stats").textContent = n + (n === 1 ? " slide" : " slides");

  const ol = $("preview-list");
  ol.innerHTML = "";
  deck.slides.forEach((s) => {
    const li = document.createElement("li");
    const label = SLIDE_TYPES[s.type].label;
    const title = previewTitle(s) || label;
    li.innerHTML = `<span class="dot type-${s.type}"></span><span class="t"></span>`;
    li.querySelector(".t").textContent = title;
    ol.appendChild(li);
  });

  document.querySelectorAll(".slide-card").forEach((card, i) => {
    const el = card.querySelector(".slide-preview-title");
    if (el && deck.slides[i]) el.textContent = previewTitle(deck.slides[i]);
  });
}

/* =========================================================================
 * Spec building / validation (client-side mirror of the server rules)
 * ========================================================================= */

function buildSpec() {
  const spec = {
    title: (deck.title || "").trim() || "Untitled Presentation",
    slides: deck.slides.map((s) => {
      const slide = { type: s.type };
      const def = SLIDE_TYPES[s.type];
      def.fields.forEach((f) => {
        if (f.type === "list") {
          const items = (Array.isArray(s[f.key]) ? s[f.key] : [])
            .map((it) => cleanItem(it, f))
            .filter(Boolean);
          if (items.length) slide[f.key] = items;
        } else if (f.type === "columns") {
          slide.columns = (Array.isArray(s.columns) ? s.columns : []).map((c) => ({
            heading: (c.heading || "").trim(),
            items: (Array.isArray(c.items) ? c.items : [])
              .map((x) => String(x).trim()).filter(Boolean),
          }));
        } else {
          const v = typeof s[f.key] === "string" ? s[f.key].trim() : "";
          if (v) slide[f.key] = v;
        }
      });
      return slide;
    }),
  };
  return spec;
}

function cleanItem(item, field) {
  if (typeof item === "string") {
    const v = item.trim();
    return v || null;
  }
  const out = {};
  let any = false;
  field.itemFields.forEach((f) => {
    const v = typeof item?.[f.key] === "string" ? item[f.key].trim() : "";
    if (v) { out[f.key] = v; any = true; }
  });
  return any ? out : null;
}

function validateSpec(spec) {
  const errs = [];
  if (!spec || typeof spec !== "object" || Array.isArray(spec)) {
    return ["spec must be an object."];
  }
  if (!spec.title || !String(spec.title).trim()) errs.push("Presentation title is required.");
  if (!Array.isArray(spec.slides)) return ["slides must be an array."];
  if (spec.slides.length === 0) errs.push("Add at least one slide.");

  const needList = (s, key, what) =>
    Array.isArray(s[key]) && s[key].filter(Boolean).length > 0;

  spec.slides.forEach((s, i) => {
    const t = s && s.type;
    if (!SLIDE_TYPES[t]) {
      errs.push(`Slide ${i + 1}: unknown type "${t}".`);
      return;
    }
    const at = `Slide ${i + 1} (${t})`;
    if ((t === "hero" || t === "statement") && !(s.title || "").trim()) {
      errs.push(`${at}: title is required.`);
    }
    if (t === "cards" && !needList(s, "cards")) errs.push(`${at}: add at least one card with a title.`);
    if (t === "process" && !needList(s, "steps")) errs.push(`${at}: add at least one step with a title.`);
    if (t === "timeline" && !needList(s, "milestones")) errs.push(`${at}: add at least one milestone with a title.`);
    if (t === "metrics") {
      if (!needList(s, "metrics")) errs.push(`${at}: add at least one metric.`);
      else s.metrics.forEach((m, j) => {
        if (!m || !(m.value || "").toString().trim() || !(m.label || "").toString().trim()) {
          errs.push(`${at}: metric ${j + 1} needs both a value and a label.`);
        }
      });
    }
    if (t === "quote" && !(s.quote || "").trim()) errs.push(`${at}: quote text is required.`);
    if (t === "comparison") {
      if (!Array.isArray(s.columns) || s.columns.length !== 2) {
        errs.push(`${at}: exactly two columns are required.`);
      } else {
        s.columns.forEach((c, j) => {
          if (!c || !(c.heading || "").trim()) errs.push(`${at}: column ${j + 1} needs a heading.`);
        });
      }
    }
  });
  return errs;
}

/* =========================================================================
 * Tabs / JSON mode
 * ========================================================================= */

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach((b) => {
    const on = b.dataset.tab === tab;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === tab);
  });
  if (tab === "json") syncJson();
}

function syncJson() {
  $("json-editor").value = JSON.stringify(buildSpec(), null, 2);
}

function normalizeSlide(s) {
  const def = SLIDE_TYPES[s.type];
  const out = { type: s.type };
  def.fields.forEach((f) => {
    if (f.type === "list") {
      out[f.key] = (Array.isArray(s[f.key]) ? s[f.key] : []).map((it) =>
        typeof it === "string"
          ? it
          : Object.fromEntries(f.itemFields.map((x) => [x.key, typeof it?.[x.key] === "string" ? it[x.key] : ""]))
      );
    } else if (f.type === "columns") {
      let cols = Array.isArray(s.columns) ? s.columns : [];
      cols = cols.map((c) => ({
        heading: typeof c?.heading === "string" ? c.heading : "",
        items: Array.isArray(c?.items) ? c.items.map(String) : [],
      }));
      while (cols.length < 2) cols.push({ heading: "", items: [] });
      out.columns = cols.slice(0, 2);
    } else if (typeof s[f.key] === "string") {
      out[f.key] = s[f.key];
    }
  });
  return out;
}

/* =========================================================================
 * Generate + download
 * ========================================================================= */

function filenameFor(spec) {
  const base = (spec.title || "presentation")
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/[\s_-]+/g, "-")
    .slice(0, 60) || "presentation";
  return base + ".pptx";
}

function showStatus(kind, message) {
  const el = $("status");
  el.hidden = false;
  el.className = "status " + kind;
  el.textContent = message;
  if (statusTimer) clearTimeout(statusTimer);
  if (kind === "ok") statusTimer = setTimeout(() => { el.hidden = true; }, 5000);
}

function setLoading(on) {
  const btn = $("generate");
  btn.disabled = on;
  btn.textContent = on ? "Generating\u2026" : "Generate PowerPoint";
  btn.classList.toggle("loading", on);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

async function generate() {
  let spec;
  if (activeTab === "json") {
    try {
      spec = JSON.parse($("json-editor").value);
    } catch (e) {
      showStatus("error", "Invalid JSON: " + e.message);
      return;
    }
  } else {
    spec = buildSpec();
  }

  const errs = validateSpec(spec);
  if (errs.length) {
    showStatus("error", errs.join("  "));
    return;
  }

  setLoading(true);
  showStatus("info", "Generating your presentation\u2026");

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "spec", spec }),
    });

    if (!res.ok) {
      let msg = "Request failed (" + res.status + ")";
      try {
        const data = await res.json();
        msg = data.error || msg;
        if (Array.isArray(data.details) && data.details.length) {
          msg += " \u2014 " + data.details.join("; ");
        }
      } catch (_) { /* non-JSON error body */ }
      showStatus("error", msg);
      return;
    }

    const blob = await res.blob();
    downloadBlob(blob, filenameFor(spec));
    showStatus("ok", "PowerPoint generated \u2014 check your downloads.");
  } catch (e) {
    showStatus("error", "Network error: " + e.message);
  } finally {
    setLoading(false);
  }
}

/* =========================================================================
 * Wiring
 * ========================================================================= */

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

 $("deck-title").addEventListener("input", (e) => {
  deck.title = e.target.value;
});

const typeSelect = $("new-slide-type");
Object.entries(SLIDE_TYPES).forEach(([key, def]) => {
  const opt = document.createElement("option");
  opt.value = key;
  opt.textContent = def.label;
  typeSelect.appendChild(opt);
});

 $("add-slide").addEventListener("click", () => {
  const type = typeSelect.value;
  deck.slides.push(DEFAULT_SLIDES[type]());
  renderSlides();
  const cards = document.querySelectorAll(".slide-card");
  if (cards.length) cards[cards.length - 1].scrollIntoView({ behavior: "smooth", block: "nearest" });
});

 $("json-sync").addEventListener("click", () => {
  syncJson();
  showStatus("ok", "JSON synced from the builder.");
});

 $("json-apply").addEventListener("click", () => {
  let spec;
  try {
    spec = JSON.parse($("json-editor").value);
  } catch (e) {
    showStatus("error", "Invalid JSON: " + e.message);
    return;
  }
  const errs = validateSpec(spec);
  if (errs.length) {
    showStatus("error", errs.join("  "));
    return;
  }
  deck = {
    title: String(spec.title || "Untitled Presentation"),
    slides: spec.slides.map(normalizeSlide),
  };
  renderSlides();
  switchTab("builder");
  showStatus("ok", "JSON applied to the builder.");
});

 $("generate").addEventListener("click", generate);

renderSlides();