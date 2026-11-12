# Pokémon Set Price Tracker

A single-page HTML app (`index.html`, no build step) that shows every card in a Pokémon TCG set with its price, a set total, charts and buy links.

## How it works

1. **Pick a language**: English or Japanese.
2. **Pick a set.** The newest released set for that language loads automatically. All other sets are in the dropdown, grouped by year, with upcoming sets at the top.
3. **See every card**: picture, card number, name, rarity, price (plus reverse-holo and other print prices), and buttons to **buy on TCGplayer** or **check PriceCharting**.

Also included:

- **Four tabs**: Sets, Master set, Collection and Wishlist.
- **Search every card** in the chosen language from the search bar at the top. For example, "Charizard" lists every Charizard card from every set with its price. Japanese and Chinese cards can be searched by English name or in their own language. Results start with the newest sets and can be sorted by price or name, and **Open set** jumps to the card inside its set.
- **Sorting** by card number, name or price, a filter box, **Cards I have / Cards I need**, and a **List / Binder** switch. Binder view shows card pictures in a grid with the ones you don't have greyed out.
- **Set totals**: total cost of the set (one copy of each card), highest card, lowest card, average and median. The set header also shows how many cards you have, what they're worth, and what the missing ones cost.
- **Charts**: the running total of the set cost card by card, and the top 10 most valuable cards.
- **Card window** (tap a card's picture):
  - TCGplayer and Cardmarket prices.
  - **PSA and other graded prices** with a price-by-grade chart (needs a PriceCharting key).
  - A recent-sales chart and your price-history chart.
  - eBay sold-listing links.
  - **My copies**: how many, which print, which grade and what you paid for each copy.
- **My collection**:
  - Tap ＋ to add a card, then use the card window for extra copies, prints, grades and prices paid.
  - The Collection tab shows total worth with a history line, **gain / loss** against what you paid, and the most valuable card.
  - **Biggest movers** shows the cards that rose or fell most over about a week.
  - Graded copies are valued at their graded price (PriceCharting key needed; otherwise the ungraded price is used and labelled).
- **Master set** tab: every print of every card in the set (normal, reverse holo, holo, 1st edition) as its own tick box, with "X of Y prints" and the cost to finish. It's the same record as your collection: ticking a print adds that copy, and copies you add anywhere else show up as ticked.
- **Wishlist**: tap ☆ Want on any card, set a target price, and the app highlights cards at or below their target. When you open the app it tells you how many have hit their target. **Got it** moves a card to your collection with today's price as what you paid.
- **Camera scanner**: line a card up in the frame and the app reads its number (and name on English cards), then shows the matching cards to add. Photos stay on your device.
- **Cloud sync** (optional): keeps your collection and wishlist in a private file in your GitHub account and in sync across devices. See below.
- **Backups**: Save backup / Load backup (a file), and **Spreadsheet** (a CSV of every copy with prices, paid and gain/loss).
- **Auto-refresh** every 30 seconds (15 s, 1 min or 5 min in Settings), with a countdown ring and a manual **Refresh** button. Prices that changed flash and show ▲/▼.
- **Currencies**: USD, JPY, EUR, GBP, CAD and AUD, using live exchange rates.
- **Languages**: English, Japanese and Traditional Chinese. Chinese sets match the Japanese ones card for card, so they get English names too.
- **Installs on your home screen** like an app (from your Cloudflare Pages link), with offline viewing of your collection.
- Light and dark themes, a phone layout, and the URL remembers your language and set.

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

### Cloud sync

1. Go to <https://github.com/settings/personal-access-tokens> and create a **fine-grained token**. Under permissions choose **Gists → Read and write**, and nothing else.
2. In the app, open Settings, paste it into **Cloud sync: GitHub key** and save. The app creates a private ("secret") gist called `pokemon-set-tracker.json` in your account and keeps it up to date.
3. On your other devices, paste the same key. The app finds the gist and merges it with what's already there.

Every card and wishlist entry records when it was last changed. When two devices change things, the newest change to each card wins, and deletions are kept. Prices aren't synced, because each device fetches its own.

Use this from your own Cloudflare Pages link rather than the raw.githack.com mirror. The mirror is shared by many websites, and any of them could read keys saved in your browser there. The app warns about this in Settings.

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

### Master set

Prints come from TCGdex's list of which versions exist, plus any version TCGplayer has a price for (TCGdex's list misses reverse holos on brand-new sets). Special patterns, like Poké Ball or Master Ball reverse holos, aren't listed separately.

## Running it

**Your link:** <https://pokemonlistchecker.pages.dev/> (Cloudflare Pages, once it's set up as below)

Open it in Safari, Chrome or another real browser. App previews and file viewers (including GitHub's file view and the preview in the Claude app) block the page from going online, so the card data can't load there. The page tells you when that happens and offers an "Open in browser" button.

### Cloudflare Pages (works with a private repo, free)

1. Sign up at <https://dash.cloudflare.com>, then go to **Workers & Pages → Create → Pages → Connect to Git** (Cloudflare may call it "Import an existing Git repository").
2. Connect GitHub. When GitHub asks which repositories Cloudflare can see, choose **Only select repositories → pokemonlistchecker**. Private repos work.
3. Pick the repo and set:
   - **Project name:** `pokemonlistchecker`. This gives the address `pokemonlistchecker.pages.dev`. If that name is taken, Cloudflare picks a slightly different one; put it in `HOSTED_URL` near the top of the script in `index.html`.
   - **Production branch:** `claude/pokemon-set-price-tracker-icxomp`
   - **Framework preset:** None · **Build command:** leave empty · **Build output directory:** `/`
4. **Save and Deploy.** After about a minute the app is live. Every push to the branch, including the weekly English-names update, redeploys it automatically.
5. Install it: in Safari tap **Share → Add to Home Screen**, or in Chrome tap **⋮ → Add to Home screen**.

Each web address keeps its own browser storage, so bring your collection over from the old link with cloud sync (add the same GitHub key on both) or **Save backup** there and **Load backup** here.

The page tells search engines not to list it, but anyone with the link can still open it. Your collection and keys are never in the repo or on the site; they stay in your browser and, with sync, in your private gist.

### Making the repo private

GitHub → repo **Settings → General → Danger Zone → Change visibility → Private**. Cloudflare keeps deploying as long as its GitHub app has access to the repo. The raw.githack.com mirror link and GitHub Pages (on a free GitHub plan) stop working for private repos, so use the Cloudflare link.

### Other ways

- **raw.githack.com mirror** (public repos only): <https://raw.githack.com/roarn20/pokemonlistchecker/claude/pokemon-set-price-tracker-icxomp/index.html>. The first visit shows an "External Content Notice"; tap **Open the page**.
- **GitHub Pages** (public repos, or private with a paid GitHub plan): repo **Settings → Pages → Deploy from a branch**, pick the branch and `/ (root)`.
- **Locally:** run `python3 -m http.server` in this folder and go to <http://localhost:8000>.

Settings, API keys and price history are kept in your browser's local storage only. **Settings → Clear saved data** removes them.

Not affiliated with Nintendo, The Pokémon Company, TCGplayer or PriceCharting.
