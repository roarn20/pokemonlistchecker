#!/usr/bin/env python3
"""Special prints (Poké Ball / Master Ball patterns, metal cards, stamps...) and catalog changes.

TCGplayer lists special prints as their own products, named after the card with a label in
brackets, e.g. "Eevee (Poke Ball Pattern)" or "Mew ex - 205/165 (151 Metal Card)". This script
reads TCGplayer's catalog for English and Japanese Pokémon (via TCGCSV), finds every card number
that has extra products, and matches them to TCGdex sets. Because it goes by the label, new kinds
of special prints are picked up automatically.

It also compares the catalog with the previous run, so the app's Updates tab can show what
changed: new sets, new cards and new special prints.

Writes:
  data/variants/index.json            {"checked": time, "en": {"sv08.5": 167, ...}, "ja": {...}}
  data/variants/<lang>/<set id>.json  {"set": name, "cards": {"001": [[label, productId, market, low, mid, high], ...]}}
  data/catalog.json                   per TCGplayer set: name, release date, card count, special print kinds
  data/changelog.json                 {"updated": time, "entries": [newest first]}

Standard library only. Run from the repo root:  python3 tools/build_variants.py
"""
import concurrent.futures as cf
import datetime as dt
import gzip
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data")
CATS = {"en": 3, "ja": 85}  # TCGplayer categories: Pokémon, Pokémon Japan
TCGDEX = "https://api.tcgdex.net/v2"
POCKET = re.compile(r"^(?:[AB]\d+[a-z]?|P-[A-Z])$")  # Pokémon TCG Pocket sets (digital only)
MAX_LOG = 300


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pokemon-set-price-tracker/1.0", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def num_key(number):
    n = str(number).split("/")[0].strip().upper()
    return n.lstrip("0") or "0"


def short_name(name):
    return re.sub(r"^[A-Za-z0-9.\-+ ]{1,14}:\s*", "", name).strip()


def norm(name):
    return re.sub(r"[^a-z0-9]", "", short_name(name).lower())


def labels(name, number):
    """The bracketed labels in a product name, e.g. {"Poke Ball Pattern"}."""
    n = name.replace(" - " + number, "")
    return set(x.strip() for x in re.findall(r"\(([^)]*)\)", n) if x.strip())


def core(name, number):
    """The card's own name without the number and bracketed labels, to tell variants from different cards."""
    n = re.sub(r"\([^)]*\)", " ", name.replace(" - " + number, ""))
    n = re.sub(r"\s+-\s+[A-Za-z-]*\d+[A-Za-z]*(/[A-Za-z-]*\d+)?\s*$", "", n)
    return re.sub(r"[^a-z0-9]", "", n.lower())


def canonical(label):
    # Japanese "Mirror Foil" / "Mirror Holofoil" is the plain reverse holo print TCGdex already lists.
    # Patterned mirrors ("Master Ball Mirror") keep their own name.
    if re.search(r"ball|pattern|energy|rocket", label, re.I):
        return label
    return "Reverse Holofoil" if re.search(r"mirror|reverse holo", label, re.I) else label


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write(path, obj, compact=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":") if compact else None, indent=None if compact else 1, sort_keys=True)
    old = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def tcgdex_sets(lang):
    sets = [s for s in get(f"{TCGDEX}/{lang}/sets") if s.get("id") and not (lang == "en" and POCKET.match(s["id"]))]

    def detail(s):
        try:
            return s["id"], get(f"{TCGDEX}/{lang}/sets/{urllib.request.quote(s['id'], safe='')}")
        except Exception:
            return s["id"], None

    with cf.ThreadPoolExecutor(8) as ex:
        return {sid: d for sid, d in ex.map(detail, sets) if d}


