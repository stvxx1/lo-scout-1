import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import time
import random
import urllib.parse

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="LO-SCOUT TITAN V18", layout="wide")

if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #0b0e14; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px; min-height: 540px;
    }
    .img-box { width: 100%; height: 320px; overflow: hidden; border-radius: 8px; background: #000; border: 1px solid #333; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 12px; }
    .tube-btn {
        background: #1f2937; color: #00f2ff !important; padding: 8px 2px; 
        border-radius: 4px; text-decoration: none; font-weight: 900; font-size: 0.7rem;
        border: 1px solid #374151; text-align: center; display: block;
    }
    .name-text { font-size: 1.1rem; font-weight: bold; margin: 10px 0; color: #fff; height: 30px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. STEALTH UTILITIES ---
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
]

def fetch_with_retries(scraper, url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            # FEATURE: Random 2-5 second delay
            time.sleep(random.uniform(2, 5))
            
            # FEATURE: Rotate User-Agent per attempt
            headers["User-Agent"] = random.choice(USER_AGENTS)
            
            response = scraper.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response
            elif response.status_code == 429: # FEATURE: Rate Limited
                st.warning(f"Rate limited (429). Backing off for {10 * (2 ** attempt)}s...")
                time.sleep(10 * (2 ** attempt))
            elif response.status_code == 403:
                st.error("Access forbidden (403). IP/User-Agent may be blocked.")
                return response
            elif response.status_code == 503:
                st.error("Service unavailable (503). Server is blocking.")
                return response
        except Exception as e:
            time.sleep(5)
    return None

# --- 3. THE ENGINE ---
def fetch_data(p_type, h_range, w_range, a_range, niches, page, p_l, p_t):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    
    # Trace-Perfect URL logic
    p_val = 'babe' if p_type == 'Babe' else 'male'
    cat_str = "".join([f"&f[categories][]={n.replace(' ', '%20')}" for n in niches])
    
    url = (
        f"https://www.freeones.com/performers?q=&page={page}&f[performerType]={p_val}{cat_str}"
        f"&r[appearance.metric.height]={h_range[0]},{h_range[1]}"
        f"&r[appearance.metric.weight]={w_range[0]},{w_range[1]}"
        f"&r[age]={a_range[0]},{a_range[1]}"
        f"&filter_mode[categories]=and&filter_mode[global]=and&s=rank.currentRank&o=desc"
    )
    if p_type == "Male":
        url += f"&r[appearance.metric.penis_length]={p_l[0]},{p_l[1]}&r[appearance.metric.penis_thickness]={p_t[0]},{p_t[1]}"

    # FEATURE: Advanced Headers
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.freeones.com/"
    }

    response = fetch_with_retries(scraper, url, headers)
    
    if not response or response.status_code != 200:
        return []

    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        batch = []
        script_tag = soup.find('script', id='__NEXT_DATA__')
        
        if script_tag:
            data = json.loads(script_tag.string)
            def extract_nodes(obj):
                if isinstance(obj, dict):
                    if 'edges' in obj and len(obj['edges']) > 0 and 'node' in obj['edges'][0]:
                        return obj['edges']
                    for k, v in obj.items():
                        res = extract_nodes(v)
                        if res: return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = extract_nodes(item)
                        if res: return res
                return None

            edges = extract_nodes(data)
            if edges:
                for edge in edges:
                    node = edge.get('node', {})
                    if node.get('name') and node.get('slug'):
                        batch.append({
                            "name": node.get('name'),
                            "slug": node.get('slug'),
                            "img": node.get('mainImage', {}).get('urls', {}).get('large', '')
                        })
        return batch
    except:
        return []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN V18")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    if st.button("🔄 FULL RESET"):
        st.session_state.current_results = []
        st.session_state.current_page = 1
        st.rerun()

    h_range = st.slider("Height", 80, 230, (88, 180))
    w_range = st.slider("Weight", 30, 180, (50, 110))
    a_range = st.slider("Age", 18, 80, (18, 30))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Length", 5, 40, (18, 28))
        p_t = st.slider("Thickness", 2, 15, (4, 8))

    min_m = st.slider("Min Minutes", 0, 120, 10)
    selected_niches = st.multiselect("Niches", ["Small Tits", "Chubby", "Big Boobs", "Teen", "Anal", "MILF", "Latina", "Asian", "Ebony"], default=["Small Tits"])

# --- 5. GRID ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            q = item["name"].replace(" ", "+")
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            st.markdown(f'''
                <div class="performer-card">
                    <div class="img-box"><img src="{item["img"]}" onerror="this.src='https://via.placeholder.com/300x400?text=No+Thumbnail';"></div>
                    <div class="name-text">{item["name"]}</div>
                    <div class="btn-grid">
                        <a class="tube-btn" href="https://www.xvideos.com/?k={q}&durf={xv_dur}" target="_blank">XV</a>
                        <a class="tube-btn" href="https://www.eporner.com/search/{q}/?min_len={min_m}" target="_blank">EP</a>
                        <a class="tube-btn" href="https://sexyprawn.com/search/all/{q}/?duration={min_m}-120" target="_blank">SP</a>
                        <a class="tube-btn" href="https://xmoviesforyou.com/?s={q}" target="_blank">XMFY</a>
                    </div>
                </div>
            ''', unsafe_allow_html=True)

st.divider()
if st.button("🚀 EXECUTE STEALTH SCAN", use_container_width=True):
    with st.spinner(f"Stealth Request: Page {st.session_state.current_page}..."):
        new_batch = fetch_data(p_type, h_range, w_range, a_range, selected_niches, st.session_state.current_page, p_l, p_t)
        if new_batch:
            st.session_state.current_results.extend(new_batch)
            st.session_state.current_page += 1
            st.rerun()
