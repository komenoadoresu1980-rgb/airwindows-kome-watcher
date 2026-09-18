"""Translate official Airwindows descriptions with a local, free Argos model."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from update_airwindows import DATA, read_json, write_json


def translate_text(text: str, translator) -> str:
    """Keep paragraphs readable and avoid sending huge blocks to the model."""
    translated = []
    for paragraph in re.split(r"\n\s*\n", text):
        if not paragraph.strip():
            continue
        chunks = []
        rest = paragraph.strip()
        while len(rest) > 1200:
            cut = rest.rfind(" ", 0, 1200)
            if cut < 300:
                cut = 1200
            chunks.append(rest[:cut].strip())
            rest = rest[cut:].strip()
        if rest:
            chunks.append(rest)
        translated.append(" ".join(translator(chunk).strip() for chunk in chunks))
    return "\n\n".join(translated)


def pending_items(documents: list[tuple[Path, dict]]):
    for path, document in documents:
        for item in document.get("items", []):
            if item.get("description_original") and not item.get("description_ja"):
                yield path, document, item


def get_translator():
    import argostranslate.package
    import argostranslate.translate

    installed = argostranslate.package.get_installed_packages()
    if not any(p.from_code == "en" and p.to_code == "ja" for p in installed):
        argostranslate.package.update_package_index()
        model = next((p for p in argostranslate.package.get_available_packages()
                      if p.from_code == "en" and p.to_code == "ja"), None)
        if model is None:
            raise RuntimeError("英語→日本語のArgos翻訳モデルが見つかりません")
        argostranslate.package.install_from_path(model.download())
    return lambda text: argostranslate.translate.translate(text, "en", "ja")


def run(limit: int, translator=None) -> int:
    paths = [DATA / "releases.json", DATA / "catalog.json"]
    documents = [(path, read_json(path, {"items": []})) for path in paths]
    pending = list(pending_items(documents))
    if not pending:
        print("翻訳待ちの説明はありません")
        return 0
    translator = translator or get_translator()
    touched = set()
    completed = 0
    for path, document, item in pending[:limit]:
        try:
            translation = translate_text(item["description_original"], translator)
            if not translation:
                continue
            item["description_ja"] = translation
            touched.add(path)
            completed += 1
        except Exception as exc:
            print(f"翻訳を保留: {item.get('name') or item.get('title')} ({type(exc).__name__})")
    for path, document in documents:
        if path in touched:
            write_json(path, document)
    print(f"今回翻訳 {completed}件 / 残り {max(0, len(pending) - completed)}件")
    return completed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    run(args.limit)
