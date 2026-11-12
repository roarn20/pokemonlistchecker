# Pokémon Set Price Tracker

A single-page HTML app (`index.html`, no build step) that shows every card in a Pokémon TCG set with its price, a set total, charts and buy links.

## How it works

1. **Pick a language**: English or Japanese.
2. **Pick a set.** The newest released set for that language loads automatically. All other sets are in the dropdown, grouped by year, with upcoming sets at the top.
3. **See every card**: picture, card number, name, rarity, price (plus reverse-holo and other print prices), and buttons to **buy on TCGplayer** or **check PriceCharting**.

Also included:

- **Search every card** in the chosen language from the search bar at the top. For example, "Charizard" lists every Charizard card from every set with its price. Japanese cards can be searched by English name ("Charizard") or Japanese name ("リザードン"). Results start with the newest sets and can be sorted by price or name. **Open set** jumps to the card inside its set.
- **My collection** tab: tap ＋ on any card (in a set, in search results or in a card's window) to add it. Owned cards get a green ✓ in set lists, and each set shows how many you have, what they're worth, and what the missing cards would cost. The collection tab shows the total worth (with a history line), card count, most valuable card, and every card with its quantity, which print you have (e.g. reverse holo) and its value. Sort and filter it, and tap a set name to jump to that card in its set.
- **Scan a card with the camera** (camera button next to Search, or in My collection). Line the card up in the frame and tap Capture. The app reads the card number (and the name on English cards) and shows the matching cards to pick from, so you can scan card after card. You can also use a photo from your library.
- **Card window** (tap a card's picture):
  - TCGplayer and Cardmarket prices for each print.
  - **PSA and other graded prices**, with a price-by-grade chart from Ungraded through Grade 7, 8, 9 and 9.5 to PSA 10, plus BGS, CGC, SGC, TAG and ACE 10. These need a PriceCharting key.
  - A **recent sales chart** of Cardmarket's 30-day, 7-day and 1-day averages, with a rising/falling note.
  - **Your price history** chart, recorded day by day in your browser.
  - Links to recent PSA 10 and PSA 9 sales on eBay, TCGplayer and PriceCharting.
  - Collection controls.
- **Sorting** by card number, name or price (tap a column header, or use the sort menu on phones). A filter box narrows the current set's list.
- **Set totals**: total cost of the set (one copy of each card), highest card, lowest card, average and median.
- **Charts**: the running total of the set cost card by card, and the top 10 most valuable cards. Hover or tap for details.
- **Auto-refresh** every 30 seconds (15 s, 1 min or 5 min in Settings), with a countdown ring and a manual **Refresh** button. Prices that changed since the last check flash and show ▲/▼.
- **Currencies**: USD, JPY, EUR, GBP, CAD and AUD, using live exchange rates.
- **Price type**: TCGplayer market, low or mid. PriceCharting ungraded or PSA 10 if you add a PriceCharting token.
- **Value history**: the total is saved in your browser each time it changes, and shown as a sparkline with the change since you started tracking.
- Light and dark themes, and a layout that works on phones.
- The URL remembers the language and set, so a refresh or a shared link opens the same set.
- **English names for Japanese cards and sets**, in brackets after the Japanese name, for example "リザードン (Charizard)". Search and name sorting use them too.

## Data sources

| Source | Used for | Key needed |
|---|---|---|
| [TCGdex](https://tcgdex.dev) | Sets and cards for English and Japanese, card pictures, **TCGplayer** prices (English cards), **Cardmarket** prices (Japanese and English cards), TCGplayer product numbers for direct buy links | No |
| [pokemontcg.io](https://pokemontcg.io) | English backup if TCGdex can't be reached | Optional |
| TCGplayer image server | Pictures for cards TCGdex has no scan of yet (common for brand-new sets) | No |
| [PriceCharting API](https://www.pricecharting.com/api-documentation) | Optional ungraded / PSA 10 prices | Yes (paid PriceCharting subscription) |
| [open.er-api.com](https://open.er-api.com), with [Frankfurter](https://frankfurter.app) as backup | Exchange rates | No |

The **Market price** setting uses the TCGplayer market price when there is one, and the Cardmarket trend price (converted from euros) when there isn't. **Cardmarket only** uses Cardmarket for every card.

### English names for Japanese cards

TCGdex only has Japanese names for Japanese cards. TCGplayer lists the same cards under English names. `tools/build_japanese_names.py` matches the two by set code and card number, and writes small files to `data/ja/` that the app loads. These files also give Japanese cards their TCGplayer picture and direct product link when TCGdex doesn't have them.

The files cover every Japanese set from about 2017 on (91 sets at the moment). Older sets, and a few starter decks TCGplayer doesn't list, show the Japanese name only.

The script also writes `data/ja/search.json`, one list of every Japanese card with an English name. That's what lets the search find Japanese cards by English name.

A GitHub Actions workflow (`.github/workflows/japanese-names.yml`) re-runs the script every Monday and commits any changes, so new sets get English names. You can also run it from the repo's **Actions** tab, or locally with `python3 tools/build_japanese_names.py`.

### My collection: where it's saved

Your collection is saved in your browser's storage, on that device, in that browser. It isn't uploaded anywhere. Use **Export** in the My collection tab now and then to save a backup file (`pokemon-collection-<date>.json`), and **Import** to load it back or move it to another device or browser. Clearing your browser's website data, or **Settings → Clear saved data**, deletes the collection.

Collection prices update when you open the tab (cards older than an hour), every 30 seconds while it's open, and whenever those cards load in a set or a search.

### Card scanner: how it works and its limits

The scanner uses [Tesseract.js](https://github.com/naptha/tesseract.js), an open-source text reader that runs in your browser. It downloads once (about 5 MB, from the jsDelivr CDN), and photos never leave your device.

1. The live camera view has a card-shaped frame. The app crops what's inside it at full resolution. For a photo from your library, it tries to find the card automatically.
2. It reads the card number at the bottom (e.g. `238/191`) and, on English cards, the name at the top.
3. It looks up cards with that number in sets of that size, and cards with that name, and lists the best matches with pictures and prices. You tap **Add** on yours.

It works best on regular cards, held flat in good light, filling the frame. On full-art cards the number is printed over the artwork and often can't be read. You'll usually get the right name but need to type the number. The name and number are always editable, with a **Find** button. Japanese cards are matched by number only, because the text reader is English-only, so pick the right set from the list.

### How the 30-second refresh works

The sources publish new prices about once a day (TCGdex around midnight UTC). Every 30 seconds the app re-reads the most valuable card. If that card's price timestamp has changed, it reloads the whole set. It also does a full reload every 15 minutes, and whenever you press **Refresh**. New prices show up within about 30 seconds of being published, without sending a request for every card every 30 seconds. Cards whose price changed flash and show ▲ or ▼.

### Limits

- **TCGplayer's own API is closed to new developers**, and the free TCGplayer data dump (TCGCSV) can't be read from a web page. TCGplayer prices come through TCGdex instead.
- **Japanese cards don't have TCGplayer prices** in any free source a web page can use. They show Cardmarket (European market) prices converted to your currency. Their TCGplayer button opens the exact Japanese product on TCGplayer when TCGdex knows it, and a search by card number otherwise.
- **Pictures:** TCGdex doesn't have scans for some recent sets. English cards fall back to TCGplayer's photo. Japanese cards do too when TCGdex has the TCGplayer product number, otherwise they show "No image".
- **PSA / graded prices** come from PriceCharting, which needs your own paid API key (Settings → PriceCharting API token). There's no free source of graded prices that a web page can use. Without a key, the card window links to recent PSA 10 and PSA 9 sales on eBay and to the card's PriceCharting page. PriceCharting allows 1 request per second and licenses its data for personal use, so the app sends one request every 1.25 seconds and saves results for a day. Opening a card takes one or two requests. Whole-set lookups only run when you choose a PriceCharting price in the Price menu, and take a few minutes.
- **Cardmarket recent-sales chart:** TCGdex occasionally links a card to the wrong Cardmarket product (often the regular print of a special art card). When Cardmarket and TCGplayer differ by more than three times, the card window warns that the Cardmarket numbers may be for a different version.
- **Price history** starts when you first open or collect a card. The app saves one price per day, in this browser only.
- **PriceCharting** needs your own API token (Settings → PriceCharting API token). The app looks up each card by name, number and set, so a few cards may not match. Japanese cards rarely match, because their names come in Japanese. Lookups are cached for an hour, because PriceCharting updates daily and a set means one request per card. If PriceCharting blocks requests made from a browser page, the app tells you. Every card always has a PriceCharting button that opens a search for it.
- The set total is one copy of each card at the chosen price.
- Converted prices use live exchange rates. If no rate service can be reached, the app uses built-in approximate rates and says so.

## Running it

**Open it here (works on phones):** <https://raw.githack.com/roarn20/pokemonlistchecker/claude/pokemon-set-price-tracker-icxomp/index.html>

The first time, that free mirror shows an "External Content Notice". Tap **Open the page** and it remembers that. For a cleaner permanent link, turn on GitHub Pages (below).

Open it in Safari, Chrome or another real browser. App previews and file viewers (including GitHub's file view and the preview in the Claude app) block the page from going online, so the card data can't load there. The page tells you when that happens and offers an "Open in browser" button.

It's a single static file, so any of these also work:

- **GitHub Pages:** repo **Settings → Pages → Build and deployment → Deploy from a branch**, pick the branch and `/ (root)`. The app is then at `https://<your-user>.github.io/<repo>/`. This is the easiest way to use it on a phone.
- **Locally:** open `index.html` in a browser, or run `python3 -m http.server` in this folder and go to <http://localhost:8000>.

Settings, API keys and price history are kept in your browser's local storage only. **Settings → Clear saved data** removes them.

Not affiliated with Nintendo, The Pokémon Company, TCGplayer or PriceCharting.
