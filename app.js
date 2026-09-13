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
        newItem: () => ({ when: "Q3", title: "New milestone", text: "" }) },
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
        newItem: () => ({ value: "99%", label: "New metric", sub: "" }) },
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

/* FIX (was critical): every default slide must include its `type`.
 * Previously DEFAULT_SLIDES returned objects without `type`, so adding any
 * slide crashed renderSlides() on SLIDE_TYPES[undefined]. The hero default
 * also closed over `deck` before it was initialised. Both are fixed here,
 * and every default is immediately valid so "Generate" works right away. */
const DEFAULT_SLIDES = {
  hero: () => ({ type: "hero", kicker: "PRESENTATION", title: "New cover slide", subtitle: "", presenter: "", date: "", notes: "" }),
  statement: () => ({ type: "statement", kicker: "", title: "One bold idea per slide.", caption: "", notes: "" }),
  cards: () => ({ type: "cards", kicker: "", title: "Highlights", cards: [{ title: "First card", text: "" }], notes: "" }),
  process: () => ({ type: "process", kicker: "", title: "How it works", steps: [{ title: "First step", text: "" }], notes: "" }),
  timeline: () => ({ type: "timeline", kicker: "", title: "Roadmap", milestones: [{ when: "Q1", title: "New milestone", text: "" }], notes: "" }),
  comparison: () => ({ type: "comparison", kicker: "", title: "Comparison", columns: [{ heading: "Option A", items: ["First point"] }, { heading: "Option B", items: ["First point"] }], verdict: "", notes: "" }),
  quote: () => ({ type: "quote", quote: "Simplicity is the ultimate sophistication.", author: "", role: "", notes: "" }),
  metrics: () => ({ type: "metrics", kicker: "", title: "By the numbers", metrics: [{ value: "99%", label: "New metric", sub: "" }], notes: "" }),
  image: () => ({ type: "image", kicker: "", title: "Visual", image: "", caption: "", notes: "" }),
  closing: () => ({ type: "closing", title: "Thank you", message: "", email: "", website: "", notes: "" }),
};

/* =========================================================================
 * State
 * ========================================================================= */

let deck = loadDeck() || createSampleDeck();
let activeTab = "builder";
let statusTimer = null;
let saveTimer = null;

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
        notes: "",
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
        notes: "",
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
        notes: "",
      },
      {
        type: "closing",
        title: "Thank you",
        message: "Questions? Let's talk.",
        email: "team@example.com",
        website: "example.com",
        notes: "",
      },
    ],
  };
}

function loadDeck() {
  try {
    const raw = localStorage.getItem("ppt-maker-deck-v1");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.slides)) return null;
    // Drop unknown slide types from older/corrupt saves.
    parsed.slides = parsed.slides.filter((s) => s && SLIDE_TYPES[s.type]);
    if (typeof parsed.title !== "string") parsed.title = "";
    return parsed;
  } catch (_) {
    return null;
  }
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      localStorage.setItem("ppt-maker-deck-v1", JSON.stringify(deck));
    } catch (_) { /* storage full / private mode — non-fatal */ }
  }, 300);
}

/* =========================================================================
 * Builder rendering
 * ========================================================================= */

function renderSlides() {
  const list = $("slide-list");
  list.innerHTML = "";
  deck.slides.forEach((slide, index) => {
    if (!slide || !SLIDE_TYPES[slide.type]) return;
    list.appendChild(slideCard(slide, index));
  });
  $("deck-title").value = deck.title || "";
  const empty = $("empty-state");
  if (empty) empty.hidden = deck.slides.length !== 0;
  renderPreview();
  scheduleSave();
}

