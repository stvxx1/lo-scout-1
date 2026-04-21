import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json

# --- 1. PERSISTENT STORAGE ---
if 'watchlist' not in st.session_state: st.session_state.watchlist = {}
if 'current_results' not in st.session_state: st.session_state.current_results = []

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #1f2937; border: 1px solid #374151; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 15px; min-height: 450px;
    }
    .img-container { width: 100%; height: 280px; overflow: hidden; border-radius: 8px; margin-bottom: 10px; }
    .img-container img { width: 100%; height: 100%; object-fit: cover; }
    .tube-btn {
        background: #374151; color: #00f2ff !important; padding: 4px 8px; 
        border-radius: 4px; text-decoration: none; font-size: 0.75rem; font-weight: bold;
        display: inline-block; margin: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE REINFORCED ENGINE ---
def fetch_titan_models(p_type, h_range, w_range, a_range, selected_cats, page, p_len=None, p_thick=None):
    scraper = cloudscraper.create_scraper()
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
        if p_len: params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        if p_thick: params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")
    
    if selected_cats:
        for cat in selected_cats: params.append(f"f[categories]={cat.replace(' ', '+')}")

    full_url = f"{base_url}?{'&'.join(params)}"
    
    try:
        # High-authority header to look like a real desktop browser
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
        resp = scraper.get(full_url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # METHOD 1: Scrape from JSON Script (Most Reliable)
        script_data = soup.find('script', id='__NEXT_DATA__')
        results = []
        seen_names = set()

        if script_data:
            try:
                js = json.loads(script_data.string)
                # Navigate the nested JSON structure
                performers = js['props']['pageProps']['data']['performers']['edges']
                for p in performers:
                    node = p['node']
                    name = node['name']
                    # Hunt for the highest quality image URL in the JSON
                    img = node.get('mainImage', {}).get('urls', {}).get('large') or \
                          node.get('mainImage', {}).get('urls', {}).get('small') or ""
                    
                    results.append({
                        "name": name,
                        "img": img,
                        "url": f"https://www.freeones.com/{node['slug']}/feed"
                    })
                    seen_names.add(name)
            except: pass

        # METHOD 2: Fallback to Grid Scraping if JSON fails
        if not results:
            items = soup.select('div[data-test="performer-item"], [class*="PerformerCard"]')
            for item in items:
                link_tag = item.find('a', href=re.compile(r'/[^/]+/feed'))
                if not link_tag: continue
                
                name = link_tag.get('href').split('/')[1].replace('-', ' ').title()
                if name not in seen_names:
                    img_tag = item.find('img')
                    img_url = ""
                    if img_tag:
                        img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-original') or ""
                    
                    results.append({
                        "name": name,
                        "img": img_url,
                        "url": f"https://www.freeones.com{link_tag.get('href')}"
                    })
        return results
    except Exception as e:
        st.error(f"Scrape Failed: {e}")
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN COMMAND")
    
    p_type = st.selectbox("Type", ["Babe", "Male"])
    page_num = st.number_input("Page", min_value=1, value=1, step=1)
    
    st.subheader("📏 Anatomy Specs")
    h_range = st.slider("Height (cm)", 100, 250, (140, 190))
    w_range = st.slider("Weight (kg)", 30, 200, (50, 100))
    a_range = st.slider("Age", 18, 75, (18, 30))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Length (cm)", 5, 40, (18, 28))
        p_t = st.slider("Thickness (cm)", 2, 15, (4, 8))

    st.subheader("⏱️ Video Search")
    min_m = st.slider("Min Minutes", 0, 120, 10)

    tags_list = ["Chubby", "Striptease", "Softcore", "Hardcore", "Celebrity", "Big Boobs", "Masturbation", "Teen", "Threesome", "Blowjobs", "Lesbian", "Anal", "Amateur", "Lingerie", "Interracial", "Small Tits", "POV", "Fetish", "Feet", "Cumshot", "Stockings", "Big Butt", "Hairy", "Facial", "Roleplay", "Bikini", "Latina", "Asian", "Uniforms", "Housewife", "Casting", "Bondage", "Handjob", "Massage", "Big Cock", "Ebony", "BBW", "Upskirt", "Alt", "Close Up", "MILF", "Strap On"]
    selected_tags = st.multiselect("Niches", tags_list)

    if st.button("🚀 EXECUTE SCAN", use_container_width=True):
        st.cache_data.clear()
        st.session_state.current_results = fetch_titan_models(p_type, h_range, w_range, a_range, selected_tags, page_num, p_l, p_t)

# --- 4. MAIN FEED ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown('<div class="performer-card">', unsafe_allow_html=True)
            
            # The Image with a proper error handler
            img_html = f'<div class="img-container"><img src="{item["img"]}" onerror="this.src=\'https://via.placeholder.com/300x400?text=Reloading+Image\';"></div>'
            st.markdown(img_html, unsafe_allow_html=True)
            
            st.write(f"**{item['name']}**")
            
            q = item['name'].replace(' ', '+')
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            
            st.markdown(f"""
                <div style="margin: 8px 0;">
                    <a class="tube-btn" href="https://www.xvideos.com/?k={q}&durf={xv_dur}" target="_blank">XV</a>
                    <a class="tube-btn" href="https://www.eporner.com/search/{q}/?min_len={min_m}" target="_blank">EP</a>
                    <a class="tube-btn" href="https://sexyprawn.com/search/all/{q}/?duration={min_m}-120" target="_blank">SP</a>
                    <a class="tube-btn" href="https://xmoviesforyou.com/?s={q}" target="_blank">XMFY</a>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"[FreeOnes Profile]({item['url']})")
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("System Ready. Execute Scan to fetch data.")
