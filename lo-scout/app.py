import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re

# --- 1. SESSION & CACHE ---
if 'current_results' not in st.session_state: st.session_state.current_results = []

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

# --- 2. THE REINFORCED ENGINE ---
def fetch_titan_models(p_type, h_range, w_range, a_range, page, p_len, p_thick):
    scraper = cloudscraper.create_scraper()
    base_url = "https://www.freeones.com/performers"
    
    params = [
        f"page={page}",
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}",
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={a_range[0]},{a_range[1]}",
        "s=rank.currentRank", "o=desc"
    ]
    
    if p_type == "Male":
        params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")

    full_url = f"{base_url}?{'&'.join(params)}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        resp = scraper.get(full_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Target the grid items specifically
        items = soup.select('div[data-test="performer-item"], .grid-item')
        results = []
        
        for item in items:
            link_tag = item.find('a', href=re.compile(r'/[^/]+/feed'))
            if not link_tag: continue
            
            name = link_tag.get('href').split('/')[1].replace('-', ' ').title()
            
            # THE THUMBNAIL FIX: Check all possible image attributes
            img_tag = item.find('img')
            img_url = ""
            if img_tag:
                # Order of priority for lazy-loaded images
                img_url = img_tag.get('data-src') or \
                          img_tag.get('data-original') or \
                          img_tag.get('srcset') or \
                          img_tag.get('src') or ""
                
                # Clean up srcset if it exists (takes the first high-res link)
                if ',' in img_url: img_url = img_url.split(',')[0].split(' ')[0]
                
                # Upgrade to large format if it's a thumbnail
                img_url = img_url.replace('small', 'large').replace('thumb', 'profile')

            results.append({
                "name": name, 
                "img": img_url, 
                "url": f"https://www.freeones.com{link_tag.get('href')}"
            })
            
        return results
    except:
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN COMMAND")
    p_type = st.selectbox("Type", ["Babe", "Male"])
    page_num = st.number_input("Page", min_value=1, value=1)
    
    st.subheader("📏 Anatomy")
    h_range = st.slider("Height", 100, 220, (140, 190))
    w_range = st.slider("Weight", 30, 150, (50, 100))
    a_range = st.slider("Age", 18, 70, (18, 32))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Length", 5, 35, (18, 28))
        p_t = st.slider("Thickness", 2, 12, (4, 8))

    if st.button("🚀 EXECUTE SCAN", use_container_width=True):
        st.cache_data.clear()
        st.session_state.current_results = fetch_titan_models(p_type, h_range, w_range, a_range, page_num, p_l, p_t)

# --- 4. MAIN FEED ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown(f"""
                <div style="background:#1f2937; padding:10px; border-radius:12px; text-align:center; margin-bottom:15px; border: 1px solid #374151;">
                    <img src="{item['img']}" style="width:100%; border-radius:8px; aspect-ratio: 3/4; object-fit: cover;" 
                         onerror="this.onerror=null;this.src='https://via.placeholder.com/300x400?text=No+Image';">
                    <p style="margin-top:8px;"><strong>{item['name']}</strong></p>
                    <div style="display:flex; flex-wrap:wrap; gap:5px; justify-content:center;">
                        <a href="https://www.xvideos.com/?k={item['name'].replace(' ', '+')}&durf=10min_more" target="_blank" style="background:#00f2ff; color:#000; padding:4px 8px; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">XV</a>
                        <a href="https://sexyprawn.com/search/all/{item['name'].replace(' ', '+')}/" target="_blank" style="background:#00f2ff; color:#000; padding:4px 8px; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">SP</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("System Ready. Run scan to load performers.")
