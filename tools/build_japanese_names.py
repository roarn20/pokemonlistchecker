#!/usr/bin/env python3
"""Build English names for Japanese Pokémon cards.

TCGdex (the app's data source) only has Japanese names for Japanese cards.
TCGplayer lists the same cards under English names, and TCGCSV publishes
TCGplayer's catalog as JSON. This script matches the two by set code and
card number and writes small JSON files the app loads:

  data/ja/sets.json        {"M2": "Inferno X", ...}
  data/ja/<set id>.json    {"set": "Inferno X", "cards": {"110": ["Mega Charizard X ex", 655892], ...}}

Card keys are TCGdex local ids. The number after each name is the TCGplayer
product id, which the app uses for pictures and direct buy links.

Standard library only. Run from the repo root:  python3 tools/build_japanese_names.py
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.request

TCGCSV = "https://tcgcsv.com/tcgplayer/85"  # 85 = Pokémon Japan on TCGplayer
TCGDEX = "https://api.tcgdex.net/v2/ja"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ja")
MIN_MATCH = 0.5  # drop a set if fewer than half its cards match (probably the wrong TCGplayer set)


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pokemon-set-price-tracker/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def set_key(code):
    """TCGplayer writes "SM5+" where TCGdex writes "SM5p"."""
    return code.strip().replace("+", "p")


def num_key(number):
    """'110/080' -> '110', '001' -> '1', 'SV-P 001' stays comparable."""
    n = str(number).split("/")[0].strip().upper()
    return n.lstrip("0") or "0"


def clean_name(name, number):
    n = name.replace(" - " + number, "")
    n = re.sub(r"\s+-\s+[A-Za-z-]*\d+[A-Za-z]*(/[A-Za-z-]*\d+)?\s*$", "", n)
    return n.strip() or name


def english_set_name(group_name):
    return re.sub(r"^[A-Za-z0-9.\-+ ]{1,14}:\s*", "", group_name).strip()


def numbered_products(group_id):
    out = {}
    for p in get(f"{TCGCSV}/{group_id}/products").get("results", []):
        ext = {e.get("name"): e.get("value") for e in p.get("extendedData") or []}
        number = (ext.get("Number") or "").strip()
        if not number:
            continue  # sealed product, code card, etc.
        name = clean_name(str(p.get("name") or ""), number)
        key = num_key(number)
        best = out.get(key)
        # Several products can share a number (pattern variants); keep the plainest name.
        if best is None or ("(" in best[0] and "(" not in name) or (("(" in best[0]) == ("(" in name) and len(name) < len(best[0])):
            out[key] = [name, p.get("productId")]
    return out


def main():
    groups = get(f"{TCGCSV}/groups")["results"]
    by_key = {}
    for g in groups:
        codes = set()
        if g.get("abbreviation"):
            codes.add(g["abbreviation"])
        m = re.match(r"^([A-Za-z0-9.\-+]+):", g.get("name") or "")
        if m:
            codes.add(m.group(1))
        for c in codes:
            by_key.setdefault(set_key(c).lower(), []).append((set_key(c), g))

    sets = get(f"{TCGDEX}/sets")
    print(f"TCGplayer Japanese sets: {len(groups)} · TCGdex Japanese sets: {len(sets)}")

    def build(s):
        sid = s["id"]
        cands = by_key.get(set_key(sid).lower(), [])
        if not cands:
            return sid, None, "no TCGplayer set"
        exact = [g for code, g in cands if code == set_key(sid)]
        pool = exact or [g for _, g in cands]
        detail = get(f"{TCGDEX}/sets/{urllib.request.quote(sid, safe='')}")
        cards = detail.get("cards") or []
        best = None
        for g in {g["groupId"]: g for g in pool}.values():
            prods = numbered_products(g["groupId"])
            names = {}
            for c in cards:
                hit = prods.get(num_key(c.get("localId", "")))
                if hit:
                    names[c["localId"]] = hit
            score = len(names) / max(1, len(cards))
            if best is None or score > best[0]:
                best = (score, g, names)
        if not best or best[0] < MIN_MATCH:
            return sid, None, f"only {best[0]:.0%} of cards matched" if best else "no cards"
        score, g, names = best
        return sid, {"set": english_set_name(g["name"]), "cards": names}, f"{len(names)}/{len(cards)} cards ← {g['name']}"

    os.makedirs(OUT_DIR, exist_ok=True)
    index = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for sid, data, note in ex.map(build, sets):
            if data:
                index[sid] = data["set"]
                with open(os.path.join(OUT_DIR, f"{sid}.json"), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            print(f"  {sid:10} {'OK  ' if data else 'skip'} {note}")
    with open(os.path.join(OUT_DIR, "sets.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"Wrote English names for {len(index)} Japanese sets to data/ja/")
    if not index:
        sys.exit("No sets matched; something is wrong with the sources.")


if __name__ == "__main__":
    main()
