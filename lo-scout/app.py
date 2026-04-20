import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re

# --- 1. PERSISTENT STORAGE ---
if 'watchlist' not in st.session_state: st.session_state.watchlist = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'current_results' not in st.session_state: st.session_state.current_results = []

st.set_page_config(page_title="LO-SCOUT TITAN", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #1f2937; border: 1px solid #374151; border-radius: 12px;
        padding: 10px; text-align: center; margin-bottom: 15px;
    }
    .history-text { font-size: 0.75rem; color: #888; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE RE-ENGINEERED SCRAPER ---
@st.cache_data(ttl=300)
def fetch_titan_data(p_type, h_range, w_range, age_range, selected_cats, p_len=None, p_thick=None):
    scraper = cloudscraper.create_scraper()
    base_url = "https://www.freeones.com/performers"
    
    # Matching your exact URL structure requirements
    params = [
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}",
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={age_range[0]},{age_range[1]}",
        "filter_mode[performerType]=and",
        "filter_mode[global]=and"
    ]
    
    # Handle Categories in the 'f[categories]' format you provided
    if selected_cats:
        for cat in selected_cats:
            params.append(f"f[categories]={cat.replace(' ', '+')}")
        params.append("filter_mode[categories]=and")
    
    # Anatomy for Males
    if p_type == "Male" and p_len and p_thick:
        params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")

    full_url = f"{base_url}?{'&'.join(params)}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        resp = scraper.get(full_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        links = soup.find_all('a', href=re.compile(r'/[^/]+/feed'))
        results = []
        seen = set()
        for link in links:
            href = link.get('href')
            name = href.split('/')[1].replace('-', ' ').title()
            if name not in seen:
                img = link.find('img').get('src') if link.find('img') else ""
                results.append({"name": name, "img": img, "url": f"https://www.freeones.com{href}"})
                seen.add(name)
        return results
    except:
        return []

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🔭 TITAN COMMAND")
    
    with st.expander("⭐ WATCHLIST", expanded=False):
        for n, l in list(st.session_state.watchlist.items()):
            c1, c2 = st.columns([4,1])
            c1.markdown(f"[{n}]({l})")
            if c2.button("X", key=f"del_{n}"):
                del st.session_state.watchlist[n]
                st.rerun()

    st.divider()

    # Inputs
    p_type = st.selectbox("Option Box 1", ["Babe", "Male"])
    h_range = st.slider("Height Range (cm)", 100, 250, (104, 169))
    w_range = st.slider("Weight Range (kg)", 30, 200, (60, 120))
    a_range = st.slider("Age Range", 18, 75, (18, 30))
    
    p_l, p_t = None, None
    if p_type == "Male":
        st.subheader("Anatomy Specs")
        p_l = st.slider("Penis Length (cm)", 5, 40, (15, 25))
        p_t = st.slider("Penis Thickness (cm)", 2, 12, (4, 6))

    # Categories list
    tags_list = [
        "Chubby", "Striptease", "Softcore", "Hardcore", "Official Site", "Celebrity", "Big Boobs",
        "Masturbation", "Teen", "Threesome", "Toys", "Blowjobs", "Lesbian", "Anal",
        "Amateur", "Lingerie", "Interracial", "Small Tits", "Mature", "POV", "Fetish",
        "Feet", "Cumshot", "Stockings", "Big Butt", "Hairy", "Facial", "Roleplay",
        "Bikini", "Latina", "Asian", "Uniforms", "Housewife", "Casting", "Bondage",
        "Handjob", "Massage", "Big Cock", "Ebony", "BBW", "Upskirt", "Alt", "Close Up",
        "MILF", "Strap On", "Extreme", "Holiday", "Orgy", "Pantyhose", "Cuckold", "Interactive Porn"
    ]
    selected_tags = st.multiselect("Option Box 2", tags_list)

    if st.button("🚀 EXECUTE SCAN"):
        res = fetch_titan_data(p_type, h_range, w_range, a_range, selected_tags, p_l, p_t)
        st.session_state.current_results = res
        st.session_state.history.insert(0, f"{p_type} | {'+'.join(selected_tags[:1])}")

    st.divider()
    st.subheader("📜 History")
    for h in st.session_state.history[:3]:
        st.markdown(f"<div class='history-text'>{h}</div>", unsafe_allow_html=True)

# --- 4. MAIN DISPLAY ---
st.title("Discovery Feed")

if st.session_state.current_results:
    cols = st.columns(4)
    for i, item in enumerate(st.session_state.current_results):
        with cols[i % 4]:
            st.markdown('<div class="performer-card">', unsafe_allow_html=True)
            if item['img']: st.image(item['img'], use_container_width=True)
            st.write(f"**{item['name']}**")
            
            if st.button("⭐ Watch", key=f"w_{item['name']}"):
                st.session_state.watchlist[item['name']] = item['url']
                st.toast(f"Saved {item['name']}")

            st.markdown(f"[Stats]({item['url']})")
            q = item['name'].replace(' ', '+')
            st.markdown(f"[XV](https://www.xvideos.com/?k={q}) | [EP](https://www.eporner.com/search/{q}/)")
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("System Standby. Adjust ranges and Execute.")