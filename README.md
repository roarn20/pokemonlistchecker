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
| [TCGCSV](https://tcgcsv.com) (a free daily copy of TCGplayer's catalog and prices) | English and Japanese sets, cards, images, TCGplayer prices, direct TCGplayer product links | No |
| [pokemontcg.io](https://pokemontcg.io) | English backup source (TCGplayer + Cardmarket prices) | Optional |
| [TCGdex](https://tcgdex.dev) | English and Japanese backup source (Japanese card names and images) | No |
| [PriceCharting API](https://www.pricecharting.com/api-documentation) | Optional ungraded / PSA 10 prices | Yes (paid PriceCharting subscription) |
| [open.er-api.com](https://open.er-api.com), with [Frankfurter](https://frankfurter.app) as backup | Exchange rates | No |

In **Automatic** mode the app tries TCGCSV first, then pokemontcg.io (English only), then TCGdex. You can force one source in **Settings**.

### Limits

- **Prices update about once a day at the source.** TCGplayer data (via TCGCSV, pokemontcg.io or TCGdex) is refreshed by those services roughly daily. The app checks every 30 seconds, so new data shows up soon after it's published, but prices won't change every 30 seconds.
- **TCGplayer's own API is closed to new developers**, so TCGplayer prices come through the free services above rather than straight from TCGplayer.
- **PriceCharting** needs your own API token (Settings → PriceCharting API token). The app looks up each card by name, number and set, so a few cards may not match. PriceCharting lookups are cached for an hour, because PriceCharting updates daily and a set means one request per card. If PriceCharting blocks requests made from a browser page, the app tells you. Every card always has a PriceCharting button that opens a search for it.
- **Japanese prices** come from TCGplayer's Japanese catalog (via TCGCSV). If you switch to TCGdex, Japanese cards mostly have no prices.
- The set total is one copy of each card at the chosen price. Special pattern variants that TCGplayer lists as separate products are counted as separate cards.

## Running it

It's a single static file. Any of these work:

- **GitHub Pages:** repo **Settings → Pages → Build and deployment → Deploy from a branch**, pick the branch and `/ (root)`. The app is then at `https://<your-user>.github.io/<repo>/`. This is the easiest way to use it on a phone.
- **Locally:** open `index.html` in a browser, or run `python3 -m http.server` in this folder and go to <http://localhost:8000>.

Settings, API keys and price history are kept in your browser's local storage only. **Settings → Clear saved data** removes them.

Not affiliated with Nintendo, The Pokémon Company, TCGplayer or PriceCharting.
