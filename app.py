"""
PPT Maker — Flask application.

Serves the web UI and exposes:
    GET  /api/health    -> service health check
    POST /api/generate  -> validate a presentation spec and return a .pptx

There is no AI, no external services, and no API keys.
User input (JSON spec) -> validation -> python-pptx -> .pptx download.
"""

import io
import logging
import os
import re

from flask import Flask, jsonify, make_response, request, send_file, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from ppt_generator import generate_pptx

log = logging.getLogger("ppt-maker")
logging.basicConfig(level=logging.INFO)

SLIDE_TYPES = {
    "hero", "statement", "cards", "process", "timeline",
    "comparison", "quote", "metrics", "image", "closing",
}

MAX_SLIDES = 60
MAX_ITEMS = 8          # max items in cards/steps/milestones/metrics
MAX_TEXT = 4000        # max characters per text field
MAX_TITLE = 300        # max characters for the deck title

# Flask with static handling disabled — we serve our known frontend
# files through explicit routes only (no directory listing / source exposure).
app = Flask(__name__, static_folder=None)
# Render terminates TLS at its proxy; respect X-Forwarded-* headers.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB request cap
app.config["JSON_SORT_KEYS"] = False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _nonempty_str(value, limit=MAX_TEXT):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit


def _check_items(slide, key, required_keys, where, errors):
    """Validate a list field (cards / steps / milestones / metrics)."""
    items = slide.get(key)
    if not isinstance(items, list) or not (1 <= len(items) <= MAX_ITEMS):
        errors.append(
            f"{where}: '{key}' must be a list with 1-{MAX_ITEMS} items."
        )
        return
    for j, item in enumerate(items):
        pos = f"{where}.{key}[{j}]"
        if isinstance(item, str):
            if not _nonempty_str(item):
                errors.append(f"{pos}: must be a non-empty string (1-{MAX_TEXT} chars).")
        elif isinstance(item, dict):
            for req in required_keys:
                if not _nonempty_str(item.get(req)):
                    errors.append(f"{pos}: '{req}' is required (1-{MAX_TEXT} chars).")
            # Guard over-long optional text inside items (e.g. cards[*].text).
            for k, v in item.items():
                if isinstance(v, str) and len(v) > MAX_TEXT:
                    errors.append(f"{pos}.{k}: text is too long (max {MAX_TEXT} chars).")
                if v is not None and not isinstance(v, str) and k in set(required_keys) | {"text", "sub", "when", "title", "label", "value"}:
                    errors.append(f"{pos}.{k}: must be a string.")
        else:
            errors.append(f"{pos}: must be a string or an object.")


def _check_text_field(slide, key, where, errors, required=False):
    """Validate an optional (or required) plain-text field."""
    if key not in slide or slide.get(key) is None or slide.get(key) == "":
        if required:
            errors.append(f"{where}: '{key}' is required.")
        return
    v = slide.get(key)
    if not isinstance(v, str):
        errors.append(f"{where}: '{key}' must be a string.")
    elif required and not v.strip():
        errors.append(f"{where}: '{key}' is required.")
    elif len(v) > MAX_TEXT:
        errors.append(f"{where}.{key}: text is too long (max {MAX_TEXT} chars).")


