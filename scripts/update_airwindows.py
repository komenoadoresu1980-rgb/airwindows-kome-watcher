from __future__ import annotations

import email.utils
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
DATA.mkdir(parents=True, exist_ok=True)

FEED_URL = "https://www.airwindows.com/feed/"
AIRWINDOPEDIA_URL = "https://www.airwindows.com/wp-content/uploads/Airwindopedia.txt"
NTFY_BASE = os.getenv("NTFY_BASE", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()

UA = "Airwindows-Kome-Watcher/1.0 (+personal RSS watcher)"

CATEGORY_JA = {
    "Ambience": "アンビエンス／空間系",
    "Amp Sims": "アンプシミュレーション",
    "Bass": "低域処理",
    "Biquads": "フィルター／バイクアッド",
    "Brightness": "高域・ブライトネス調整",
    "Clipping": "クリッピング／ピーク処理",
    "Consoles": "コンソール／ミックスバス",
    "Distortion": "歪み",
    "Dithers": "ディザリング",
    "Dynamics": "ダイナミクス",
    "Effects": "エフェクト",
    "Filter": "フィルター／EQ",
    "Lo-Fi": "Lo-Fi／デジタル質感",
    "Noise": "ノイズ／テクスチャ",
    "Reverb": "リバーブ",
    "Saturation": "サチュレーション",
    "Stereo": "ステレオ処理",
    "Subtlety": "微細な質感調整",
    "Tape": "テープ系",
    "Tone Color": "音色・カラー付け",
    "Utility": "ユーティリティ",
    "XYZ Filters": "特殊フィルター",
    "Innovative": "実験的／独創的",
}

KEYWORD_HINTS = [
    (r"reverb|room|hall|plate|cathedral|chamber|space|verb", "空間・残響を扱うタイプ"),
    (r"bass|sub|low[- ]?end|kick", "低域の質感や量感に関係するタイプ"),
    (r"tape|flutter|wow|oxide", "テープ的な質感や揺れを扱うタイプ"),
    (r"clip|loud|peak|maxim", "ピークやラウドネスを扱うタイプ"),
    (r"satur|drive|distort|density|tube", "歪み・サチュレーション系"),
    (r"eq|filter|lowpass|highpass|bandpass", "EQ／フィルター系"),
    (r"stereo|width|wide|mid.?side|pan", "ステレオ像を扱うタイプ"),
    (r"console|buss|channel", "コンソール／バス処理系"),
    (r"guitar|amp|cab", "ギター／アンプ用途と関係するタイプ"),
    (r"lo.?fi|bit|rez|crush|glitch", "Lo-Fi／デジタル破壊系"),
]

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def fetch_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset, errors="replace")


