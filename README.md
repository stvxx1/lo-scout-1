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
./.venv/bin/pytest -q -m live    # hits freeones.com
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
│   │   └── freeones.py      # Freeones-specific scraper
│   ├── models/
│   │   ├── __init__.py
│   │   ├── performer.py     # Performer data model
│   │   └── filters.py       # Filter configuration model
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py         # CSS theme with dark seductive styling
│   │   └── components.py    # Reusable UI components
│   ├── config.py            # Application configuration
│   └── app.py               # Main Streamlit application
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
- With `PORNDB_API_KEY` set, cards with no portrait fall back to ThePornDB's

### Profile dialog says "No ThePornDB API key configured"
- Set `PORNDB_API_KEY` (see Configuration) and reload the page
- Check the key with `curl -H "Authorization: Bearer $PORNDB_API_KEY" \
  "https://api.theporndb.net/performers?q=sara%20jay&per_page=1"`

### Filters not working
- Ensure min values are less than max values
- Dick length filter only appears for "Males" gender

## License

For educational purposes only. Use responsibly.