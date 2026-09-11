# 🎯 PPT Maker
Turn structured presentation content into a real, fully editable PowerPoint (.pptx) file — right in your browser.

PPT Maker is deliberately simple: there is no AI, no LLM, no API keys, no accounts.You describe your deck (title + slides + content), and a Python renderer built on python-pptx lays it out with a clean, modern design system. Every element in the generated file is a genuine PowerPoint text box or shape, so you can keep editing it in PowerPoint, Keynote, or Google Slides.

Browser → Flask backend → presentation spec (JSON) → validation → PPT renderer → python-pptx → .pptx download
* ✨ Features
* 🧱 Visual builder UI — deck title, slide list, per-slide content editing, reorder and delete slides
* ⌨️ Advanced JSON mode — paste/edit the raw presentation specification
* 👀 Live preview/summary of the deck outline
* 🖼️ 10 polished slide layouts — hero, statement, cards, process, timeline, comparison, quote, metrics, image, closing
* 🗒️ Speaker notes per slide (notes field)
* 📐 16:9 slides — consistent theme, footers with page numbers
* 🚀 Works locally (python app.py) and deploys to Render
* 📦 Installation
* Requires Python 3.12+.

git clone <your-repo-url> ppt-makercd ppt-makerpython -m venv .venvsource .venv/bin/activate      # Windows: .venv\Scripts\activatepip install -r requirements.txt
🖥️ Local Development & Running the Server
python app.py
Then open http://localhost:5000.

For production-style serving locally:

gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120

## 🧭 Using the Web UI
**Builder tab — enter a presentation title, add slides, pick a slide type, and fill in the content fields. Use ↑ / ↓ to reorder slides and ✕ to delete them.**

**Advanced JSON tab — the raw spec is synced from the builder automatically. Edit it directly, or paste your own JSON and click Apply to builder.**

Click Generate PowerPoint — the .pptx downloads to your machine. Validation errors (if any) are shown inline before the request is sent.
🔌 API Usage
GET /api/health
curl http://localhost:5000/api/health# {"service":"ppt-maker","status":"ok"}
POST /api/generate
Send JSON with mode: "spec" — the only supported mode — and a spec object:

curl -X POST http://localhost:5000/api/generate \  -H "Content-Type: application/json" \  -d @sample.json \  --output my-deck.pptx
Request body:

{  "mode": "spec",  "spec": {    "title": "Example Presentation",    "slides": [      { "type": "hero", "title": "Hello World", "subtitle": "My first presentation" }    ]  }}
Responses:

## Status	Meaning
200	The generated .pptx file (attachment download)
400	Invalid JSON body, unsupported mode, or spec validation failure — {"error": "...", "details": [...]}
413	Request body larger than 2 MB
500	Unexpected rendering error
📋 JSON Specification Format
Top level
Field	Type	Required	Notes
title	string	✅ yes	Deck title (also the filename)
slides	array	✅ yes	1–60 slide objects

**💡 Every slide may also include a notes (string) field — it becomes PowerPoint speaker notes.**

## 🖼️ hero — cover slide
{  "type": "hero",  "title": "Product Launch Plan",  "subtitle": "How we ship v2.0 this quarter",  "presenter": "Product Team",  "date": "March 2025",  "kicker": "PRESENTATION"}

💬 statement — one big idea
{  "type": "statement",  "title": "Simple beats clever.",  "caption": "Our design philosophy since day one",  "kicker": "PHILOSOPHY"}

🃏 cards — a grid of 1–6 cards
{  "type": "cards",  "title": "Three pillars of the launch",  "cards": [    { "title": "Performance", "text": "2x faster load times." },    { "title": "Design", "text": "A refreshed interface." },    { "title": "Reliability", "text": "99.9% uptime target." }  ]}

⚙️ process — numbered steps (1–6)
{  "type": "process",  "title": "How it works",  "steps": [    { "title": "Collect", "text": "Gather structured content." },    { "title": "Validate", "text": "Check the specification." },    { "title": "Render", "text": "Lay out the .pptx." }  ]}

📅 timeline — milestones (1–6)
{  "type": "timeline",  "title": "Roadmap",  "milestones": [    { "when": "Q1", "title": "Beta", "text": "Internal testing." },    { "when": "Q2", "title": "Launch", "text": "Public release." }  ]}

⚖️ comparison — two-column comparison
{  "type": "comparison",  "title": "Before vs. after",  "columns": [    { "heading": "Before", "items": ["Manual slide decks", "Inconsistent styling"] },    { "heading": "After", "items": ["Structured spec", "Consistent design system"] }  ],  "verdict": "Structured content wins."}

