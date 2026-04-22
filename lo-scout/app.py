import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import time

# --- 1. INTERFACE & S24 ULTRA STYLING ---
st.set_page_config(page_title="LO-SCOUT TITAN V17", layout="wide")

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

# --- 2. THE HANDSHAKE ENGINE ---
def fetch_data(p_type, h_range, w_range, a_range, niches, page, p_l, p_t):
    # Initialize scraper with trace-accurate mobile fingerprint
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    
    # Precise URL building from S24 Ultra Trace
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
        url += f"&r[appearance.metric.penis_length]={p_l[0]},{p_l[1]}"
        url += f"&r[appearance.metric.penis_thickness]={p_t[0]},{p_t[1]}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.freeones.com/",
        "Sec-CH-UA-Platform": '"Android"',
        "X-Requested-With": "com.android.chrome"
    }

    try:
        # Give the server a moment to respond (simulates human latency)
        response = scraper.get(url, headers=headers, timeout=20)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, 'html.parser')
        batch = []

        # Target the Next.js data script (The Gold Mine)
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if script_tag:
            data = json.loads(script_tag.string)
            
            # Navigate the nested JSON structure
            try:
                # Find the 'edges' list wherever it exists in the tree
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
                        name = node.get('name')
                        slug = node.get('slug')
                        # Lock image directly to name object
                        img = node.get('mainImage', {}).get('urls', {}).get('large', '')
                        
                        if name and slug:
                            batch.append({"name": name, "img": img, "slug": slug})
            except:
                pass
        
        return batch
    except:
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN V17")
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

# --- 4. DISPLAY ---
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
if st.button("🚀 EXECUTE SCAN", use_container_width=True):
    with st.spinner(f"Initiating Handshake Page {st.session_state.current_page}..."):
        new_batch = fetch_data(p_type, h_range, w_range, a_range, selected_niches, st.session_state.current_page, p_l, p_t)
        if new_batch:
            st.session_state.current_results.extend(new_batch)
            st.session_state.current_page += 1
            st.rerun()
        else:
            st.error("Fetch failed. If you see this, the site is blocking the script's connection. Try resetting and reducing the height range.")

