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
  data/totals/<lang>.json             daily set totals (one copy of each card, TCGplayer market price, in
                                      cents) for the app's "up / down since yesterday" badge:
                                      {"start": day, "end": day, "sets": {"sv08.5": [395332, ...]},
                                       "counts": {"sv08.5": [180, ...]}}  (cards priced that day)
                                      (day = days since 1970-01-01, UTC). The first run fills in the last
                                      30 days from TCGCSV's daily price archives (needs: pip install py7zr).

Standard library only, except py7zr for the one-off backfill of set totals (skipped without it).
Run from the repo root:  python3 tools/build_variants.py
"""
import concurrent.futures as cf
import datetime as dt
import gzip
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data")
CATS = {"en": 3, "ja": 85}  # TCGplayer categories: Pokémon, Pokémon Japan
TCGDEX = "https://api.tcgdex.net/v2"
POCKET = re.compile(r"^(?:[AB]\d+[a-z]?|P-[A-Z])$")  # Pokémon TCG Pocket sets (digital only)
MAX_LOG = 300
TOTAL_DAYS = 120  # days of set totals kept
BACKFILL = 30     # days filled in from TCGCSV's price archives when missing
EPOCH = dt.date(1970, 1, 1)
# Which print's price counts for a card, like the app: normal, then holo, ..., reverse holo last.
PRINT_ORDER = ["normal", "holofoil", "1st edition holofoil", "1st edition normal", "1st edition", "unlimited holofoil", "unlimited", "reverse holofoil"]


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


def print_rank(name):
    n = (name or "").lower()
    return PRINT_ORDER.index(n) if n in PRINT_ORDER else (90 if "reverse" in n else 95)


def set_total(rows, base_ids):
    """One copy of each card at its first print's market price (else mid, else low): (cents, cards priced)."""
    by = {}
    for r in rows:
        by.setdefault(r.get("productId"), []).append(r)
    total, n = 0.0, 0
    for pid in base_ids:
        for r in sorted(by.get(pid, []), key=lambda r: print_rank(r.get("subTypeName"))):
            v = next((r[k] for k in ("marketPrice", "midPrice", "lowPrice") if isinstance(r.get(k), (int, float)) and r[k] > 0), None)
            if v:
                total += v
                n += 1
                break
    return (round(total * 100), n) if n else None


