#!/usr/bin/env python3
"""
build_cyber_audio.py — pre-generate Castilian Spanish audio for the new
NEÓN flashcard app (cyber/index.html), using the same es-ES-ElviraNeural
voice as the Cartas app so the voice is consistent across every level
(A1 → C2) and every category (nouns / verbs / phrases).

Output goes to cartas/audio/words/<slug>.mp3 — the same folder the cyber
app loads from. Existing files are skipped, so this is idempotent.

Usage:
    pip install --user edge-tts
    python3 tools/build_cyber_audio.py
    python3 tools/build_cyber_audio.py --force           # regenerate all
    python3 tools/build_cyber_audio.py --kind phrases    # only phrases
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("Missing dependency. Install with: pip install --user edge-tts", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "audio" / "words"

VOICE = "es-ES-ElviraNeural"
RATE = "-10%"

LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def audio_slug(s: str) -> str:
    """Must match normalize() in cyber/index.html."""
    s = s.lower()
    for src, dst in (("á","a"),("à","a"),("ä","a"),("â","a"),
                     ("é","e"),("è","e"),("ë","e"),("ê","e"),
                     ("í","i"),("ì","i"),("ï","i"),("î","i"),
                     ("ó","o"),("ò","o"),("ö","o"),("ô","o"),
                     ("ú","u"),("ù","u"),("ü","u"),("û","u"),
                     ("ñ","n"),("ç","c")):
        s = s.replace(src, dst)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def slice_balanced(text: str, start_pat: str, open_ch: str, close_ch: str) -> str:
    """Find start_pat, then return the substring from open_ch through the matching close_ch."""
    m = re.search(start_pat, text)
    if not m:
        raise RuntimeError(f"start_pat not found: {start_pat!r}")
    i = m.end() - 1
    if text[i] != open_ch:
        raise RuntimeError(f"expected {open_ch!r} at position, got {text[i]!r}")
    depth = 0
    in_str = False
    quote = None
    start = i
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                in_str = False
        else:
            if c in ('"', "'"):
                in_str = True
                quote = c
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start: i + 1]
        i += 1
    raise RuntimeError("unterminated block")


def parse_vocab(html: str) -> dict:
    """Pull every Spanish-speakable string out of cyber/index.html.

    Returns {level: {nouns:[(text, slug)], verbs:[...], phrases:[...]}}
    where 'nouns' also includes the 'el/la <word>' phrase form.
    """
    vocab_block = slice_balanced(html, r"const VOCAB\s*=\s*\{", "{", "}")
    out = {}
    for L in LEVELS:
        # Each level block: A1: { nouns: [...], verbs: [...], phrases: [...] }
        # Slice the level's body, then each sub-array within it.
        try:
            level_body = slice_balanced(vocab_block, rf"\b{L}\s*:\s*\{{", "{", "}")
        except RuntimeError:
            continue
        level_out = {"nouns": [], "verbs": [], "phrases": []}

        # nouns: {w:"...", e:"...", g:"..."}
        # Stressed-initial-a feminine nouns take "el" in the singular.
        STRESSED_A_FEM = {"agua","águila","alma","arma","aula","hacha","hambre","ala","área","ave","asa"}
        try:
            arr = slice_balanced(level_body, r"nouns\s*:\s*\[", "[", "]")
            for obj in re.finditer(r"\{[^{}]*\}", arr):
                o = obj.group(0)
                wm = re.search(r"\bw\s*:\s*\"([^\"]+)\"", o)
                gm = re.search(r"\bg\s*:\s*\"([^\"]+)\"", o)
                if wm:
                    w = wm.group(1)
                    level_out["nouns"].append(w)
                    if gm:
                        g = gm.group(1)
                        if g == "f" and w not in STRESSED_A_FEM:
                            art = "la"
                        else:
                            art = "el"
                        level_out["nouns"].append(f"{art} {w}")
        except RuntimeError:
            pass

        # verbs: {i:"...", e:"...", c:"..."}
        try:
            arr = slice_balanced(level_body, r"verbs\s*:\s*\[", "[", "]")
            for obj in re.finditer(r"\{[^{}]*\}", arr):
                o = obj.group(0)
                im = re.search(r"\bi\s*:\s*\"([^\"]+)\"", o)
                if im:
                    level_out["verbs"].append(im.group(1))
        except RuntimeError:
            pass

        # phrases: {s:"...", e:"...", n:"..."}
        try:
            arr = slice_balanced(level_body, r"phrases\s*:\s*\[", "[", "]")
            for obj in re.finditer(r"\{[^{}]*\}", arr):
                o = obj.group(0)
                sm = re.search(r"\bs\s*:\s*\"([^\"]+)\"", o)
                if sm:
                    level_out["phrases"].append(sm.group(1))
        except RuntimeError:
            pass

        out[L] = level_out
    return out


def build_jobs(vocab: dict, kind_filter: str | None):
    seen = set()
    for L, cats in vocab.items():
        for cat, texts in cats.items():
            if kind_filter and kind_filter != cat:
                continue
            for text in texts:
                slug = audio_slug(text)
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                yield (f"{L}/{cat}", text, OUT / f"{slug}.mp3")


async def gen_audio(text: str, path: Path, force: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio = bytearray()
    async for chunk in comm.stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise RuntimeError("no audio data")
    path.write_bytes(bytes(audio))
    return "generated"


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--force", action="store_true", help="Regenerate even if files exist")
    p.add_argument("--kind", choices=["nouns", "verbs", "phrases"], help="Only build one category")
    p.add_argument("--limit", type=int, help="Stop after N clips (smoke test)")
    p.add_argument("--dry-run", action="store_true", help="List what would be built without calling the API")
    args = p.parse_args()

    if not INDEX.exists():
        print(f"Missing {INDEX}", file=sys.stderr)
        sys.exit(1)

    html = INDEX.read_text(encoding="utf-8")
    vocab = parse_vocab(html)
    for L, cats in vocab.items():
        n = sum(len(v) for v in cats.values())
        print(f"  {L}: nouns={len(cats['nouns'])} verbs={len(cats['verbs'])} phrases={len(cats['phrases'])} (total {n})")

    jobs = list(build_jobs(vocab, args.kind))
    if args.limit:
        jobs = jobs[: args.limit]
    print(f"Total unique clips planned: {len(jobs)}")

    if args.dry_run:
        for label, text, path in jobs:
            marker = "EXISTS " if path.exists() else "missing"
            print(f"  [{marker}] {label}  {text!r}  ->  {path.name}")
        return

    summary = {"generated": 0, "skipped": 0, "failed": 0}
    for n, (label, text, path) in enumerate(jobs, 1):
        try:
            r = await gen_audio(text, path, args.force)
            summary[r] += 1
            if r == "generated" and (summary["generated"] % 25 == 0 or n == len(jobs)):
                print(f"  [{n:>4}/{len(jobs)}] {label}  {text!r}")
        except Exception as exc:
            print(f"  ! {label}  ERROR: {exc}", file=sys.stderr)
            summary["failed"] += 1

    print()
    print(f"Done. generated={summary['generated']} skipped={summary['skipped']} failed={summary['failed']}")
    print(f"Output: {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    asyncio.run(main())
