import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

# --- 1. SESSION PERSISTENCE ---
if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

# This meta tag is critical to bypass thumbnail hotlink protection
st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #00f2ff; padding-top: 2rem; }
    .performer-card {
        background: #1f2937; border: 1px solid #374151; border-radius: 12px;
        padding: 12px; text-align: center; margin-bottom: 20px; transition: 0.3s;
    }
    .performer-card:hover { border-color: #00f2ff; transform: translateY(-5px); }
    .img-box { width: 100%; height: 300px; overflow: hidden; border-radius: 8px; background: #000; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .tube-btn {
        background: #374151; color: #00f2ff !important; padding: 5px 10px; 
        border-radius: 4px; text-decoration: none; font-size: 0.75rem; font-weight: bold;
        display: inline-block; margin: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GHOST ENGINE (BYPASS FOCUSED) ---
def fetch_titan_models(p_type, h_range, w_range, a_range, selected_cats, page, p_len, p_thick):
    # Updated to a more aggressive browser profile
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    # Headers must look like a real navigation request
    scraper.headers.update({
        "Referer": "https://www.freeones.com/performers",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    })

    # Exact reconstruction of the URL parameters from your link
    params = [
        "q=", 
        f"page={page}",
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}",
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={a_range[0]},{a_range[1]}",
        "filter_mode[global]=and", 
        "s=rank.currentRank", 
        "o=desc"
    ]
    
    if p_type == "Male":
        params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")
    
    if selected_cats:
        for cat in selected_cats:
            params.append(f"f[categories]={urllib.parse.quote(cat)}")
        params.append("filter_mode[categories]=and")

    url = f"https://www.freeones.com/performers?{'&'.join(params)}"
    
    try:
        resp = scraper.get(url, timeout=15)
        if resp.status_code != 200: return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        
        # Next.js Data Hunt
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            js = json.loads(script.string)
            # Safe nested get logic
            try:
                edges = js['props']['pageProps']['data']['performers']['edges']
                for e in edges:
                    node = e.get('node', {})
                    name = node.get('name')
                    if name:
                        img_urls = node.get('mainImage', {}).get('urls', {})
                        results.append({
                            "name": name,
                            "img": img_urls.get('large') or img_urls.get('small') or "",
                            "url": f"https://www.freeones.com/{node.get('slug')}/feed"
                        })
            except (KeyError, TypeError):
                pass
        
        # HTML Scrape Fallback
        if not results:
            cards = soup.select('div[data-test="performer-item"]')
            for card in cards:
                link = card.find('a', href=re.compile(r'/[^/]+/feed'))
                if link:
                    name = link.get('href').split('/')[1].replace('-', ' ').title()
                    img_tag = card.find('img')
                    img = img_tag.get('data-src') or img_tag.get('src') or ""
                    results.append({
                        "name": name,
                        "img": img,
                        "url": f"https://www.freeones.com{link.get('href')}"
                    })
        return results
    except Exception:
        return []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🔭 TITAN COMMAND")
    p_type = st.selectbox("Model Type", ["Babe", "Male"])
    
    if st.button("🔄 FULL SYSTEM RESET", use_container_width=True):
        st.session_state.current_results = []
        st.session_state.current_page = 1
        st.rerun()

    st.subheader("📏 Physical Filters")
    h_range = st.slider("Height (cm)", 80, 230, (140, 190))
    w_range = st.slider("Weight (kg)", 30, 180, (50, 100))
    a_range = st.slider("Age", 18, 80, (18, 30))
    
    p_l, p_t = (0,0), (0,0)
    if p_type == "Male":
        p_l = st.slider("Length (cm)", 5, 40, (18, 28))
        p_t = st.slider("Thickness (cm)", 2, 15, (4, 8))

    min_m = st.slider("Min Length (Mins)", 0, 120, 10)
    tags_list = ["Small Tits", "Chubby", "Big Boobs", "Teen", "Threesome", "Blowjobs", "Anal", "Lingerie", "POV", "Feet", "Big Butt", "MILF", "Amateur", "Latina", "Asian", "Ebony"]
    selected_tags = st.multiselect("Niches", tags_list)

# --- 4. MAIN INTERFACE ---
if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown('<div class="performer-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="img-box"><img src="{item["img"]}" onerror="this.src=\'https://via.placeholder.com/300x400?text=No+Thumbnail\';"></div>', unsafe_allow_html=True)
            st.write(f"**{item['name']}**")
            
            q_safe = urllib.parse.quote_plus(item['name'])
            xv_dur = "10min_more" if min_m >= 10 else "allduration"
            
            st.markdown(f"""
                <div style="margin-top: 10px;">
                    <a class="tube-btn" href="https://www.xvideos.com/?k={q_safe}&durf={xv_dur}" target="_blank">XV</a>
                    <a class="tube-btn" href="https://sexyprawn.com/search/all/{q_safe}/" target="_blank">SP</a>
                    <a class="tube-btn" href="https://www.eporner.com/search/{q_safe}/" target="_blank">EP</a>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(f"[FreeOnes Profile]({item['url']})")
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Scanner Ready. Apply filters and hit EXECUTE SCAN.")

st.divider()
btn_label = "🚀 LOAD NEXT BATCH" if st.session_state.current_results else "🚀 EXECUTE SCAN"
if st.button(btn_label, use_container_width=True):
    with st.spinner(f"Requesting Page {st.session_state.current_page}..."):
        batch = fetch_titan_models(p_type, h_range, w_range, a_range, selected_tags, st.session_state.current_page, p_l, p_t)
        if batch:
            st.session_state.current_results.extend(batch)
            st.session_state.current_page += 1
            st.rerun()
        else:
            st.warning("No response from server. Try changing your physical filter ranges or niches.")