def validate_spec(spec):
    """Return a list of human-readable validation errors (empty = valid)."""
    if not isinstance(spec, dict):
        return ["spec must be a JSON object."]

    errors = []

    if not _nonempty_str(spec.get("title"), MAX_TITLE):
        errors.append("spec: 'title' must be a non-empty string (1-300 chars).")

    slides = spec.get("slides")
    if not isinstance(slides, list):
        errors.append("spec: 'slides' must be an array.")
        return errors

    if len(slides) == 0:
        errors.append("spec: 'slides' must contain at least one slide.")
    if len(slides) > MAX_SLIDES:
        errors.append(f"spec: 'slides' cannot contain more than {MAX_SLIDES} slides.")

    for i, slide in enumerate(slides):
        where = f"slides[{i}]"
        if not isinstance(slide, dict):
            errors.append(f"{where}: must be an object.")
            continue

        # Guard against absurdly long text anywhere in the slide
        # (recurses one level into nested dicts/lists).
        def _scan(node, path):
            if isinstance(node, str):
                if len(node) > MAX_TEXT:
                    errors.append(f"{path}: text is too long (max {MAX_TEXT} chars).")
            elif isinstance(node, dict):
                for k, v in node.items():
                    _scan(v, f"{path}.{k}")
            elif isinstance(node, list):
                for j, v in enumerate(node):
                    _scan(v, f"{path}[{j}]")

        _scan(slide, where)

        stype = slide.get("type")
        if stype not in SLIDE_TYPES:
            errors.append(
                f"{where}.type: must be one of: {', '.join(sorted(SLIDE_TYPES))}."
            )
            continue

        where = f"slides[{i}] ({stype})"

        # Speaker notes are optional but bounded.
        notes = slide.get("notes")
        if notes is not None and notes != "":
            if not isinstance(notes, str):
                errors.append(f"{where}: 'notes' must be a string.")
            elif len(notes) > MAX_TEXT:
                errors.append(f"{where}.notes: text is too long (max {MAX_TEXT} chars).")

        for opt in ("kicker", "subtitle", "presenter", "date", "caption",
                    "title", "quote", "author", "role", "message", "email",
                    "website", "verdict", "image"):
            if opt in slide and slide.get(opt) is not None and not isinstance(slide.get(opt), str):
                errors.append(f"{where}: '{opt}' must be a string.")

        if stype in ("hero", "statement") and not _nonempty_str(slide.get("title")):
            errors.append(f"{where}: 'title' is required.")
        if stype == "cards":
            _check_items(slide, "cards", ("title",), where, errors)
        if stype == "process":
            _check_items(slide, "steps", ("title",), where, errors)
        if stype == "timeline":
            _check_items(slide, "milestones", ("title",), where, errors)
        if stype == "metrics":
            _check_items(slide, "metrics", ("value", "label"), where, errors)
        if stype == "quote" and not _nonempty_str(slide.get("quote")):
            errors.append(f"{where}: 'quote' is required.")
        if stype == "comparison":
            cols = slide.get("columns")
            if not isinstance(cols, list) or len(cols) != 2:
                errors.append(f"{where}: 'columns' must be a list of exactly 2 objects.")
            else:
                for j, col in enumerate(cols):
                    if not isinstance(col, dict) or not _nonempty_str(col.get("heading")):
                        errors.append(f"{where}.columns[{j}]: 'heading' is required.")
                    items = col.get("items")
                    if items is None:
                        continue
                    if not isinstance(items, list):
                        errors.append(f"{where}.columns[{j}]: 'items' must be an array of strings.")
                    else:
                        for k, it in enumerate(items):
                            if not isinstance(it, str):
                                errors.append(f"{where}.columns[{j}].items[{k}]: must be a string.")
                            elif len(it) > MAX_TEXT:
                                errors.append(f"{where}.columns[{j}].items[{k}]: text is too long (max {MAX_TEXT} chars).")
        if stype == "image":
            img = slide.get("image")
            if img not in (None, "") and not isinstance(img, str):
                errors.append(f"{where}: 'image' must be a URL string.")
        # 'closing' has no strictly required fields.

    return errors


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _error(status, message):
    return jsonify({"error": message}), status


def _safe_filename(title):
    base = re.sub(r"[^\w\s-]", "", str(title or "presentation")).strip()
    base = re.sub(r"[\s_-]+", "-", base).lower() or "presentation"
    return base[:60] + ".pptx"


@app.get("/")
def index():
    resp = make_response(send_from_directory(app.root_path, "index.html"))
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/index.html")
def index_html():
    resp = make_response(send_from_directory(app.root_path, "index.html"))
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/style.css")
def style_css():
    resp = make_response(
        send_from_directory(app.root_path, "style.css", mimetype="text/css")
    )
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@app.get("/app.js")
def app_js():
    resp = make_response(
        send_from_directory(app.root_path, "app.js", mimetype="application/javascript")
    )
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@app.get("/favicon.ico")
def favicon():
    return ("", 204)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "ppt-maker"})


@app.post("/api/generate")
def generate():
    payload = request.get_json(silent=True)
    if payload is None:
        return _error(400, "Request body must be valid JSON.")
    if not isinstance(payload, dict):
        return _error(400, "Request body must be a JSON object.")

    mode = payload.get("mode")
    if mode != "spec":
        return _error(400, f'Unsupported mode {mode!r}. Only mode "spec" is supported.')
    if "spec" not in payload:
        return _error(400, 'Missing "spec" object.')

    errors = validate_spec(payload["spec"])
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        pptx_bytes = generate_pptx(payload["spec"])
    except Exception:
        log.exception("PPTX generation failed")
        return _error(500, "Something went wrong while generating the presentation.")

    return send_file(
        io.BytesIO(pptx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=_safe_filename(payload["spec"].get("title")),
    )


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    return resp


@app.errorhandler(413)
def request_too_large(_e):
    return jsonify({"error": "Request body too large (limit is 2 MB)."}), 413


@app.errorhandler(404)
def not_found(_e):
    # API callers get JSON; browsers loading unknown pages get JSON too
    # (single-page app has no client-side routing to preserve).
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(_e):
    log.exception("Unhandled server error")
    return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Never enable the debugger in production; Render sets PORT for us.
    app.run(host="0.0.0.0", port=port, debug=False)