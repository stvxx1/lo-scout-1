import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

# --- 1. SETUP ---
st.set_page_config(page_title="LO-SCOUT TITAN V13", layout="wide")

if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    .performer-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px; min-height: 540px;
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

# --- 2. THE ENGINE ---
def fetch_data(p_type, h_range, w_range, a_range, niches, page, p_l, p_t):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    
    # URL structure from your trace
    params = [
        "q=", f"page={page}",
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}"
    ]
    for n in niches:
        params.append(f"f[categories]={urllib.parse.quote(n)}")
        
    params.extend([
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={a_range[0]},{a_range[1]}",
        "filter_mode[categories]=and", "filter_mode[global]=and",
        "s=rank.currentRank", "o=desc"
    ])

    if p_type == "Male":
        params.append(f"r[appearance.metric.penis_length]={p_l[0]},{p_l[1]}")
        params.append(f"r[appearance.metric.penis_thickness]={p_t[0]},{p_t[1]}")

    url = f"https://www.freeones.com/performers?{'&'.join(params)}"
    
    # Trace-accurate headers for S24 Ultra
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.freeones.com/",
        "X-Requested-With": "com.android.chrome"
    }

    try:
        resp = scraper.get(url, headers=headers, timeout=15)
        
        # LOG STATUS FOR DEBUGGING
        if resp.status_code != 200:
            return [], resp.status_code
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        batch = []

        # Find the JSON block (Next.js data)
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            js = json.loads(script.string)
            
            # Recursive search for performer nodes
            def find_nodes(obj):
                if isinstance(obj, dict):
                    if 'edges' in obj and len(obj['edges']) > 0 and 'node' in obj['edges'][0]:
                        return obj['edges']
                    for v in obj.values():
                        res = find_nodes(v)
                        if res: return res
                elif isinstance(obj, list):
                    for i in obj:
                        res = find_nodes(i)
                        if res: return res
                return None

            nodes = find_nodes(js)
            if nodes:
                for edge in nodes:
                    n = edge.get('node', {})
                    name = n.get('name')
                    img = n.get('mainImage', {}).get('urls', {}).get('large', '')
                    slug = n.get('slug')
                    if name and slug:
                        batch.append({"name": name, "img": img, "slug": slug})
        
        return batch, resp.status_code
    except Exception as e:
        st.error(f"Engine Error: {str(e)}")
        return [], 0

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN V13")
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

# --- 4. MAIN ---
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
                    <a href="https://www.freeones.com/{item['slug']}/feed" target="_blank" style="font-size:10px; color:#555; display:block; margin-top:10px;">FreeOnes Profile</a>
                </div>
            ''', unsafe_allow_html=True)

st.divider()
if st.button("🚀 EXECUTE SCAN", use_container_width=True):
    with st.spinner("Connecting..."):
        batch, status = fetch_data(p_type, h_range, w_range, a_range, selected_niches, st.session_state.current_page, p_l, p_t)
        if batch:
            st.session_state.current_results.extend(batch)
            st.session_state.current_page += 1
            st.rerun()
        else:
            if status == 403:
                st.error("🚨 ACCESS DENIED (403): The site has blocked the Streamlit server IP. You may need to run this locally or wait for the IP to cycle.")
            elif status == 200:
                st.warning("Connected, but no performers found. Try widening your Height/Weight sliders.")
            else:
                st.error(f"Server Error Code: {status}")
