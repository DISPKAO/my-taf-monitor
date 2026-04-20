import streamlit as st
import requests
import re

st.set_page_config(page_title="專業 TAF 監控系統", layout="wide")
st.title("✈️ 航空氣象 TAF 深度監控與比對")

# --- 側邊欄 ---
input_icao = st.sidebar.text_input("輸入機場代碼", value="RCTP, RCSS, WSSS")
icao_list = [code.strip().upper() for code in re.split(r'[ ,]+', input_icao) if code.strip()]

def highlight_taf(taf):
    """標註危險天氣與低能見度"""
    text = str(taf)
    hazards = r"(\+RA|\+SHRA|TSRA|TSSH|TS|VCTS|VCSH|SN|FG|FZFG|BLSN|SQ|SS|DS|DU|FU|HZ)"
    text = re.sub(hazards, r'<span style="color:red; font-weight:bold;">\1</span>', text)
    # 能見度 < 800m
    text = re.sub(r"\s(0[0-7]\d{2})\s", r' <span style="color:red; font-weight:bold;">\1</span> ', text)
    # 低雲幕 < 500ft
    text = re.sub(r"((?:BKN|OVC)00[1-5])", r'<span style="color:red; font-weight:bold;">\1</span>', text)
    return text

def get_worst(taf_block):
    """分析報文中最低能見度、雲幕與有無雷雨"""
    vis_vals = [int(v) for v in re.findall(r"\s(\d{4})\s", taf_block)]
    min_vis = min(vis_vals) if vis_vals else 9999
    clouds = [int(c[1]) for c in re.findall(r"(BKN|OVC)(\d{3})", taf_block)]
    min_cloud = min(clouds) if clouds else 999
    has_ts = any(x in taf_block for x in ["TS", "+RA", "FG", "SN"])
    return min_vis, min_cloud, has_ts

def fetch_json_data(icao):
    """使用 JSON 格式抓取，確保版本不遺漏"""
    # 改用 json 格式 API
    url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json() # 這會回傳一個清單，每項代表一個版本
    except: pass
    return []

# --- 主畫面 ---
if icao_list:
    for icao in icao_list:
        with st.expander(f"📊 機場：{icao}", expanded=True):
            data_list = fetch_json_data(icao) # 這是從 API 拿到的陣列
            
            if len(data_list) >= 1:
                # --- 版本比對 (取 data_list[0] 和 [1]) ---
                if len(data_list) >= 2:
                    v1_raw = data_list[0].get('rawTAF', '')
                    v2_raw = data_list[1].get('rawTAF', '')
                    v1_v, v1_c, v1_t = get_worst(v1_raw)
                    v2_v, v2_c, v2_t = get_worst(v2_raw)
                    
                    diff = []
                    if v1_v < v2_v: diff.append(f"👁️ 能見度下降({v1_v}m)")
                    if v1_c < v2_c: diff.append(f"☁️ 雲幕下降({v1_c*100}ft)")
                    if v1_t and not v2_t: diff.append("⚠️ 新增危險天氣")
                    
                    if diff: st.error(f"🚨 較前版惡化：{' | '.join(diff)}")
                    else: st.success("✅ 天氣趨勢穩定")

                # --- 列表顯示所有版本 ---
                for i, item in enumerate(data_list):
                    raw = item.get('rawTAF', '')
                    issue_time = item.get('issueTime', '未知時間')
                    label = f"【最新版本】(發布時間: {issue_time})" if i == 0 else f"【歷史版本 {i}】({issue_time})"
                    
                    st.markdown(f"**{label}**")
                    # 將 \n 換成網頁換行
                    display = raw.replace('\n', '<br>&nbsp;&nbsp;&nbsp;&nbsp;')
                    st.markdown(
                        f'''<div style="background-color: #f9f9f9; padding: 12px; border-left: 5px solid {"#ff4b4b" if i==0 else "#ccc"}; 
                        border-radius: 5px; font-family: monospace; font-size: 15px; line-height: 1.5;">
                        {highlight_taf(display)}
                        </div>''', unsafe_allow_html=True
                    )
            else:
                st.info(f"查無 {icao} 預報資料。")