def archive_prices(day, keys):
    """One day's prices for the given TCGplayer sets, from TCGCSV's daily archive (a ~4 MB 7z file)."""
    try:
        import py7zr
    except ImportError:
        return None
    date = (EPOCH + dt.timedelta(days=day)).isoformat()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "prices.7z")
            req = urllib.request.Request(f"https://tcgcsv.com/archive/tcgplayer/prices-{date}.ppmd.7z", headers={"User-Agent": "pokemon-set-price-tracker/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())
            with py7zr.SevenZipFile(path, "r") as z:
                names = set(z.getnames())
                want = [t for t in (f"{date}/{CATS[lang]}/{gid}/prices" for lang, gid in keys) if t in names]
                z.extract(path=tmp, targets=want)
            out = {}
            for lang, gid in keys:
                fp = os.path.join(tmp, date, str(CATS[lang]), str(gid), "prices")
                if os.path.exists(fp):
                    with open(fp, encoding="utf-8") as f:
                        out[(lang, gid)] = (json.load(f) or {}).get("results") or []
            return out
    except Exception as e:
        print(f"  archive {date}: {e}")
        return None


def update_totals(group_sid, bases, live_rows, live_day):
    series = {}  # lang -> sid -> {day: (cents, cards priced)}
    for lang in CATS:
        old = load(os.path.join(DATA, "totals", f"{lang}.json"), {})
        start = old.get("start")
        series[lang] = {}
        if isinstance(start, int):
            counts = old.get("counts") or {}
            for sid, arr in (old.get("sets") or {}).items():
                ns = counts.get(sid) or []
                series[lang][sid] = {start + i: (v, ns[i] if i < len(ns) else None) for i, v in enumerate(arr) if isinstance(v, int)}

    def add(day, rows_by_key):
        for key, rows in rows_by_key.items():
            if rows is None or key not in group_sid:
                continue
            tot = set_total(rows, bases.get(key, []))
            if tot is not None:
                series[key[0]].setdefault(group_sid[key], {})[day] = tot

    add(live_day, live_rows)
    have = {d for lang in series for days in series[lang].values() for d in days}
    missing = [d for d in range(live_day - BACKFILL, live_day) if d not in have]
    if missing:
        print(f"Filling in {len(missing)} days of set totals from TCGCSV's archives...")
        keys = list(group_sid)
        for d in missing:
            rows = archive_prices(d, keys)
            if rows is None:
                print("  (py7zr not installed or archive unavailable; skipping the rest)")
                break
            add(d, rows)
    for lang in CATS:
        start = live_day - TOTAL_DAYS + 1
        rows = {}
        for sid, days in sorted(series[lang].items()):
            arr = [days.get(d) for d in range(start, live_day + 1)]
            while arr and arr[0] is None and len(arr) > 1:
                arr.pop(0)
            if any(v is not None for v in arr):
                rows[sid] = arr
        # Align every set to one start day so the file stays small and simple.
        first = min((live_day + 1 - len(a) for a in rows.values()), default=live_day)
        rows = {sid: [None] * (live_day + 1 - len(a) - first) + a for sid, a in rows.items()}
        sets = {sid: [v[0] if v else None for v in a] for sid, a in rows.items()}
        counts = {sid: [v[1] if v else None for v in a] for sid, a in rows.items()}
        write(os.path.join(DATA, "totals", f"{lang}.json"), {"start": first, "end": live_day, "sets": sets, "counts": counts})
        print(f"{lang}: daily totals for {len(sets)} sets, {live_day - first + 1} days")


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

    # Special prints per TCGplayer set: number -> [(label, productId)]; and each card's own product
    specials, counts, bases = {}, {}, {}
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
        base_ids = []
        for number, items in bynum.items():
            labelled = [(labels(str(p.get("name") or ""), number), p) for p in items]
            base = min(labelled, key=lambda x: (len(x[0]), len(str(x[1].get("name") or ""))))
            base_ids.append(base[1].get("productId"))
            if len(items) < 2:
                continue
            base_core = core(str(base[1].get("name") or ""), number)
            for lab, p in labelled:
                if p is base[1] or core(str(p.get("name") or ""), number) != base_core:
                    continue  # a different card that happens to share the number
                extra = sorted(lab - base[0])
                if not extra:
                    continue
                found.setdefault(num_key(number), []).append((canonical(" / ".join(extra)), p.get("productId")))
        bases[(lang, gid)] = base_ids
        if found:
            specials[(lang, gid)] = found

    # Prices for the special prints
    def fetch_prices(key):
        lang, gid = key
        try:
            return key, get(f"https://tcgcsv.com/tcgplayer/{CATS[lang]}/{gid}/prices")["results"]
        except Exception:
            return key, None

    prices, raw = {}, {}
    with cf.ThreadPoolExecutor(8) as ex:
        for key, rows in ex.map(fetch_prices, list(specials)):
            raw[key] = rows
            best = {}
            for r in rows or []:
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

    # Daily set totals for every matched set
    need = [k for k in group_sid if k not in raw and products.get(k)]
    with cf.ThreadPoolExecutor(8) as ex:
        for key, rows in ex.map(fetch_prices, need):
            raw[key] = rows
    try:
        stamp = urllib.request.urlopen(urllib.request.Request("https://tcgcsv.com/last-updated.txt", headers={"User-Agent": "pokemon-set-price-tracker/1.0"}), timeout=30).read().decode()[:10]
        live_day = (dt.date.fromisoformat(stamp) - EPOCH).days
    except Exception:
        live_day = (dt.datetime.now(dt.timezone.utc).date() - EPOCH).days
    update_totals(group_sid, bases, raw, live_day)

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
