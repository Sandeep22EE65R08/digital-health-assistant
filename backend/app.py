"""Flask backend for the AI Digital Health Assistant.

Endpoints:
    GET  /api/health      -> { ok, mode }
    POST /api/analyze     -> { reply, mode }  (structured intake)
    POST /api/chat        -> { reply, mode }  (free-form follow-up)

If AI_API_KEY is set in the environment (or .env), requests are forwarded to an
OpenAI-compatible chat-completions endpoint. Otherwise the safe rule-based
responder in fallback.py is used.
"""
from __future__ import annotations

import base64
import html
import io
import os
import time
from pathlib import Path

import pymupdf
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from fallback import analyze as fallback_analyze
from prompt import (
    REPORT_ANALYSIS_INSTRUCTION,
    SYSTEM_PROMPT,
    build_report_message,
    build_user_message,
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Load .env if present (local dev); on hosted platforms env vars come from the dashboard.
load_dotenv(BASE_DIR / ".env")

AI_API_BASE = os.getenv("AI_API_BASE", "https://api.openai.com/v1").rstrip("/")
AI_API_MODEL = os.getenv("AI_API_MODEL", "gpt-4o-mini")
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()

app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _mode() -> str:
    return "live" if AI_API_KEY else "demo"


def _ai_payload(reply: str) -> dict:
    """Wrap a raw AI reply (markdown) for the frontend to render."""
    return {"reply": reply, "format": "markdown", "mode": "live"}


def _fallback_payload(html_reply: str, error_note: str | None = None,
                      mode: str = "demo") -> dict:
    payload = {"reply": html_reply, "format": "html", "mode": mode}
    if error_note:
        payload["error_note"] = error_note
    return payload


def _call_ai(messages: list[dict], *, retries: int = 2) -> str:
    """POST to an OpenAI-compatible chat-completions endpoint.

    Retries once on 429/503 (transient model overload / rate limit) with a
    short backoff before giving up.
    """
    url = f"{AI_API_BASE}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
    }
    payload = {"model": AI_API_MODEL, "temperature": 0.4, "messages": messages}
    last_err: str | None = None
    for attempt in range(retries + 1):
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.ok:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        last_err = f"AI service error {resp.status_code}: {resp.text[:300]}"
        if resp.status_code in (429, 503) and attempt < retries:
            time.sleep(2 * (attempt + 1))
            continue
        break
    raise RuntimeError(last_err or "AI service error: unknown")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "mode": _mode(), "model": AI_API_MODEL if AI_API_KEY else None})


@app.post("/api/analyze")
def analyze_endpoint():
    intake = request.get_json(silent=True) or {}
    if not intake.get("symptoms") and not intake.get("reportText"):
        return jsonify({"error": "Please provide symptoms or a medical report."}), 400

    if AI_API_KEY:
        try:
            user_msg = build_user_message(intake)
            reply = _call_ai([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ])
            return jsonify(_ai_payload(reply))
        except Exception as exc:
            return jsonify(_fallback_payload(
                fallback_analyze(intake),
                error_note=str(exc),
                mode="demo-fallback",
            ))

    return jsonify(_fallback_payload(fallback_analyze(intake)))


MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PDF_TEXT_CHARS = 18000
MAX_VISION_PAGES = 6           # cap pages sent to vision (cost / latency)
VISION_RENDER_DPI = 150        # render resolution for scanned pages
ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
IMAGE_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Return text layer from a PDF. Empty string if none / scanned."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except PdfReadError as exc:
        raise ValueError(f"Could not read PDF: {exc}")
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("PDF is password-protected. Please upload an unlocked file.")
    parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(text)
    full = "\n".join(parts).strip()
    if len(full) > MAX_PDF_TEXT_CHARS:
        full = full[:MAX_PDF_TEXT_CHARS] + "\n\n[...truncated for length...]"
    return full


def _render_pdf_pages_to_png(pdf_bytes: bytes, max_pages: int = MAX_VISION_PAGES) -> list[bytes]:
    """Render up to `max_pages` PDF pages to PNG bytes using PyMuPDF."""
    images: list[bytes] = []
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF for vision: {exc}")
    try:
        zoom = VISION_RENDER_DPI / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    if not images:
        raise ValueError("PDF has no pages to render.")
    return images


def _vision_analyze_pdf(pdf_bytes: bytes, language: str) -> str:
    """Send PDF pages as images to the AI model and get a markdown report."""
    pngs = _render_pdf_pages_to_png(pdf_bytes)
    return _vision_analyze_images(
        [(p, "image/png") for p in pngs],
        language,
        source_label="PDF",
    )


def _vision_analyze_images(
    images: list[tuple[bytes, str]],
    language: str,
    source_label: str = "image",
) -> str:
    """Send one or more report images (bytes, mime) to the AI model."""
    prelude = (
        f"The user has uploaded a medical/lab report as a {source_label} "
        f"({len(images)} image(s) attached). "
        "Read EVERY value, parameter, reference range and note you can see in "
        "the image(s) — including any handwritten or printed reference ranges.\n"
        f"Respond in: {language}\n\n"
    )
    content: list[dict] = [
        {"type": "text", "text": prelude + REPORT_ANALYSIS_INSTRUCTION}
    ]
    for img_bytes, mime in images:
        b64 = base64.b64encode(img_bytes).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })
    return _call_ai([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ])


