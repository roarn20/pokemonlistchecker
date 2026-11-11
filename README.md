# Pokémon Set Price Tracker

A single-page HTML app (`index.html`, no build step) that shows every card in a Pokémon TCG set with its price, a set total, charts and buy links.

## How it works

1. **Pick a language**: English or Japanese.
2. **Pick a set.** The newest released set for that language loads automatically. All other sets are in the dropdown, grouped by year, with upcoming sets at the top.
3. **See every card**: picture, card number, name, rarity, price (plus reverse-holo and other print prices), and buttons to **buy on TCGplayer** or **check PriceCharting**.

Also included:

- **Sorting** by card number, name or price (tap a column header, or use the sort menu on phones). There's also a search box.
- **Set totals**: total cost of the set (one copy of each card), highest card, lowest card, average and median.
- **Charts**: the running total of the set cost card by card, and the top 10 most valuable cards. Hover or tap for details.
- **Auto-refresh** every 30 seconds (15 s, 1 min or 5 min in Settings), with a countdown ring and a manual **Refresh** button. Prices that changed since the last check flash and show ▲/▼.
- **Currencies**: USD, JPY, EUR, GBP, CAD and AUD, using live exchange rates.
- **Price type**: TCGplayer market, low or mid. PriceCharting ungraded or PSA 10 if you add a PriceCharting token.
- **Value history**: the total is saved in your browser each time it changes, and shown as a sparkline with the change since you started tracking.
- Light and dark themes, and a layout that works on phones.
- The URL remembers the language and set, so a refresh or a shared link opens the same set.

## Data sources

| Source | Used for | Key needed |
|---|---|---|
| [TCGdex](https://tcgdex.dev) | Sets and cards for English and Japanese, card pictures, **TCGplayer** prices (English cards), **Cardmarket** prices (Japanese and English cards), TCGplayer product numbers for direct buy links | No |
| [pokemontcg.io](https://pokemontcg.io) | English backup if TCGdex can't be reached | Optional |
| TCGplayer image server | Pictures for cards TCGdex has no scan of yet (common for brand-new sets) | No |
| [PriceCharting API](https://www.pricecharting.com/api-documentation) | Optional ungraded / PSA 10 prices | Yes (paid PriceCharting subscription) |
| [open.er-api.com](https://open.er-api.com), with [Frankfurter](https://frankfurter.app) as backup | Exchange rates | No |

The **Market price** setting uses the TCGplayer market price when there is one, and the Cardmarket trend price (converted from euros) when there isn't. **Cardmarket only** uses Cardmarket for every card.

### How the 30-second refresh works

The sources publish new prices about once a day (TCGdex around midnight UTC). Every 30 seconds the app re-reads the most valuable card. If that card's price timestamp has changed, it reloads the whole set. It also does a full reload every 15 minutes, and whenever you press **Refresh**. New prices show up within about 30 seconds of being published, without sending a request for every card every 30 seconds. Cards whose price changed flash and show ▲ or ▼.

### Limits

- **TCGplayer's own API is closed to new developers**, and the free TCGplayer data dump (TCGCSV) can't be read from a web page. TCGplayer prices come through TCGdex instead.
- **Japanese cards don't have TCGplayer prices** in any free source a web page can use. They show Cardmarket (European market) prices converted to your currency. Their TCGplayer button opens the exact Japanese product on TCGplayer when TCGdex knows it, and a search by card number otherwise.
- **Pictures:** TCGdex doesn't have scans for some recent sets. English cards fall back to TCGplayer's photo. Japanese cards do too when TCGdex has the TCGplayer product number, otherwise they show "No image".
- **PriceCharting** needs your own API token (Settings → PriceCharting API token). The app looks up each card by name, number and set, so a few cards may not match. Japanese cards rarely match, because their names come in Japanese. Lookups are cached for an hour, because PriceCharting updates daily and a set means one request per card. If PriceCharting blocks requests made from a browser page, the app tells you. Every card always has a PriceCharting button that opens a search for it.
- The set total is one copy of each card at the chosen price.
- Converted prices use live exchange rates. If no rate service can be reached, the app uses built-in approximate rates and says so.

## Running it

**Open it here (works on phones):** <https://raw.githack.com/roarn20/pokemonlistchecker/claude/pokemon-set-price-tracker-icxomp/index.html>

Open it in Safari, Chrome or another real browser. App previews and file viewers (including GitHub's file view and the preview in the Claude app) block the page from going online, so the card data can't load there. The page tells you when that happens and offers an "Open in browser" button.

It's a single static file, so any of these also work:

- **GitHub Pages:** repo **Settings → Pages → Build and deployment → Deploy from a branch**, pick the branch and `/ (root)`. The app is then at `https://<your-user>.github.io/<repo>/`. This is the easiest way to use it on a phone.
- **Locally:** open `index.html` in a browser, or run `python3 -m http.server` in this folder and go to <http://localhost:8000>.

Settings, API keys and price history are kept in your browser's local storage only. **Settings → Clear saved data** removes them.

Not affiliated with Nintendo, The Pokémon Company, TCGplayer or PriceCharting.
