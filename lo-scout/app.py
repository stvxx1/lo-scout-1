import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import re

# --- 1. SETUP ---
st.set_page_config(page_title="LO-SCOUT TITAN V22", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .performer-card {
        background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 10px; text-align: center; margin-bottom: 15px;
    }
    .img-box { width: 100%; height: 280px; overflow: hidden; border-radius: 5px; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    .tube-link {
        display: inline-block; background: #238636; color: white !important;
        padding: 5px 10px; margin: 2px; border-radius: 4px; font-size: 0.8rem;
        text-decoration: none; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE PARSER ---
def parse_html_content(html_text):
    batch = []
    try:
        # Strategy A: The Next.js JSON Extraction (The "Golden" Way)
        soup = BeautifulSoup(html_text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        
        if script_tag:
            data = json.loads(script_tag.string)
            # This regex-like traversal finds the "edges" list anywhere in the deep JSON
            def extract_nodes(obj):
                if isinstance(obj, dict):
                    if 'edges' in obj and isinstance(obj['edges'], list):
                        return obj['edges']
                    for k, v in obj.items():
                        res = extract_nodes(v)
                        if res: return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = extract_nodes(item)
                        if res: return res
                return None
            
            items = extract_nodes(data)
            if items:
                for item in items:
                    node = item.get('node', {})
                    if node.get('name'):
                        batch.append({
                            "name": node.get('name'),
                            "img": node.get('mainImage', {}).get('urls', {}).get('large', ''),
                            "slug": node.get('slug')
                        })
        
        # Strategy B: Hardcore Regex (The "Brute Force" Way if JSON fails)
        if not batch:
            names = re.findall(r'"name":"([^"]+)"', html_text)
            slugs = re.findall(r'"slug":"([^"]+)"', html_text)
            # Filter out duplicates and non-performers
            unique_names = list(dict.fromkeys(names))
            for name in unique_names[:24]:
                batch.append({"name": name, "img": "", "slug": ""})

        return batch
    except Exception as e:
        st.error(f"Parsing failed: {e}")
        return []

# --- 3. UI ---
with st.sidebar:
    st.title("🔭 TITAN V22")
    mode = st.radio("Fetch Mode", ["Automatic", "Manual Paste"])
    min_m = st.number_input("Min Duration (Mins)", 10)

if mode == "Manual Paste":
    st.info("Right-click the site -> View Page Source -> Ctrl+A -> Ctrl+C. Paste below.")
    raw_input = st.text_area("Paste HTML Source Code Here", height=200)
    if st.button("🏗️ EXTRACT FROM PASTE"):
        results = parse_html_content(raw_input)
        st.session_state.results = results
else:
    # --- AUTO FETCH LOGIC ---
    if st.button("🚀 RUN AUTO-SCAN"):
        scraper = cloudscraper.create_scraper()
        # Using the exact URL from your paste
        url = "https://www.freeones.com/performers?s=rank.currentRank&o=desc"
        resp = scraper.get(url)
        st.session_state.results = parse_html_content(resp.text)

# --- 4. DISPLAY ---
if 'results' in st.session_state and st.session_state.results:
    st.success(f"Found {len(st.session_state.results)} performers!")
    cols = st.columns(4)
    for idx, p in enumerate(st.session_state.results):
        with cols[idx % 4]:
            q = p['name'].replace(" ", "+")
            st.markdown(f"""
                <div class="performer-card">
                    <div class="img-box"><img src="{p['img']}"></div>
                    <p><b>{p['name']}</b></p>
                    <a class="tube-link" href="https://www.xvideos.com/?k={q}&durf=10min_more">XV</a>
                    <a class="tube-link" href="https://www.eporner.com/search/{q}/">EP</a>
                </div>
            """, unsafe_allow_html=True)
