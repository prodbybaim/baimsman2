import re
import hashlib
from datetime import datetime, timezone


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:200]


def text_snippet(md: str, length=200):
    txt = re.sub(r"```.*?```", "", md, flags=re.S)
    txt = re.sub(r"`.+?`", "", txt)
    txt = re.sub(r"!\[.*?\]\(.*?\)", "", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", txt)
    txt = re.sub(r"[#*>\-]{1,3}", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:length] + ("…" if len(txt) > length else "")


fm_regex = r"^---\s*\n(.*?)\n---\s*\n?"


def parseMD(raw):
    import re
    m = re.match(fm_regex, raw, flags=re.S)
    if not m:
        return {}, raw
    fm_text = m.group(1)
    try:
        import yaml
        meta = yaml.safe_load(fm_text) or {}
    except Exception:
        meta = {}
        for line in fm_text.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"\'')
    body = raw[m.end():]
    return meta, body


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()