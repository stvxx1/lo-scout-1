import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import random

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="LO-SCOUT TITAN V20", layout="wide")

if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    .performer-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px;
    }
    .img-box { width: 100%; height: 320px; overflow: hidden; border-radius: 8px; background: #000; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .tube-btn {
        background: #1f2937; color: #00f2ff !important; padding: 8px 2px; 
        border-radius: 4px; text-decoration: none; font-weight: 900; font-size: 0.7rem;
        border: 1px solid #374151; text-align: center; display: block;
    }
    .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE STEALTH ENGINE ---
def fetch_data(page, p_type):
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'android', 'desktop': False}
    )
    
    p_val = 'babe' if p_type == 'Babe' else 'male'
    url = f"https://www.freeones.com/performers?f[performerType]={p_val}&page={page}&s=rank.currentRank&o=desc"

    # FEATURE: Aggressive Stealth Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.freeones.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1"
    }

    try:
        # FEATURE: Increased Delay to mimic human browsing
        time.sleep(random.uniform(2, 5))
        
        resp = scraper.get(url, headers=headers, timeout=25)
        
        if resp.status_code != 200:
            st.error(f"Access Denied or Blocked. Status Code: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        batch = []
        
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            js = json.loads(script.string)
            
            def find_items(d):
                if isinstance(d, dict):
                    if 'edges' in d: return d['edges']
                    for v in d.values():
                        res = find_items(v)
                        if res: return res
                elif isinstance(obj, list):
                    for i in d:
                        res = find_items(i)
                        if res: return res
                return None

            items = find_items(js)
            if items:
                for item in items:
                    node = item.get('node', {})
                    name = node.get('name')
                    slug = node.get('slug')
                    img = node.get('mainImage', {}).get('urls', {}).get('large', '')
                    if name and slug:
                        batch.append({"name": name, "img": img, "slug": slug})
        
        return batch

    # FEATURE: Enhanced Error Logging
    except Exception as e:
        st.error(f"Engine Error: {str(e)}")
        print(f"DEBUG LOG: {e}") # Viewable in console
        return []

# --- 3. UI ---
with st.sidebar:
    st.title("🔭 TITAN V20")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    min_m = st.slider("Min Minutes", 0, 120, 10)
    if st.button("🔄 RESET APP"):
        st.session_state.current_results = []
        st.session_state.current_page = 1
        st.rerun()

# --- 4. DISPLAY ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            q = item["name"].replace(" ", "+")
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            st.markdown(f'''
                <div class="performer-card">
                    <div class="img-box"><img src="{item["img"]}" onerror="this.src='https://via.placeholder.com/300x400?text=No+Preview';"></div>
                    <div style="margin:10px 0; font-weight:bold;">{item["name"]}</div>
                    <div class="btn-grid">
                        <a class="tube-btn" href="https://www.xvideos.com/?k={q}&durf={xv_dur}" target="_blank">XV</a>
                        <a class="tube-btn" href="https://www.eporner.com/search/{q}/?min_len={min_m}" target="_blank">EP</a>
                        <a class="tube-btn" href="https://sexyprawn.com/search/all/{q}/?duration={min_m}-120" target="_blank">SP</a>
                        <a class="tube-btn" href="https://xmoviesforyou.com/?s={q}" target="_blank">XMFY</a>
                    </div>
                </div>
            ''', unsafe_allow_html=True)

if st.button("🚀 EXECUTE SCAN", use_container_width=True):
    with st.spinner(f"Contacting Server (Page {st.session_state.current_page})..."):
        new_batch = fetch_data(st.session_state.current_page, p_type)
        if new_batch:
            st.session_state.current_results.extend(new_batch)
            st.session_state.current_page += 1
            st.rerun()
        else:
            st.warning("No new data received. Check the error log above.")
