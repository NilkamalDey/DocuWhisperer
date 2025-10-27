# General helpers for file validation, session state, and web URLs.
import os
import zipfile
import json
import re

DATA_FOLDER = "data"
WEB_URLS_FILE = "web_urls.json"

def save_web_urls(urls):
    with open(WEB_URLS_FILE, "w") as f:
        json.dump(urls, f)

def load_web_urls():
    if os.path.exists(WEB_URLS_FILE):
        try:
            with open(WEB_URLS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def is_valid_docx(path):
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            return any(f.filename.endswith('.xml') for f in zf.infolist())
    except Exception:
        return False

def is_valid_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False

def is_valid_url(url):
    return re.match(r"^https?://", url)