import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

# --- 1. SESSION STATE ---
if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    .performer-card {
        background: #1f2937; border: 1px solid #374151; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px; min-height: 460px;
    }
    .img-box { width: 100%; height: 300px; overflow: hidden; border-radius: 8px; background: #111827; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .tube-btn {
        background: #374151; color: #00f2ff !important; padding: 5px 10px; 
        border-radius: 4px; text-decoration: none; font-size: 0.8rem; font-weight: bold;
        display: inline-block; margin: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ENGINE ---
def fetch_titan_models(p_type, h_range, w_range, a_range, selected_cats, page, p_len, p_thick):
    # Using a more aggressive scraper config
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
        delay=10
    )
    
    base_url = "https://www.freeones.com/performers"
    params = [
        "q=",
        f"page={page}",
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}",
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={a_range[0]},{a_range[1]}",
        "filter_mode[global]=and", "s=rank.currentRank", "o=desc"
    ]
    
    if p_type == "Male":
        params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")
    
    if selected_tags:
        for cat in selected_tags:
            params.append(f"f[categories]={urllib.parse.quote(cat)}")
        params.append("filter_mode[categories]=and")

    full_url = f"{base_url}?{'&'.join(params)}"
    
    try:
        resp = scraper.get(full_url, timeout=20)
        if resp.status_code != 200:
            st.error(f"Site returned Error {resp.status_code}. Usually means a temporary block.")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        seen = set()

        # --- TIER 1: JSON SEARCH ---
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            try:
                js = json.loads(script.string)
                # Broader search for the performers list in the JSON tree
                def find_performers(obj):
                    if isinstance(obj, dict):
                        if 'performers' in obj and 'edges' in obj['performers']:
                            return obj['performers']['edges']
                        for v in obj.values():
                            found = find_performers(v)
                            if found: return found
                    elif isinstance(obj, list):
                        for item in obj:
                            found = find_performers(item)
                            if found: return found
                    return None
                
                edges = find_performers(js)
                if edges:
                    for e in edges:
                        node = e.get('node', {})
                        name = node.get('name')
                        if name and name not in seen:
                            img = node.get('mainImage', {}).get('urls', {}).get('large') or ""
                            results.append({"name": name, "img": img, "url": f"https://www.freeones.com/{node.get('slug')}/feed"})
                            seen.add(name)
            except: pass

        # --- TIER 2: CSS SELECTORS ---
        if not results:
            cards = soup.select('div[data-test="performer-item"], .grid-item, [class*="PerformerCard"]')
            for card in cards:
                link = card.find('a', href=re.compile(r'/[^/]+/feed'))
                if link:
                    name = link.get('href').split('/')[1].replace('-', ' ').title()
                    if name not in seen:
                        img_tag = card.find('img')
                        img = img_tag.get('data-src') or img_tag.get('src') or ""
                        results.append({"name": name, "img": img, "url": f"https://www.freeones.com{link.get('href')}"})
                        seen.add(name)
        
        return results
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN COMMAND")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    
    if st.button("🔄 RESET ALL"):
        st.session_state.current_results = []
        st.session_state.current_page = 1
        st.rerun()

    h_range = st.slider("Height (cm)", 100, 230, (140, 190))
    w_range = st.slider("Weight (kg)", 30, 180, (50, 100))
    a_range = st.slider("Age", 18, 80, (18, 30))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Length", 5, 40, (18, 28))
        p_t = st.slider("Thickness", 2, 15, (4, 8))

    min_m = st.slider("Min Mins", 0, 120, 10)
    
    tags_list = ["Small Tits", "Chubby", "Big Boobs", "Teen", "Threesome", "Blowjobs", "Anal", "Lingerie", "POV", "Feet", "Big Butt", "MILF"]
    selected_tags = st.multiselect("Niches", tags_list)

# --- 4. MAIN FEED ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown(f'''
                <div class="performer-card">
                    <div class="img-box"><img src="{item["img"]}" onerror="this.src='https://via.placeholder.com/300x400?text=No+Img';"></div>
                    <p><strong>{item['name']}</strong></p>
                    <a class="tube-btn" href="https://www.xvideos.com/?k={item['name'].replace(' ', '+')}&durf=10min_more" target="_blank">XV</a>
                    <a class="tube-btn" href="https://sexyprawn.com/search/all/{item['name'].replace(' ', '+')}/" target="_blank">SP</a>
                    <br><br><a href="{item['url']}" target="_blank" style="color:#00f2ff; font-size:12px;">View Profile</a>
                </div>
            ''', unsafe_allow_html=True)

st.divider()
if st.button("🚀 EXECUTE / LOAD MORE", use_container_width=True):
    with st.spinner("Scanning..."):
        batch = fetch_titan_models(p_type, h_range, w_range, a_range, selected_tags, st.session_state.current_page, p_l, p_t)
        if batch:
            st.session_state.current_results.extend(batch)
            st.session_state.current_page += 1
            st.rerun()
        else:
            st.warning("No models found. Try broadening your filters or resetting.")