function slideCard(slide, index) {
  const def = SLIDE_TYPES[slide.type];
  const card = document.createElement("article");
  card.className = "slide-card";

  const head = document.createElement("header");
  head.className = "slide-card-head";

  const idx = document.createElement("span");
  idx.className = "slide-index";
  idx.textContent = String(index + 1);

  const badge = document.createElement("span");
  badge.className = "type-badge";
  badge.textContent = def.label;

  const preview = document.createElement("span");
  preview.className = "slide-preview-title";

  const tools = document.createElement("div");
  tools.className = "slide-tools";

  // Per-slide type switcher (keeps existing shared fields where sensible).
  const typeSel = document.createElement("select");
  typeSel.className = "type-select";
  typeSel.title = "Change slide type";
  typeSel.setAttribute("aria-label", "Slide " + (index + 1) + " type");
  Object.entries(SLIDE_TYPES).forEach(([key, d]) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = d.label;
    if (key === slide.type) opt.selected = true;
    typeSel.appendChild(opt);
  });
  typeSel.addEventListener("change", () => {
    const next = typeSel.value;
    if (next === slide.type || !SLIDE_TYPES[next]) return;
    const keepTitle = typeof slide.title === "string" ? slide.title : "";
    const keepNotes = typeof slide.notes === "string" ? slide.notes : "";
    const fresh = DEFAULT_SLIDES[next]();
    if (keepTitle && ("title" in fresh) && !fresh.title) fresh.title = keepTitle;
    if (keepNotes) fresh.notes = keepNotes;
    deck.slides[index] = fresh;
    renderSlides();
  });

  const mkBtn = (act, title, html, disabled) => {
    const b = document.createElement("button");
    b.className = "icon-btn" + (act === "remove" ? " danger" : "");
    b.type = "button";
    b.dataset.act = act;
    b.title = title;
    b.innerHTML = html;
    if (disabled) b.disabled = true;
    return b;
  };

  tools.append(
    typeSel,
    mkBtn("up", "Move up", "&#8593;", index === 0),
    mkBtn("down", "Move down", "&#8595;", index === deck.slides.length - 1),
    mkBtn("dup", "Duplicate slide", "&#10697;", false),
    mkBtn("remove", "Delete slide", "&#10005;", false),
  );

  tools.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn || btn.disabled) return;
    const act = btn.dataset.act;
    if (act === "up" && index > 0) {
      [deck.slides[index - 1], deck.slides[index]] = [deck.slides[index], deck.slides[index - 1]];
    } else if (act === "down" && index < deck.slides.length - 1) {
      [deck.slides[index + 1], deck.slides[index]] = [deck.slides[index], deck.slides[index + 1]];
    } else if (act === "dup") {
      deck.slides.splice(index + 1, 0, JSON.parse(JSON.stringify(deck.slides[index])));
    } else if (act === "remove") {
      deck.slides.splice(index, 1);
    }
    renderSlides();
  });

  head.append(idx, badge, preview, tools);
  card.appendChild(head);

  const body = document.createElement("div");
  body.className = "slide-card-body";
  def.fields.forEach((field) => body.appendChild(fieldControl(slide, field)));
  body.appendChild(notesControl(slide));
  card.appendChild(body);
  return card;
}

function fieldControl(slide, field) {
  if (field.type === "list") return listControl(slide, field);
  if (field.type === "columns") return columnsControl(slide);
  return simpleControl(slide, field);
}

function notesControl(slide) {
  const wrap = document.createElement("div");
  wrap.className = "field field-wide notes-field";
  const label = document.createElement("label");
  label.textContent = "Speaker notes (optional)";
  const input = document.createElement("textarea");
  input.rows = 1;
  input.placeholder = "Notes for the presenter — exported to PowerPoint notes.";
  input.value = typeof slide.notes === "string" ? slide.notes : "";
  input.addEventListener("input", () => {
    slide.notes = input.value;
    scheduleSave();
  });
  wrap.append(label, input);
  return wrap;
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
  if (field.key === "email") input.setAttribute("inputmode", "email");
  if (field.key === "website" || field.key === "image") input.setAttribute("inputmode", "url");
  input.value = obj[field.key] ?? "";
  input.addEventListener("input", () => {
    obj[field.key] = input.value;
    renderPreview();
    scheduleSave();
  });
  wrap.appendChild(input);
  return wrap;
}