@app.post("/api/analyze-report")
def analyze_report_endpoint():
    upload = request.files.get("report")
    if upload is None or not upload.filename:
        return jsonify({"error": "Please attach a PDF or image file."}), 400
    fname_lower = upload.filename.lower()
    is_pdf = fname_lower.endswith(".pdf")
    is_image = fname_lower.endswith(ALLOWED_IMAGE_EXTS)
    if not (is_pdf or is_image):
        return jsonify({"error": "Only PDF or image files (JPG, PNG, WebP) are supported."}), 400

    file_bytes = upload.stream.read()
    if not file_bytes:
        return jsonify({"error": "Uploaded file is empty."}), 400
    if len(file_bytes) > MAX_PDF_BYTES:
        return jsonify({"error": "File is too large. Maximum size is 10 MB."}), 400

    language = (request.form.get("language") or "English").strip()

    # Image branch: skip PDF text extraction, go straight to vision.
    if is_image:
        if not AI_API_KEY:
            return jsonify({
                "error": "Image analysis requires Live AI mode. "
                         "Enable an AI key or upload a text-based PDF."
            }), 400
        ext = "." + fname_lower.rsplit(".", 1)[-1]
        mime = IMAGE_MIME_BY_EXT.get(ext, "image/jpeg")
        try:
            reply = _vision_analyze_images(
                [(file_bytes, mime)], language, source_label="image"
            )
            payload = _ai_payload(reply)
            payload["extracted_chars"] = 0
            payload["source"] = "vision-image"
            return jsonify(payload)
        except Exception as exc:
            intake = {"symptoms": "", "language": language, "reportText": ""}
            payload = _fallback_payload(
                fallback_analyze(intake),
                error_note=f"Image analysis failed: {exc}",
                mode="demo-fallback",
            )
            payload["source"] = "vision-failed"
            return jsonify(payload)

    pdf_bytes = file_bytes
    try:
        report_text = _extract_pdf_text(pdf_bytes)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    has_text = bool(report_text)
    used_vision = False

    # Path A: text layer present -> use the dedicated report prompt.
    if has_text and AI_API_KEY:
        intake = {"symptoms": "", "language": language, "reportText": report_text}
        try:
            user_msg = build_report_message(report_text, language=language)
            reply = _call_ai([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ])
            payload = _ai_payload(reply)
            payload["extracted_chars"] = len(report_text)
            payload["source"] = "text"
            return jsonify(payload)
        except Exception as exc:
            payload = _fallback_payload(
                fallback_analyze(intake),
                error_note=str(exc),
                mode="demo-fallback",
            )
            payload["extracted_chars"] = len(report_text)
            payload["source"] = "text"
            return jsonify(payload)

    # Path B: no text layer (scanned/image PDF) -> use vision.
    if AI_API_KEY:
        try:
            reply = _vision_analyze_pdf(pdf_bytes, language)
            used_vision = True
            payload = _ai_payload(reply)
            payload["extracted_chars"] = 0
            payload["source"] = "vision"
            return jsonify(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            intake = {"symptoms": "", "language": language, "reportText": ""}
            payload = _fallback_payload(
                fallback_analyze(intake),
                error_note=f"Vision analysis failed: {exc}",
                mode="demo-fallback",
            )
            payload["source"] = "vision-failed"
            return jsonify(payload)

    # Demo mode (no key) with a scanned PDF: we cannot read images without AI.
    if not has_text:
        return jsonify({
            "error": "This PDF is a scanned image and Live AI mode is off. "
                     "Enable an AI key or upload a text-based PDF."
        }), 400

    intake = {"symptoms": "", "language": language, "reportText": report_text}
    payload = _fallback_payload(fallback_analyze(intake))
    payload["extracted_chars"] = len(report_text)
    payload["source"] = "text"
    return jsonify(payload)


@app.post("/api/chat")
def chat_endpoint():
    body = request.get_json(silent=True) or {}
    intake = body.get("intake") or {}
    question = (body.get("question") or "").strip()
    history = body.get("history") or []  # list of {role, content}
    if not question:
        return jsonify({"error": "Question is required."}), 400

    if AI_API_KEY:
        try:
            user_msg = build_user_message(intake, follow_up=question)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(
                m for m in history if m.get("role") in ("user", "assistant") and m.get("content")
            )
            messages.append({"role": "user", "content": user_msg})
            reply = _call_ai(messages)
            return jsonify(_ai_payload(reply))
        except Exception as exc:
            merged = dict(intake)
            merged["symptoms"] = (merged.get("symptoms") or "") + "\n" + question
            return jsonify(_fallback_payload(
                fallback_analyze(merged),
                error_note=str(exc),
                mode="demo-fallback",
            ))

    merged = dict(intake)
    merged["symptoms"] = (merged.get("symptoms") or "") + "\n" + question
    return jsonify(_fallback_payload(fallback_analyze(merged)))


# --- Serve the frontend (optional convenience) ---
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path: str):
    target = FRONTEND_DIR / path
    if target.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    # In production (Render/Heroku) gunicorn imports `app` directly; this block
    # is only used for local `python app.py`. When PORT is set by a platform we
    # bind 0.0.0.0 so the container is reachable.
    is_dev = FLASK_ENV == "development"
    bind_host = HOST if is_dev else "0.0.0.0"
    print(f"[Digital Health Assistant] mode={_mode()}  http://{bind_host}:{PORT}")
    app.run(host=bind_host, port=PORT, debug=is_dev)
