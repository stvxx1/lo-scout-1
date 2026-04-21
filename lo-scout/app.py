import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="LO-SCOUT TITAN V6", layout="wide")

if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    .performer-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 10px; text-align: center; margin-bottom: 15px;
    }
    .img-box { width: 100%; height: 280px; overflow: hidden; border-radius: 6px; background: #000; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .tube-btn {
        background: #1f2937; color: #00f2ff !important; padding: 6px; 
        border-radius: 4px; text-decoration: none; font-weight: 900; font-size: 0.7rem;
        border: 1px solid #374151; display: inline-block; width: 45%; margin: 2px;
    }
    .debug-box { background: #2d0000; color: #ff6666; padding: 10px; border-radius: 5px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE DIAGNOSTIC ENGINE ---
def fetch_data(p_type, h_range, w_range, a_range, niches, page, p_len, p_thick):
    # Create a persistent session
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'android', 'desktop': False}
    )
    
    # URL construction (Verified against your Trace URL)
    base_params = [
        "q=", f"page={page}",
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}"
    ]
    for n in niches:
        base_params.append(f"f[categories]={urllib.parse.quote(n)}")
        
    base_params.extend([
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={a_range[0]},{a_range[1]}",
        "filter_mode[categories]=and", "filter_mode[global]=and",
        "s=rank.currentRank", "o=desc"
    ])

    if p_type == "Male":
        base_params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        base_params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")

    url = f"https://www.freeones.com/performers?{'&'.join(base_params)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.freeones.com/performers"
    }

    try:
        resp = scraper.get(url, headers=headers, timeout=15)
        
        # --- DEBUG OUTPUT ---
        if resp.status_code != 200:
            st.error(f"⚠️ SERVER REJECTED CONNECTION (Status: {resp.status_code})")
            if resp.status_code == 403:
                st.warning("Cloudflare has blocked the Streamlit Cloud IP. You may need to run this locally.")
            return [], resp.status_code
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        
        # Hunting for performers in JSON
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            js = json.loads(script.string)
            # Dynamic path search
            def find_edges(d):
                if isinstance(d, dict):
                    if 'edges' in d and len(d['edges']) > 0: return d['edges']
                    for v in d.values():
                        res = find_edges(v)
                        if res: return res
                elif isinstance(d, list):
                    for i in d:
                        res = find_edges(i)
                        if res: return res
                return None
            
            edges = find_edges(js)
            if edges:
                for e in edges:
                    n = e.get('node', {})
                    if n.get('name'):
                        img = n.get('mainImage', {}).get('urls', {}).get('large') or ""
                        results.append({"name": n['name'], "img": img, "slug": n.get('slug')})

        # Fallback to HTML link scraping
        if not results:
            links = soup.find_all('a', href=re.compile(r'/[^/]+/feed'))
            for l in links:
                name = l.get('href').split('/')[1].replace('-', ' ').title()
                img_tag = l.find_next('img')
                img = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
                if not any(r['name'] == name for r in results):
                    results.append({"name": name, "img": img, "slug": l.get('href').split('/')[1]})

        return results, resp.status_code
    except Exception as e:
        st.error(f"ENGINE CRASH: {str(e)}")
        return [], 0

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 COMMAND CENTER")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    if st.button("🔄 HARD RESET"):
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

    min_m = st.slider("Min Mins", 0, 120, 10)
    selected_niches = st.multiselect("Niches", ["Small Tits", "Chubby", "Big Boobs", "Teen", "Anal", "MILF", "Latina", "Asian"], default=["Small Tits"])

# --- 4. DISPLAY ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            q = item["name"].replace(" ", "+")
            st.markdown(f'''
                <div class="performer-card">
                    <div class="img-box"><img src="{item["img"]}"></div>
                    <div style="margin:10px 0"><strong>{item["name"]}</strong></div>
                    <a class="tube-btn" href="https://www.xvideos.com/?k={q}&durf=10min_more">XV</a>
                    <a class="tube-btn" href="https://www.eporner.com/search/{q}/">EP</a>
                    <div style="font-size:10px; margin-top:10px;"><a href="https://www.freeones.com/{item['slug']}/feed">Profile</a></div>
                </div>
            ''', unsafe_allow_html=True)

st.divider()
if st.button("🚀 INITIATE SCAN", use_container_width=True):
    with st.spinner("Bypassing firewalls..."):
        batch, status = fetch_data(p_type, h_range, w_range, a_range, selected_niches, st.session_state.current_page, p_l, p_t)
        if batch:
            st.session_state.current_results.extend(batch)
            st.session_state.current_page += 1
            st.rerun()
        elif status == 200:
            st.warning("Site loaded but no performers found with these filters.")
