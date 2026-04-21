import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

# --- 1. PERSISTENT STORAGE ---
if 'watchlist' not in st.session_state: st.session_state.watchlist = {}
if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

# Hotlink protection bypass + CSS styling
st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #1f2937; border: 1px solid #374151; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px; min-height: 460px;
        transition: transform 0.2s;
    }
    .performer-card:hover { transform: scale(1.02); border-color: #00f2ff; }
    .img-box { 
        width: 100%; height: 300px; overflow: hidden; border-radius: 8px; 
        background: #111827; position: relative;
    }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .tube-btn {
        background: #374151; color: #00f2ff !important; padding: 5px 10px; 
        border-radius: 4px; text-decoration: none; font-size: 0.8rem; font-weight: bold;
        display: inline-block; margin: 2px; border: 1px solid transparent;
    }
    .tube-btn:hover { border-color: #00f2ff; background: #111827; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE REINFORCED IMAGE ENGINE ---
def get_clean_thumb(node):
    """Safely deep dives into JSON node to find the best possible image URL."""
    try:
        main_img = node.get('mainImage') or {}
        urls = main_img.get('urls') or {}
        return urls.get('large') or urls.get('small') or "https://via.placeholder.com/300x400?text=No+Image"
    except Exception:
        return "https://via.placeholder.com/300x400?text=No+Image"

def fetch_titan_models(p_type, h_range, w_range, a_range, selected_cats, page, p_len, p_thick):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    base_url = "https://www.freeones.com/performers"
    
    params = [
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
    
    if selected_cats:
        for cat in selected_cats: params.append(f"f[categories]={cat.replace(' ', '+')}")

    full_url = f"{base_url}?{'&'.join(params)}"
    
    try:
        resp = scraper.get(full_url, timeout=15)
        if resp.status_code != 200:
            st.error(f"Connection blocked (Code {resp.status_code}).")
            return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        
        # PRIMARY: JSON SCRAPE (Highest Image Success Rate)
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            js = json.loads(script.string)
            data_node = js.get('props', {}).get('pageProps', {}).get('data', {})
            edges = data_node.get('performers', {}).get('edges', [])
            
            for e in edges:
                node = e.get('node') or {}
                name = node.get('name')
                if name:
                    results.append({
                        "name": name,
                        "img": get_clean_thumb(node),
                        "url": f"https://www.freeones.com/{node.get('slug')}/feed"
                    })
        
        # SECONDARY: HTML SCRAPE (Fallback if JSON shifts structure)
        if not results:
            cards = soup.select('div[data-test="performer-item"]')
            for card in cards:
                link = card.find('a', href=re.compile(r'/[^/]+/feed'))
                img_tag = card.find('img')
                if link and img_tag:
                    name = link.get('href').split('/')[1].replace('-', ' ').title()
                    img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('srcset', '').split(' ')[0]
                    if img_url and img_url.startswith('/'):
                        img_url = "https://www.freeones.com" + img_url
                        
                    results.append({
                        "name": name,
                        "img": img_url or "https://via.placeholder.com/300x400?text=No+Image",
                        "url": f"https://www.freeones.com{link.get('href')}"
                    })
        return results
    except Exception as e:
        st.error(f"Engine failure: {str(e)}")
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN SCROLLER")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    
    if st.button("🔄 RESET SEARCH", use_container_width=True):
        st.session_state.current_results = []
        st.session_state.current_page = 1
        st.cache_data.clear()
        st.rerun()

    st.subheader("📏 Anatomy Specs")
    h_range = st.slider("Height (cm)", 100, 230, (140, 190))
    w_range = st.slider("Weight (kg)", 30, 180, (50, 100))
    a_range = st.slider("Age", 18, 80, (18, 30))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Length (cm)", 5, 40, (18, 28))
        p_t = st.slider("Thickness (cm)", 2, 15, (4, 8))

    min_m = st.slider("Min Video Length (Mins)", 0, 120, 10)
    
    tags_list = ["Chubby", "Striptease", "Softcore", "Hardcore", "Big Boobs", "Masturbation", "Teen", "Threesome", "Blowjobs", "Lesbian", "Anal", "Amateur", "Lingerie", "Interracial", "Small Tits", "POV", "Fetish", "Feet", "Cumshot", "Stockings", "Big Butt", "Hairy", "Facial", "Roleplay", "Bikini", "Latina", "Asian", "MILF"]
    selected_tags = st.multiselect("Niches", tags_list)

# --- 4. MAIN FEED ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown('<div class="performer-card">', unsafe_allow_html=True)
            # Img Container with eager loading
            st.markdown(f'''
                <div class="img-box">
                    <img src="{item["img"]}" loading="eager" onerror="this.onerror=null;this.src='https://via.placeholder.com/300x400?text=Broken+Link';">
                </div>
            ''', unsafe_allow_html=True)
            
            st.write(f"**{item['name']}**")
            
            # Safe URL encoding for tube searches
            q_safe = urllib.parse.quote_plus(item['name'])
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            
            st.markdown(f"""
                <div style="margin: 10px 0;">
                    <a class="tube-btn" href="https://www.xvideos.com/?k={q_safe}&durf={xv_dur}" target="_blank">XV</a>
                    <a class="tube-btn" href="https://www.eporner.com/search/{q_safe}/?min_len={min_m}" target="_blank">EP</a>
                    <a class="tube-btn" href="https://sexyprawn.com/search/all/{q_safe}/?duration={min_m}-120" target="_blank">SP</a>
                    <a class="tube-btn" href="https://xmoviesforyou.com/?s={q_safe}" target="_blank">XMFY</a>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"[FreeOnes Profile]({item['url']})")
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("System Ready. Adjust filters and execute scan below.")

# LOAD / SCAN BUTTON
st.divider()
btn_label = "🚀 LOAD NEXT BATCH" if st.session_state.current_results else "🚀 EXECUTE SCAN"

if st.button(btn_label, use_container_width=True):
    with st.spinner(f"Fetching models (Page {st.session_state.current_page})..."):
        batch = fetch_titan_models(p_type, h_range, w_range, a_range, selected_tags, st.session_state.current_page, p_l, p_t)
        if batch:
            st.session_state.current_results.extend(batch)
            st.session_state.current_page += 1
            st.rerun()
        else:
            st.warning("No more results found matching these criteria.")
