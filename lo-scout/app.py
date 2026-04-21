import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re

# --- 1. PERSISTENT STORAGE ---
if 'watchlist' not in st.session_state: st.session_state.watchlist = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'current_results' not in st.session_state: st.session_state.current_results = []

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #1f2937; border: 1px solid #374151; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 15px;
    }
    .btn-row { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; margin-top: 10px; }
    .tube-btn {
        background: #374151; color: #00f2ff !important; padding: 4px 8px; 
        border-radius: 4px; text-decoration: none; font-size: 0.75rem; font-weight: bold;
    }
    .tube-btn:hover { background: #4b5563; border: 1px solid #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE VIDEO ENGINE ---
@st.cache_data(ttl=300)
def fetch_titan_videos(selected_cats, page, dur_range):
    scraper = cloudscraper.create_scraper()
    # Now targeting the VIDEOS section
    base_url = "https://www.freeones.com/videos"
    
    # Duration is in seconds for the URL
    min_sec = dur_range[0] * 60
    max_sec = dur_range[1] * 60
    
    params = [
        f"page={page}",
        f"r[duration]={min_sec},{max_sec}",
        "filter_mode[global]=and",
        "s=relevance"
    ]
    
    if selected_cats:
        for cat in selected_cats:
            params.append(f"f[categories]={cat.replace(' ', '+')}")
        params.append("filter_mode[categories]=and")

    full_url = f"{base_url}?{'&'.join(params)}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0'}
        resp = scraper.get(full_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Selectors for Video Grid items
        items = soup.select('div[data-test="video-item"]')
        results = []
        for item in items:
            link_tag = item.select_one('a[href^="/video/"]')
            img_tag = item.select_one('img')
            title_tag = item.select_one('p, span') # Varies by site layout
            
            if link_tag:
                href = link_tag['href']
                title = link_tag.get('title') or (title_tag.text if title_tag else "Video Result")
                img = img_tag['src'] if img_tag else ""
                results.append({
                    "name": title.strip(), 
                    "img": img, 
                    "url": f"https://www.freeones.com{href}"
                })
        return results
    except Exception as e:
        st.error(f"Scrape Error: {e}")
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN VIDEO CMD")
    
    with st.expander("⭐ WATCHLIST"):
        for n, l in list(st.session_state.watchlist.items()):
            c1, c2 = st.columns([4,1])
            c1.markdown(f"[{n}]({l})")
            if c2.button("X", key=f"del_{n}"):
                del st.session_state.watchlist[n]
                st.rerun()

    st.divider()
    page_num = st.number_input("Page", min_value=1, value=1)
    
    # VIDEO LENGTH FILTERS (Minutes)
    st.subheader("⏱️ Video Specs")
    dur_range = st.slider("Duration (Minutes)", 0, 120, (10, 30))
    
    # Categories
    tags_list = ["Chubby", "Striptease", "Softcore", "Hardcore", "Official Site", "Celebrity", "Big Boobs", "Masturbation", "Teen", "Threesome", "Toys", "Blowjobs", "Lesbian", "Anal", "Amateur", "Lingerie", "Interracial", "Small Tits", "Mature", "POV", "Fetish", "Feet", "Cumshot", "Stockings", "Big Butt", "Hairy", "Facial", "Roleplay", "Bikini", "Latina", "Asian", "Uniforms", "Housewife", "Casting", "Bondage", "Handjob", "Massage", "Big Cock", "Ebony", "BBW", "Upskirt", "Alt", "Close Up", "MILF", "Strap On", "Extreme", "Holiday", "Orgy", "Pantyhose", "Cuckold", "Interactive Porn"]
    selected_tags = st.multiselect("Niches", tags_list)

    if st.button("🚀 EXECUTE SCAN"):
        res = fetch_titan_videos(selected_tags, page_num, dur_range)
        st.session_state.current_results = res
        st.session_state.history.insert(0, f"Pg {page_num} | {dur_range[0]}-{dur_range[1]}m")

# --- 4. MAIN FEED ---
st.title("Titan Video Feed")

if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown('<div class="performer-card">', unsafe_allow_html=True)
            if item['img']: st.image(item['img'], use_container_width=True)
            st.markdown(f"**{item['name'][:50]}...**")
            
            if st.button("⭐ Watch", key=f"w_{i}"):
                st.session_state.watchlist[item['name']] = item['url']
                st.toast("Saved to Watchlist")

            # THE TUBE HUB + DURATION FILTERS
            q = item['name'].replace(' ', '+')
            min_m = dur_range[0]
            
            # Map duration to tube buckets
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            
            st.markdown(f"""
                <div class="btn-row">
                    <a class="tube-btn" href="https://www.xvideos.com/?k={q}&durf={xv_dur}" target="_blank">XV</a>
                    <a class="tube-btn" href="https://www.eporner.com/search/{q}/?min_len={min_m}" target="_blank">EP</a>
                    <a class="tube-btn" href="https://sxyprn.com/search/all/{q}/?duration={min_m}-120" target="_blank">SP</a>
                    <a class="tube-btn" href="https://xmoviesforyou.com/?s={q}" target="_blank">XMFY</a>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("System Ready. Configure duration and execute.")