def strip_html(text: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip()


def iso_date(raw: str) -> str:
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return raw


def make_id(guid: str, link: str, title: str) -> str:
    src = guid or link or title
    return hashlib.sha1(src.encode("utf-8", errors="ignore")).hexdigest()[:16]


def summarize_jp(title: str, body: str, categories: list[str]) -> str:
    cats = [CATEGORY_JA[c] for c in categories if c in CATEGORY_JA]
    low = f"{title} {body}".lower()
    hints = []
    for pattern, hint in KEYWORD_HINTS:
        if re.search(pattern, low) and hint not in hints:
            hints.append(hint)
        if len(hints) >= 2:
            break

    if cats:
        head = f"Airwindowsの{cats[0]}系の新しい公開物です。"
    else:
        head = "Airwindowsの新しい公開物です。"
    if hints:
        head += " " + "、".join(hints) + "として見ると分かりやすそうです。"
    head += " 詳細は公式説明で確認できます。"
    return head


@dataclass
class Release:
    id: str
    title: str
    link: str
    guid: str
    published_at: str
    categories: list[str]
    summary_ja: str
    excerpt_original: str


def parse_feed(xml_text: str) -> list[Release]:
    root = ET.fromstring(xml_text)
    out: list[Release] = []
    content_ns = "{http://purl.org/rss/1.0/modules/content/}encoded"
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        cats = [(c.text or "").strip() for c in item.findall("category") if (c.text or "").strip()]
        desc = item.findtext(content_ns) or item.findtext("description") or ""
        body = strip_html(desc)
        excerpt = body[:420] + ("…" if len(body) > 420 else "")
        out.append(Release(
            id=make_id(guid, link, title),
            title=title,
            link=link,
            guid=guid,
            published_at=iso_date(pub),
            categories=cats,
            summary_ja=summarize_jp(title, body, cats),
            excerpt_original=excerpt,
        ))
    return out


def parse_airwindopedia(text: str) -> list[dict]:
    category_by_plugin: dict[str, set[str]] = {}
    for line in text.splitlines():
        if ":" not in line or line.startswith("#"):
            continue
        cat, rest = line.split(":", 1)
        cat = cat.strip()
        if cat not in CATEGORY_JA:
            continue
        for name in rest.split(","):
            name = name.strip().strip(".")
            if not name or " " in name and name.lower() in {"hard vacuum"}:
                pass
            if name:
                category_by_plugin.setdefault(name, set()).add(cat)

    blocks = re.split(r"(?m)^############\s+", text)
    descriptions: dict[str, str] = {}
    for block in blocks[1:]:
        first, *rest = block.splitlines()
        first = first.strip()
        # Heading normally starts with plugin name, then explanation.
        name = first.split()[0].strip("#:,.") if first else ""
        # Prefer known names that match heading prefix.
        candidates = [p for p in category_by_plugin if first.lower().startswith(p.lower() + " ") or first.lower() == p.lower()]
        if candidates:
            name = max(candidates, key=len)
        body = strip_html(" ".join([first] + rest))
        if name:
            descriptions[name] = body[:1200]

    items = []
    for name in sorted(category_by_plugin, key=str.lower):
        cats = sorted(category_by_plugin[name])
        desc = descriptions.get(name, "")
        items.append({
            "id": hashlib.sha1(("catalog:" + name).encode()).hexdigest()[:16],
            "name": name,
            "categories": cats,
            "categories_ja": [CATEGORY_JA[c] for c in cats if c in CATEGORY_JA],
            "summary_ja": summarize_jp(name, desc, cats),
            "excerpt_original": desc[:420] + ("…" if len(desc) > 420 else ""),
            "search_url": "https://www.airwindows.com/?s=" + urllib.parse.quote(name),
        })
    return items


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ntfy_publish(release: Release) -> None:
    if not NTFY_TOPIC:
        return
    url = f"{NTFY_BASE}/{urllib.parse.quote(NTFY_TOPIC, safe='')}"
    payload = {
        "topic": NTFY_TOPIC,
        "title": "おいでたぞコメくん！うおおお",
        "message": f"{release.title}\n{release.summary_ja}",
        "tags": ["tada", "musical_note"],
        "priority": 3,
        "click": release.link,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            res.read()
    except Exception as exc:
        print(f"ntfy通知に失敗しました: {type(exc).__name__}", file=sys.stderr)


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    previous = read_json(DATA / "releases.json", {"items": []})
    known = {x.get("id") for x in previous.get("items", [])}

    feed_xml = fetch_text(FEED_URL)
    releases = parse_feed(feed_xml)
    new_items = [x for x in releases if x.id not in known]

    # On the very first run, populate silently so old posts do not flood the phone.
    first_run = not (DATA / "initialized.json").exists()
    if not first_run:
        for release in reversed(new_items):
            ntfy_publish(release)

    write_json(DATA / "releases.json", {
        "generated_at": now,
        "source": FEED_URL,
        "items": [asdict(x) for x in releases[:120]],
    })

    try:
        aw = fetch_text(AIRWINDOPEDIA_URL)
        catalog = parse_airwindopedia(aw)
        write_json(DATA / "catalog.json", {
            "generated_at": now,
            "source": AIRWINDOPEDIA_URL,
            "items": catalog,
        })
    except Exception as exc:
        print(f"Airwindopedia更新に失敗しました: {type(exc).__name__}", file=sys.stderr)
        if not (DATA / "catalog.json").exists():
            write_json(DATA / "catalog.json", {"generated_at": now, "source": AIRWINDOPEDIA_URL, "items": []})

    write_json(DATA / "status.json", {
        "last_checked_at": now,
        "new_count": 0 if first_run else len(new_items),
        "notification_enabled": bool(NTFY_TOPIC),
    })
    write_json(DATA / "initialized.json", {"initialized_at": now})
    print(f"取得 {len(releases)}件 / 新規 {0 if first_run else len(new_items)}件 / first_run={first_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