function listControl(slide, field) {
  const wrap = document.createElement("div");
  wrap.className = "field field-wide";

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
      scheduleSave();
    });
    box.appendChild(add);
  };

  const listItem = (item, i) => {
    const el = document.createElement("div");
    el.className = "list-item";
    const itemHead = document.createElement("div");
    itemHead.className = "list-item-head";
    itemHead.innerHTML = `<span class="list-item-index">${field.singular || "Item"} ${i + 1}</span>
      <button class="icon-btn danger" type="button" title="Remove">&#10005;</button>`;
    itemHead.querySelector("button").addEventListener("click", () => {
      items.splice(i, 1);
      rerender();
      renderPreview();
      scheduleSave();
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
  wrap.className = "field field-wide";

  const label = document.createElement("label");
  label.textContent = "Columns (one point per line)";
  wrap.appendChild(label);

  if (!Array.isArray(slide.columns) || slide.columns.length !== 2) {
    slide.columns = [{ heading: "Option A", items: [""] }, { heading: "Option B", items: [""] }];
  }

  const grid = document.createElement("div");
  grid.className = "columns-grid";

  slide.columns.forEach((col) => {
    if (!col || typeof col !== "object") return;
    const box = document.createElement("div");
    box.className = "column-box";

    const heading = document.createElement("input");
    heading.type = "text";
    heading.placeholder = "Column heading";
    heading.setAttribute("aria-label", "Column heading");
    heading.value = col.heading || "";
    heading.addEventListener("input", () => {
      col.heading = heading.value;
      renderPreview();
      scheduleSave();
    });

    const items = document.createElement("textarea");
    items.rows = 4;
    items.placeholder = "One point per line";
    items.setAttribute("aria-label", "Column points, one per line");
    items.value = (col.items || []).join("\n");
    items.addEventListener("input", () => {
      col.items = items.value.split("\n");
      renderPreview();
      scheduleSave();
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
  if (!slide || typeof slide !== "object") return "";
  return (
    slide.title || slide.quote || slide.message || slide.subtitle ||
    (Array.isArray(slide.cards) && slide.cards[0] && (slide.cards[0].title || "")) || ""
  ).toString().trim();
}

function renderPreview() {
  const n = deck.slides.length;
  const stats = $("preview-stats");
  if (stats) stats.textContent = n + (n === 1 ? " slide" : " slides");

  const ol = $("preview-list");
  if (!ol) return;
  ol.innerHTML = "";
  deck.slides.forEach((s, i) => {
    const def = SLIDE_TYPES[s.type];
    if (!def) return;
    const li = document.createElement("li");
    const dot = document.createElement("span");
    dot.className = "dot type-" + s.type;
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = previewTitle(s) || def.label;
    t.title = t.textContent;
    const num = document.createElement("span");
    num.className = "n";
    num.textContent = String(i + 1).padStart(2, "0");
    li.append(dot, t, num);
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
    slides: deck.slides
      .filter((s) => s && SLIDE_TYPES[s.type])
      .map((s) => {
        const slide = { type: s.type };
        const def = SLIDE_TYPES[s.type];
        def.fields.forEach((f) => {
          if (f.type === "list") {
            const items = (Array.isArray(s[f.key]) ? s[f.key] : [])
              .map((it) => cleanItem(it, f))
              .filter(Boolean);
            if (items.length) slide[f.key] = items;
          } else if (f.type === "columns") {
            slide.columns = (Array.isArray(s.columns) ? s.columns : []).slice(0, 2).map((c) => ({
              heading: ((c && c.heading) || "").trim(),
              items: (c && Array.isArray(c.items) ? c.items : [])
                .map((x) => String(x).trim()).filter(Boolean),
            }));
            while (slide.columns.length < 2) slide.columns.push({ heading: "", items: [] });
          } else {
            const v = typeof s[f.key] === "string" ? s[f.key].trim() : "";
            if (v) slide[f.key] = v;
          }
        });
        const notes = typeof s.notes === "string" ? s.notes.trim() : "";
        if (notes) slide.notes = notes.slice(0, 4000);
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
  if (!item || typeof item !== "object") return null;
  const out = {};
  let any = false;
  field.itemFields.forEach((f) => {
    const v = typeof item[f.key] === "string" ? item[f.key].trim() : "";
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
  else if (String(spec.title).trim().length > 300) errs.push("Presentation title is too long (max 300 characters).");
  if (!Array.isArray(spec.slides)) return ["slides must be an array."];
  if (spec.slides.length === 0) errs.push("Add at least one slide.");
  if (spec.slides.length > 60) errs.push("Too many slides (max 60).");

  const needList = (s, key) =>
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
  const ed = $("json-editor");
  if (ed) ed.value = JSON.stringify(buildSpec(), null, 2);
}

function normalizeSlide(s) {
  if (!s || !SLIDE_TYPES[s.type]) return null;
  const def = SLIDE_TYPES[s.type];
  const out = { type: s.type };
  def.fields.forEach((f) => {
    if (f.type === "list") {
      const arr = Array.isArray(s[f.key]) ? s[f.key] : [];
      out[f.key] = arr.map((it) =>
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
    } else if (typeof s[f.key] === "number") {
      out[f.key] = String(s[f.key]);
    }
  });
  if (typeof s.notes === "string" && s.notes.trim()) out.notes = s.notes;
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
  if (!el) return;
  el.hidden = false;
  el.className = "status " + kind;
  el.textContent = message;
  if (statusTimer) clearTimeout(statusTimer);
  if (kind === "ok") statusTimer = setTimeout(() => { el.hidden = true; }, 6000);
}

function setLoading(on) {
  ["generate", "top-export"].forEach((id) => {
    const btn = $(id);
    if (!btn) return;
    if (id === "generate") {
      btn.disabled = on;
      btn.textContent = on ? "Generating\u2026" : "Generate PowerPoint";
      btn.classList.toggle("loading", on);
    } else {
      btn.disabled = on;
    }
  });
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

async function checkHealth() {
  const pill = $("api-status");
  if (!pill) return;
  const label = pill.querySelector(".api-label");
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 6000);
    const res = await fetch("/api/health", { signal: ctrl.signal });
    clearTimeout(t);
    if (!res.ok) throw new Error("HTTP " + res.status);
    pill.classList.add("ok");
    pill.classList.remove("bad");
    if (label) label.textContent = "API online";
  } catch (_) {
    pill.classList.add("bad");
    pill.classList.remove("ok");
    if (label) label.textContent = "API unreachable";
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
  renderPreview();
  scheduleSave();
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
  if (!SLIDE_TYPES[type] || !DEFAULT_SLIDES[type]) return;
  deck.slides.push(DEFAULT_SLIDES[type]());
  renderSlides();
  const cards = document.querySelectorAll(".slide-card");
  if (cards.length) cards[cards.length - 1].scrollIntoView({ behavior: "smooth", block: "nearest" });
});

const resetBtn = $("reset-sample");
if (resetBtn) {
  resetBtn.addEventListener("click", () => {
    deck = createSampleDeck();
    renderSlides();
    showStatus("ok", "Sample deck restored.");
  });
}

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
    slides: spec.slides.map(normalizeSlide).filter(Boolean),
  };
  renderSlides();
  switchTab("builder");
  showStatus("ok", "JSON applied to the builder.");
});

$("generate").addEventListener("click", generate);

const topExport = $("top-export");
if (topExport) topExport.addEventListener("click", generate);

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    generate();
  }
});

renderSlides();
checkHealth();
