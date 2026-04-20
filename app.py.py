import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="多機場 TAF 監控系統", layout="wide")

st.title("✈️ 多機場 TAF 自動比對監控")

# --- 側邊欄設定 ---
st.sidebar.header("監控設定")
# 讓使用者輸入多個代碼，用逗號或空白隔開
input_icao = st.sidebar.text_input("輸入機場代碼 (例如: RCTP, RCSS, VHHH)", value="RCTP, RCSS")
# 將輸入轉為列表
icao_list = [code.strip().upper() for code in re.split(r'[ ,]+', input_icao) if code.strip()]

refresh_rate = st.sidebar.slider("自動整理頻率 (分鐘)", 1, 60, 5)

def analyze_taf(taf):
    hazards = []
    if not taf: return hazards
    # 天氣現象
    if "TS" in taf: hazards.append("⚡ 雷雨")
    if "+RA" in taf: hazards.append("🌧️ 大雨")
    if "SN" in taf: hazards.append("❄️ 下雪")
    if "FG" in taf: hazards.append("🌫️ 霧")
    
    # 低能見度 (低於 800m)
    vis = re.search(r"\s(\d{4})\s", taf)
    if vis and int(vis.group(1)) < 800:
        hazards.append(f"👁️ 低能見度({vis.group(1)}m)")
        
    # 低雲幕 (低於 500ft)
    clouds = re.findall(r"(BKN|OVC)(\d{3})", taf)
    for c_type, c_height in clouds:
        if int(c_height) < 5:
            hazards.append(f"☁️ 低雲幕({c_type}{c_height})")
    return hazards

def fetch_taf_data(icao):
    url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return [l.strip() for l in res.text.split('\n') if l.strip()]
    except:
        pass
    return []

# --- 主畫面顯示 ---
if icao_list:
    for icao in icao_list:
        with st.expander(f"📊 機場狀況：{icao}", expanded=True):
            data = fetch_taf_data(icao)
            
            if len(data) >= 2:
                new_taf, old_taf = data[0], data[1]
                
                # 分析天氣
                new_hazards = analyze_taf(new_taf)
                old_hazards = analyze_taf(old_taf)
                added_threats = [h for h in new_hazards if h not in old_hazards]
                
                # 介面佈局
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**最新 TAF:** `{new_taf}`")
                    st.markdown(f"**前版 TAF:** `{old_taf}`")
                
                with c2:
                    if added_threats:
                        st.error(f"🚨 惡化提醒：{', '.join(added_threats)}")
                    elif new_hazards:
                        st.warning(f"⚠️ 維持警報：{', '.join(new_hazards)}")
                    else:
                        st.success("✅ 天氣良好")
            else:
                st.info(f"無法取得 {icao} 的足夠預報資料進行比對。")
else:
    st.warning("請在左側輸入至少一個機場代碼。")

# 自動重新載入功能 (Streamlit 內建小技巧)
if st.sidebar.button("立即刷新"):
    st.rerun()