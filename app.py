from __future__ import annotations
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, jsonify, request, send_file
import yt_dlp
app = Flask(__name__)
# ============================================================
# A R V A N
# Video Downloader API
# ============================================================
MAX_URL_LENGTH = 2048
MAX_FILE_SIZE = 500 * 1024 * 1024
SUPPORTED_DOMAINS = (
    "snapchat.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
)
# ============================================================
# URL VALIDATION
# ============================================================
def validate_url(url: str) -> bool:
    if not url:
        return False
    if len(url) > MAX_URL_LENGTH:
        return False
    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE
    ):
        return False
    try:
        parsed = urlparse(url)
        hostname = (
            parsed.hostname or ""
        ).lower()
    except Exception:
        return False
    if not hostname:
        return False
    for domain in SUPPORTED_DOMAINS:
        if (
            hostname == domain
            or hostname.endswith(
                "." + domain
            )
        ):
            return True
    return False
# ============================================================
# SAFE FILENAME
# ============================================================
def safe_filename(
    title: str
) -> str:
    title = title or "arvan-video"
    title = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        title
    )
    title = title.strip()
    if not title:
        title = "arvan-video"
    return title[:100] + ".mp4"
# ============================================================
# DOWNLOAD API
# ============================================================
@app.post("/api/download")
def download_video():
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )
    url = str(
        data.get("url", "")
    ).strip()
    # Validate URL
    if not validate_url(url):
        return jsonify(
            error=(
                "ئەم لینکە پشتگیری ناکرێت. "
                "تکایە لینکێکی گشتی و دروست دابنێ."
            )
        ), 400
    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="arvan_"
        )
    )
    output_template = str(
        temp_dir /
        "%(title).80s-%(id)s.%(ext)s"
    )
    options = {
        # Best available MP4-compatible
        # public media.
        "format":
            "best[ext=mp4]/best",
        "outtmpl":
            output_template,
        "noplaylist":
            True,
        "quiet":
            True,
        "no_warnings":
            True,
        "restrictfilenames":
            True,
        "merge_output_format":
            "mp4",
        "max_filesize":
            MAX_FILE_SIZE,
    }
    try:
        with yt_dlp.YoutubeDL(
            options
        ) as ydl:
            info = ydl.extract_info(
                url,
                download=True
            )
            prepared =
                ydl.prepare_filename(
                    info
                )
        file_path =
            Path(prepared)
        # Some formats are merged
        # into MP4.
        if not file_path.exists():
            files = list(
                temp_dir.glob("*")
            )
            if not files:
                raise RuntimeError(
                    "هیچ فایلێک دروست نەکرا."
                )
            file_path = files[0]
        if not file_path.is_file():
            raise RuntimeError(
                "فایلی دابەزێنراو نەدۆزرایەوە."
            )
        filename =
            safe_filename(
                info.get("title")
            )
        response =
            send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype="video/mp4",
                max_age=0,
            )
        # Delete temporary directory
        # after the response closes.
        @response.call_on_close
        def cleanup():
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )
        return response
    except Exception as error:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )
        return jsonify(
            error=(
                "نەتوانرا ڤیدیۆکە "
                f"دابەزێنرێت: {error}"
            )
        ), 502
# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health")
def health():
    return jsonify(
        ok=True,
        app="A R V A N",
        service="Video Downloader"
    )
# ============================================================
# HOME
# ============================================================
@app.get("/")
def home():
    return send_file(
        "index.html"
    )
# ============================================================
# START SERVER
# ============================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