def main():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    groups, products = {}, {}
    for lang, cat in CATS.items():
        groups[lang] = [g for g in get(f"https://tcgcsv.com/tcgplayer/{cat}/groups")["results"] if g.get("groupId")]

    jobs = [(lang, CATS[lang], g["groupId"]) for lang in CATS for g in groups[lang]]

    def fetch_products(job):
        lang, cat, gid = job
        try:
            return job, get(f"https://tcgcsv.com/tcgplayer/{cat}/{gid}/products")["results"]
        except Exception:
            return job, None

    with cf.ThreadPoolExecutor(8) as ex:
        for (lang, cat, gid), res in ex.map(fetch_products, jobs):
            products[(lang, gid)] = res
    missing = sum(1 for v in products.values() if v is None)
    print(f"TCGplayer sets: {len(groups['en'])} English, {len(groups['ja'])} Japanese ({missing} couldn't be read)")
    if missing > len(jobs) * 0.2:
        sys.exit("Too many TCGplayer sets couldn't be read; not updating anything.")

    # Special prints per TCGplayer set: number -> [(label, productId)]
    specials, counts = {}, {}
    for (lang, gid), prods in products.items():
        if prods is None:
            continue
        bynum = {}
        for p in prods:
            ext = {e.get("name"): e.get("value") for e in p.get("extendedData") or []}
            number = (ext.get("Number") or "").strip()
            if number:
                bynum.setdefault(number, []).append(p)
        counts[(lang, gid)] = len(bynum)
        found = {}
        for number, items in bynum.items():
            if len(items) < 2:
                continue
            labelled = [(labels(str(p.get("name") or ""), number), p) for p in items]
            base = min(labelled, key=lambda x: (len(x[0]), len(str(x[1].get("name") or ""))))
            base_core = core(str(base[1].get("name") or ""), number)
            for lab, p in labelled:
                if p is base[1] or core(str(p.get("name") or ""), number) != base_core:
                    continue  # a different card that happens to share the number
                extra = sorted(lab - base[0])
                if not extra:
                    continue
                found.setdefault(num_key(number), []).append((canonical(" / ".join(extra)), p.get("productId")))
        if found:
            specials[(lang, gid)] = found

    # Prices for the special prints
    def fetch_prices(key):
        lang, gid = key
        try:
            return key, get(f"https://tcgcsv.com/tcgplayer/{CATS[lang]}/{gid}/prices")["results"]
        except Exception:
            return key, []

    prices = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for key, rows in ex.map(fetch_prices, list(specials)):
            best = {}
            for r in rows:
                pid = r.get("productId")
                if pid is None:
                    continue
                if pid not in best or (best[pid].get("marketPrice") is None and r.get("marketPrice") is not None):
                    best[pid] = r
            prices[key] = best

    # Match TCGplayer sets to TCGdex sets
    product_group = {(lang, p.get("productId")): gid for (lang, gid), prods in products.items() if prods for p in prods}
    index = {"checked": now}
    group_sid = {}  # (lang, TCGplayer group) -> TCGdex set id
    for lang in CATS:
        gs = groups[lang]
        sets = tcgdex_sets(lang)
        by_code, by_name = {}, {}
        for g in gs:
            codes = {(g.get("abbreviation") or "").strip()}
            m = re.match(r"^([A-Za-z0-9.\-+]+):", g.get("name") or "")
            if m:
                codes.add(m.group(1))
            for c in codes:
                if c:
                    by_code.setdefault(c.upper().replace("+", "P"), []).append(g)
            by_name.setdefault(norm(g.get("name") or ""), []).append(g)
        index[lang] = {}
        out_dir = os.path.join(DATA, "variants", lang)
        keep = set()
        for sid, d in sets.items():
            cards = d.get("cards") or []
            if not cards:
                continue
            cand = []
            if lang == "ja":
                cand = by_code.get(sid.upper().replace("+", "P"), [])
            else:
                nm = norm(d.get("name") or "")
                close = lambda g: abs(counts.get((lang, g["groupId"]), 0) - len(cards)) <= max(5, len(cards) * 0.15)
                cand = by_name.get(nm, [])
                if len(cand) != 1:
                    # Set codes get reused across eras, so a code match must also look like the same set.
                    ab = ((d.get("abbreviation") or {}).get("official") or "").upper()
                    cand = [g for g in by_code.get(ab, []) if close(g) or norm(g.get("name") or "").endswith(nm)] if ab else []
                if len(cand) != 1:
                    cand = [g for g in gs if len(nm) >= 3 and norm(g.get("name") or "").endswith(nm)]
                if len(cand) != 1:
                    # Last resort: the TCGplayer set that holds this set's first card's product.
                    try:
                        c0 = get(f"{TCGDEX}/en/cards/{urllib.request.quote(cards[0]['id'], safe='')}")
                        pid = next((v.get("productId") for v in ((c0.get("pricing") or {}).get("tcgplayer") or {}).values() if isinstance(v, dict) and v.get("productId")), None)
                        gid = product_group.get(("en", pid))
                        cand = [g for g in gs if g["groupId"] == gid] if gid else []
                    except Exception:
                        cand = []
            if len(cand) > 1:
                cand = sorted(cand, key=lambda g: abs(counts.get((lang, g["groupId"]), 0) - len(cards)))[:1]
            if not cand:
                continue
            g = cand[0]
            group_sid[(lang, g["groupId"])] = sid
            sp = specials.get((lang, g["groupId"]))
            if not sp:
                continue
            pr = prices.get((lang, g["groupId"]), {})
            out = {}
            for c in cards:
                hits = sp.get(num_key(c.get("localId", "")))
                if not hits:
                    continue
                rows = []
                for label, pid in hits:
                    r = pr.get(pid, {})
                    rnd = lambda v: round(v, 2) if isinstance(v, (int, float)) else None
                    rows.append([label, pid, rnd(r.get("marketPrice")), rnd(r.get("lowPrice")), rnd(r.get("midPrice")), rnd(r.get("highPrice"))])
                out[str(c["localId"])] = rows
            if out:
                write(os.path.join(out_dir, f"{sid}.json"), {"set": g["name"], "group": g["groupId"], "cards": out})
                index[lang][sid] = sum(len(v) for v in out.values())
                keep.add(f"{sid}.json")
        if os.path.isdir(out_dir):
            for f in os.listdir(out_dir):
                if f.endswith(".json") and f not in keep:
                    os.remove(os.path.join(out_dir, f))
        print(f"{lang}: special prints for {len(index[lang])} sets")
    write(os.path.join(DATA, "variants", "index.json"), index)

    # Catalog changes since the last run
    catalog = {}
    for lang in CATS:
        catalog[lang] = {}
        for g in groups[lang]:
            gid = g["groupId"]
            if products.get((lang, gid)) is None:
                continue
            kinds = sorted({lab for hits in specials.get((lang, gid), {}).values() for lab, _ in hits})
            catalog[lang][str(gid)] = {"n": g.get("name") or "", "p": (g.get("publishedOn") or "")[:10], "c": counts.get((lang, gid), 0), "v": kinds}
    old_catalog = load(os.path.join(DATA, "catalog.json"), None)
    log = load(os.path.join(DATA, "changelog.json"), {"entries": []})
    entries = log.get("entries") or []
    new = []
    lang_name = {"en": "English", "ja": "Japanese"}
    if not old_catalog:
        total = sum(1 for lang in catalog for v in catalog[lang].values() if v["c"])
        new.append({"t": now, "kind": "start", "lang": "", "text": f"Started watching TCGplayer's catalog: {total} English and Japanese sets."})
    else:
        for lang in catalog:
            before = old_catalog.get(lang, {})
            for gid, cur in catalog[lang].items():
                prev = before.get(gid)
                base = {"t": now, "lang": lang, "group": int(gid), "name": cur["n"]}
                if (lang, int(gid)) in group_sid:
                    base["set"] = group_sid[(lang, int(gid))]  # the app's set id, for "Open set"
                if prev is None:
                    if cur["c"]:
                        new.append(dict(base, kind="new-set", text=f"New {lang_name[lang]} set listed: {cur['n']} ({cur['c']} cards{', releases ' + cur['p'] if cur['p'] else ''})."))
                    continue
                if cur["c"] > prev.get("c", 0):
                    added = cur["c"] - prev.get("c", 0)
                    if prev.get("c", 0) == 0:
                        new.append(dict(base, kind="new-set", text=f"Cards listed for {cur['n']}: {cur['c']} cards."))
                    else:
                        new.append(dict(base, kind="new-cards", text=f"{cur['n']}: {added} more card{'s' if added != 1 else ''} listed (now {cur['c']})."))
                fresh = [k for k in cur["v"] if k not in (prev.get("v") or [])]
                if fresh:
                    new.append(dict(base, kind="new-variants", text=f"{cur['n']}: new special prints: {', '.join(fresh)}."))
    if new:
        entries = new + entries
        print(f"{len(new)} new changelog entries")
    write(os.path.join(DATA, "catalog.json"), catalog)
    write(os.path.join(DATA, "changelog.json"), {"checked": now, "updated": now if new else (log.get("updated") or now), "entries": entries[:MAX_LOG]})


if __name__ == "__main__":
    main()
