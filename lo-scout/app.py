import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

# --- 1. CONFIG ---
st.set_page_config(page_title="LO-SCOUT TITAN V11", layout="wide")

if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #0b0e14; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px; min-height: 530px;
    }
    .img-box { width: 100%; height: 310px; overflow: hidden; border-radius: 8px; background: #000; border: 1px solid #333; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 12px; }
    .tube-btn {
        background: #1f2937; color: #00f2ff !important; padding: 8px 2px; 
        border-radius: 4px; text-decoration: none; font-weight: 900; font-size: 0.7rem;
        border: 1px solid #374151; text-align: center; display: block;
    }
    .name-text { font-size: 1.1rem; font-weight: bold; margin: 10px 0; color: #fff; height: 28px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINE (TRACE-ALIGNED) ---
def fetch_data(p_type, h_range, w_range, a_range, niches, page, p_len, p_thick):
    # Create scraper with the Android platform flag
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    
    # URL params matching your manual working link
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
        params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")

    url = f"https://www.freeones.com/performers?{'&'.join(params)}"
    
    # CRITICAL: Sec-CH-UA Headers from your SM-S928B Trace
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.freeones.com/",
        "Sec-CH-UA": '"Chromium";v="125", "Not.A/Brand";v="24", "Samsung Internet";v="25"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-CH-UA-Platform": '"Android"',
        "X-Requested-With": "com.android.chrome"
    }

    try:
        resp = scraper.get(url, headers=headers, timeout=15)
        if resp.status_code != 200: return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        batch = []
        
        # Scrape using the card container to keep image/name synced
        items = soup.select('[data-test="performer-item"]')
        
        for item in items:
            link = item.find('a', href=re.compile(r'/[^/]+/feed'))
            if link:
                slug = link.get('href').split('/')[1]
                name = slug.replace('-', ' ').title()
                
                # Image search restricted ONLY to this item's container
                img_tag = item.find('img')
                img_url = ""
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src') or ""
                
                if name and not any(x['name'] == name for x in batch):
                    batch.append({"name": name, "img": img_url, "slug": slug})
                    
        return batch
    except:
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN V11")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    if st.button("🔄 FULL RESET", use_container_width=True):
        st.session_state.current_results = []
        st.session_state.current_page = 1
        st.rerun()

    h_range = st.slider("Height (cm)", 80, 230, (88, 180))
    w_range = st.slider("Weight (kg)", 30, 180, (50, 110))
    a_range = st.slider("Age", 18, 80, (18, 30))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Penis Length (cm)", 5, 40, (18, 28))
        p_t = st.slider("Penis Thickness (cm)", 2, 15, (4, 8))

    min_m = st.slider("Min Minutes", 0, 120, 10)
    selected_niches = st.multiselect("Niches", ["Small Tits", "Chubby", "Big Boobs", "Teen", "Anal", "MILF", "Latina", "Asian", "Ebony"], default=["Small Tits"])

# --- 4. GRID ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            q = item["name"].replace(" ", "+")
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            st.markdown(f'''
                <div class="performer-card">
                    <div class="img-box"><img src="{item["img"]}" onerror="this.src='https://
