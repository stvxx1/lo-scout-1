import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import urllib.parse
import time

# --- 1. SYSTEM CONFIG ---
if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'current_page' not in st.session_state: st.session_state.current_page = 1

st.set_page_config(page_title="LO-SCOUT TITAN V5", layout="wide")

st.markdown("""
    <meta name="referrer" content="no-referrer">
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #0b0e14; border-right: 1px solid #00f2ff; }
    .performer-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 12px;
        padding: 10px; text-align: center; margin-bottom: 15px; min-height: 520px;
    }
    .img-box { width: 100%; height: 280px; overflow: hidden; border-radius: 6px; background: #000; }
    .img-box img { width: 100%; height: 100%; object-fit: cover; }
    
    /* Tube Site Buttons */
    .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 10px; }
    .tube-btn {
        background: #1f2937; color: #00f2ff !important; padding: 6px; 
        border-radius: 4px; text-decoration: none; font-weight: 900; font-size: 0.7rem;
        border: 1px solid #374151; transition: 0.2s;
    }
    .tube-btn:hover { border-color: #00f2ff; background: #0b0e14; }
    .meta-text { color: #9ca3af; font-size: 0.75rem; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ENGINE ---
def find_data_recursive(obj, key_to_find):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key_to_find: return v
            result = find_data_recursive(v, key_to_find)
            if result: return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_data_recursive(item, key_to_find)
            if result: return result
    return None

def fetch_data(p_type, h_range, w_range, a_range, niches, page, p_len, p_thick):
    # Aligning with your S24 Ultra Trace
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'android', 'desktop': False}
    )
    
    # URL Parameter Construction
    base_params = [
        "q=",
        f"page={page}",
        f"f[performerType]={'babe' if p_type == 'Babe' else 'male'}"
    ]
    
    for n in niches:
        base_params.append(f"f[categories]={urllib.parse.quote(n)}")
        
    base_params.extend([
        f"r[appearance.metric.height]={h_range[0]},{h_range[1]}",
        f"r[appearance.metric.weight]={w_range[0]},{w_range[1]}",
        f"r[age]={a_range[0]},{a_range[1]}",
        "filter_mode[categories]=and",
        "filter_mode[global]=and",
        "s=rank.currentRank",
        "o=desc"
    ])

    if p_type == "Male":
        base_params.append(f"r[appearance.metric.penis_length]={p_len[0]},{p_len[1]}")
        base_params.append(f"r[appearance.metric.penis_thickness]={p_thick[0]},{p_thick[1]}")

    url = f"https://www.freeones.com/performers?{'&'.join(base_params)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.freeones.com/",
        "X-Requested-With": "com.android.chrome"
    }

    try:
        resp = scraper.get(url, headers=headers, timeout=15)
        if resp.status_code != 200: return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        seen = set()

        # Try JSON first
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            js = json.loads(script.string)
            perf_data = find_data_recursive(js, 'performers')
            if perf_data and 'edges' in perf_data:
                for edge in perf_data['edges']:
                    node = edge.get('node', {})
                    name = node.get('name')
                    if name:
                        imgs = node.get('mainImage', {}).get('urls', {})
                        results.append({
                            "name": name,
                            "img": imgs.get('large') or imgs.get('small') or "",
                            "slug": node.get('slug')
                        })
                        seen.add(name)
        
        # HTML Fallback
        if not results:
            items = soup.find_all('a', href=re.compile(r'/[^/]+/feed'))
            for item in items:
                name_raw = item.get('href').split('/')[1]
                name = name_raw.replace('-', ' ').title()
                if name not in seen:
                    img_tag = item.find_next('img')
                    img_url = img_tag.get('data-src') or img_tag.get('src') or "" if img_tag else ""
                    results.append({"name": name, "img": img_url, "slug": name_raw})
                    seen.add(name)
                    
        return results
    except Exception:
        return []

# --- 3. SIDEBAR (ALL FEATURES REST