❝ quote
{  "type": "quote",  "quote": "Simplicity is the ultimate sophistication.",  "author": "Leonardo da Vinci",  "role": "Attributed"}

📊 metrics — big numbers (1–8)
{  "type": "metrics",  "title": "Where we stand today",  "metrics": [    { "value": "42k", "label": "Active users", "sub": "+18% MoM" },    { "value": "4.8", "label": "App store rating" },    { "value": "$1.2M", "label": "ARR" }  ]}

🖼️ image — image or styled placeholder
{  "type": "image",  "title": "The new dashboard",  "image": "https://example.com/dashboard.png",  "caption": "Analytics view, March 2025"}
ℹ️ If image is a reachable http(s) URL (≤ 6 MB), it is downloaded once and embedded. Otherwise a clean dashed placeholder frame is rendered — just drop your picture into it in PowerPoint via Insert → Pictures.

🏁 closing — final slide
{  "type": "closing",  "title": "Thank you",  "message": "Questions? Let's talk.",  "email": "team@example.com",  "website": "example.com"}

📄 Complete Sample Spec
{  "title": "Example Presentation",  "slides": [    {      "type": "hero",      "kicker": "PRESENTATION",      "title": "Example Presentation",      "subtitle": "Built from structured content",      "presenter": "You",      "date": "2025"    },    {      "type": "statement",      "kicker": "THE POINT",      "title": "Structured content in, polished decks out.",      "caption": "No AI. No magic. Just good layout."    },    {      "type": "cards",      "title": "What you get",      "cards": [        { "title": "Editable", "text": "Real text boxes, not screenshots." },        { "title": "Consistent", "text": "One design system across all slides." },        { "title": "Fast", "text": "Generated in milliseconds." }      ]    },    {      "type": "process",      "title": "How it works",      "steps": [        { "title": "Describe", "text": "Write your content." },        { "title": "Validate", "text": "The spec is checked." },        { "title": "Download", "text": "Get your .pptx." }      ]    },    {      "type": "timeline",      "title": "Plan",      "milestones": [        { "when": "Q1", "title": "Draft", "text": "Outline the story." },        { "when": "Q2", "title": "Review", "text": "Share with the team." },        { "when": "Q3", "title": "Present", "text": "Deliver the deck." }      ]    },    {      "type": "comparison",      "title": "Why not manual slides?",      "columns": [        { "heading": "Manual", "items": ["Hours of fiddling", "Drifting styles"] },        { "heading": "PPT Maker", "items": ["Minutes to a deck", "Locked-in design"] }      ],      "verdict": "Spend time on content, not on alignment."    },    {      "type": "quote",      "quote": "Content is king, but layout is the crown.",      "author": "Anonymous designer"    },    {      "type": "metrics",      "title": "By the numbers",      "metrics": [        { "value": "10", "label": "Slide types" },        { "value": "0", "label": "API keys needed" },        { "value": "1", "label": "JSON spec" }      ]    },    {      "type": "image",      "title": "A picture is worth a slide",      "caption": "Add any image URL — or replace the placeholder later."    },    {      "type": "closing",      "title": "Thank you",      "message": "Now go build your own deck.",      "email": "you@example.com",      "website": "example.com"    }  ]}

## ✅ Validation Rules
* spec must be an object; title a non-empty string (≤ 300 chars)
* slides a non-empty array (≤ 60 slides)
* Every slide must have a valid type
* Required fields per type:
* hero / statement → title
* cards → cards[*].title
* process → steps[*].title
* timeline → milestones[*].title
* metrics → metrics[*].value + metrics[*].label
* quote → quote
* comparison → exactly 2 columns, each with heading
* Text fields capped at 4,000 characters; request bodies at 2 MB

## 🔒 Security Notes

❌ No user code is ever executed — only data-driven rendering
✅ Malformed JSON is handled gracefully (400 with a clear message)
✅ The Flask app serves only the three known frontend files — no directory listing
✅ Temporary artifacts stay in memory (BytesIO) — no files written to disk

## ☁️ Render Deployment
Push this repository to GitHub or GitLab.
In Render, choose New → Web Service and import the repo(or use the provided render.yaml via New → Blueprint).
Render auto-detects Python. Otherwise set:
Build command: pip install -r requirements.txt
Start command: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
Deploy — the health check is available at /api/health.

## 📁 Project Layout
ppt-maker/
│
├── app.py
├── ppt_generator.py
├── layouts.py
├── index.html
├── app.js
├── style.css
├── requirements.txt
├── render.yaml
├── README.md
└── .gitignore

## License

**The software is a MIT licensed software, hence you are free to use this software if you want.**

Thanks for Reading and
**Happy Coding !!!**

Project made and Mantained by:
DG

[Discord Link](https://discord.gg/J6pXBg7XnY)