# LO-SCOUT TITAN V22

A professional Streamlit web application for discovering adult performers with advanced filtering and multi-site search integration.

## Features

- 🔮 **Advanced Filtering**: Filter performers by gender, height, weight, and length (for males)
- 📸 **Reliable Scraping**: Multiple extraction strategies for maximum success rate
- 🔄 **Pagination**: Load more performers with "Load More" button (24 per page, Freeones' own default)
- 🔗 **4-Site Integration**: Search performers on XVideos, Eporner, Sxyprn, and Xmoviesforyou
- 🖼️ **Resilient Portraits**: signed Freeones CDN images, initials fallback when a host fails
- ⭐ **Favourites**: save performers to a local sqlite db, browse them before any scan, export/import JSON
- 🎬 **Clip Panel**: search Eporner and RedTube for a performer and play the results inline
- ℹ️ **Profiles**: bios, measurements and aliases from ThePornDB (optional API key)
- 🔎 **Find Similar**: one click returns performers inside her height/weight window, filtered by Freeones itself
- 📚 **Second Opinion**: StashDB stats and portraits beside the ThePornDB profile (optional API key)
- 🎨 **Dark Theme**: Professional seductive UI with purple and magenta accents
- 📋 **Manual Mode**: Paste HTML source for when auto-fetch fails

## Installation

```bash
./run.sh
```

`run.sh` creates `.venv` on first launch, installs `requirements.txt`, and starts
the app at `http://localhost:8501`.

Manual equivalent:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/streamlit run lo-scout/app.py
```

## Tests

```bash
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/pytest -q            # offline, uses tests/fixtures
./.venv/bin/pytest -q -m live    # hits freeones.com, plus any keyed source you configured
```

## Usage

### Auto-Scan Mode
1. Use the sidebar to set your filters:
   - **Gender**: Babes or Males
   - **Height**: Min/Max in cm
   - **Weight**: Min/Max in kg
   - **Length**: Min/Max in cm (males only)
2. Click "🚀 RUN AUTO-SCAN" to start scanning
3. Browse results in the 4-column grid
4. Click "⚡ LOAD MORE" to load additional performers
5. Click any site button (XV, EP, SX, XM) to search that performer on the external site
6. With an API key configured, `ℹ️ Profile` opens her details and `🔎 Similar`
   shows performers inside her height/weight window

### Manual Paste Mode
1. Go to freeones.com in your browser
2. Right-click → View Page Source
3. Select all (Ctrl+A) and copy (Ctrl+C)
4. In the app sidebar, expand "📋 Manual Paste Mode"
5. Paste the HTML and click "🏗️ Extract from Paste"

## Project Structure

```
lo-scout-1/
├── lo-scout/
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── base.py          # Base scraper with HTTP client
│   │   ├── freeones.py      # Freeones listing scraper
│   │   ├── porndb.py        # ThePornDB profiles (keyed)
│   │   ├── stashdb.py       # StashDB profiles via GraphQL (keyed)
│   │   ├── similar.py       # "More like her" window, built on Freeones filters
│   │   └── videos.py        # Eporner/RedTube clip search
│   ├── models/
│   │   ├── __init__.py
│   │   ├── performer.py     # Performer data model
│   │   └── filters.py       # Filter configuration model
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py         # CSS theme with dark seductive styling
│   │   ├── components.py    # Reusable UI components
│   │   ├── profile_panel.py # Profile dialog (ThePornDB + StashDB)
│   │   ├── similar_panel.py # Similar-performer dialog
│   │   └── video_panel.py   # Clip dialog
│   ├── credentials.py       # API-key lookup shared by the keyed sources
│   ├── config.py            # Application configuration
│   └── app.py               # Main Streamlit application
├── tests/                   # offline by default, -m live for the network
├── requirements.txt
├── implementation_plan.md
└── README.md
```

## Configuration

Edit `config.py` to customize:
- External site URLs and icons
- Items per page (default: 24 — Freeones' own default; `robots.txt` forbids `l=`)
- Scraper timeout and retry settings
- Theme colors
- Default filter values

### ThePornDB (optional)

Bios, measurements, aliases and a portrait fallback come from
[ThePornDB](https://theporndb.net), which needs a free API key. Nothing else in
the app depends on it: without a key the Profile button is hidden and the grid
works exactly as before.

Put the key in `.streamlit/secrets.toml` (gitignored) or the environment:

```toml
PORNDB_API_KEY = "your-key-here"
```

```bash
export PORNDB_API_KEY="your-key-here"
```

The key is read from `$PORNDB_API_KEY`, `$LO_SCOUT_HOME/secrets.toml`, or
`.streamlit/secrets.toml` beside the app, the working directory or `~`.
Results are cached for 24 hours, and only cards with a *missing* portrait are
looked up (at most 6 per page), so a healthy listing costs no requests at all.

The same key is what powers **Find Similar**: it supplies the anchor height and
weight, which then become ordinary Freeones filters (`157,169` on
`r[appearance.metric.height]`). No key, no anchor -- so the button is hidden
rather than showing a dialog that cannot do anything.

### StashDB (optional, needs its own key)

StashDB is a second, crowd-curated source. Create a key in your
[StashDB](https://stashdb.org) account settings and add it the same way:

```toml
STASHDB_API_KEY = "your-key-here"
```

With it, the Profile dialog gains a **StashDB** tab (curated band/waist/hip
integers, career start year, scene count, a scene-linked portrait) and the source
label makes clear which record you are reading. Without it, the tab simply isn't
there. StashDB is also enough on its own: with only this key the Profile button
appears and opens on StashDB alone, while **Find Similar** stays hidden because
the anchor comes from ThePornDB.

Values are formatted the way ThePornDB writes them (`163cm`, `36E`, `American`)
because the two tabs share one stat grid, and a grid that reads `163cm` on one
tab and `163 cm` on the next looks like a bug rather than a second source.

Three details worth knowing:

- the endpoint is GraphQL, and unauthenticated queries answer HTTP 200 with
  `{"errors": [{"message": "not authorized"}]}` — that failure is *not* cached,
  so fixing the key takes effect immediately;
- names are matched strictly (exact name, then exact alias, then a lone result).
  This matters: asking for "Sara Jay" returns **Sara Jaymes first**, because
  stash-box name search is fuzzy. ThePornDB's search is fuzzy enough to justify
  containment matching; stash-box's is not, and showing a stranger's measurements
  is worse than showing nothing;
- portraits are plain `https://stashdb.org/images/<uuid>` URLs that load without
  a key, so the `<img>` in the browser works for users who never configured one.

The fixture in `tests/fixtures/stashdb_performer.json` is a recorded response,
not a guess — and recording it was worth it: the hand-written version assumed
`aliases` was one comma-separated string, while the live schema returns a list,
which rendered every alias as `['Sarah Jay']`. It also documents where the second
opinion pays off: both sources say 163cm and career start 2001, and they differ
only in how they spell the measurements (`36E-25-41` versus `36-25-41`).

### Boobpedia: deliberately not used

Boobpedia has the richest trivia, but its `robots.txt` disallows `/wiki/api.php`
and `/wiki/index.php?*action=` — i.e. both the MediaWiki API and the raw-wikitext
route. Scraping the rendered pages around that would be working around a stated
preference, so the app doesn't. ThePornDB and StashDB are both APIs that invite
this use.

## External Sites

The app generates search links for:
- **XVideos** (XV): Popular adult video site
- **Eporner** (EP): High-quality adult videos
- **Sxyprn** (SX): Adult video search engine
- **Xmoviesforyou** (XM): Adult movie database

## Technical Details

### Scraping Strategies
1. **Next.js JSON Extraction**: Parses `__NEXT_DATA__` script tag for structured data
2. **Enhanced Regex**: Pattern matching for performer data in HTML
3. **DOM Parsing**: BeautifulSoup fallback for HTML structure parsing

### Filter URL Building
Filters are converted to freeones.com URL parameters:
```
https://www.freeones.com/performers?s=rank.currentRank&o=desc&gender=babes&height_min=160&height_max=170
```

### Session State Management
- Performers list persists across page interactions
- Pagination state tracked for "Load More" functionality
- Filter state maintained during session

## Dependencies

- **streamlit**: Web application framework
- **cloudscraper**: Cloudflare bypass for HTTP requests
- **beautifulsoup4**: HTML parsing
- **fake-useragent**: Rotating user agents for better success rates

## Troubleshooting

### Scraping fails
- Try Manual Paste Mode instead of Auto-Scan
- Check if freeones.com is accessible in your region
- Increase timeout in config.py

### Images not loading
- Some performers may not have images (shows placeholder)
- Image URLs are validated before display
- With `PORNDB_API_KEY` set, cards with no portrait are looked up on ThePornDB
  (at most 6 per page), so a broken listing image still shows a face

### Profile dialog says "No metadata API key configured"
- Set `PORNDB_API_KEY` (see Configuration) and reload the page
- Check the key with `curl -H "Authorization: Bearer $PORNDB_API_KEY" \
  "https://api.theporndb.net/performers?q=sara%20jay&per_page=1"`

### Profile dialog shows no StashDB tab
- The tab only exists when `STASHDB_API_KEY` is set **and** StashDB has that
  performer. Check the key with:
  `curl -H "ApiKey: $STASHDB_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"{ queryPerformers(input: {names: \"Sara Jay\"}) { count } }"}' \
  https://stashdb.org/graphql`
- Without a key that call answers `{"errors":[{"message":"not authorized"}]}`
- A performer you know is on StashDB can still be dropped on purpose: the search
  ranks fuzzily ("Sara Jay" returns Sara Jaymes first), and if no result matches
  her name or an alias exactly, the tab stays closed rather than showing someone
  else's measurements

### "Find Similar" says there are no stats to match on
- The window is built from ThePornDB's height/weight, so the performer needs a
  profile that has them; try the height range in the sidebar instead
- A window that comes back empty is possible — the height facet is genuinely
  narrow (±6 cm), which is the point

### Filters not working
- Ensure min values are less than max values
- Dick length filter only appears for "Males" gender

## License

For educational purposes only. Use responsibly.