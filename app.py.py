import streamlit as st
import requests
import re

st.set_page_config(page_title="專業 TAF 監控比對系統", layout="wide")

st.title("✈️ 航空氣象 TAF 版本完整監控")

# --- 側邊欄控制 ---
st.sidebar.header("監控參數")
input_icao = st.sidebar.text_input("輸入機場代碼 (例如: RCTP, RCSS, VHHH)", value="RCTP, RCSS")
icao_list = [code.strip().upper() for code in re.split(r'[ ,]+', input_icao) if code.strip()]

# --- 核心分析函數 ---
def get_weather_values(taf):
    """提取能見度與雲幕數值用於比對"""
    # 提取能見度 (尋找 4 位數，如 0800)
    vis = re.search(r"\s(\d{4})\s", taf)
    vis_val = int(vis.group(1)) if vis else 9999
    
    # 提取最低雲幕 (尋找 BKN/OVC 後的 3 位數)
    clouds = re.findall(r"(BKN|OVC)(\d{3})", taf)
    cloud_val = min([int(c[1]) for c in clouds]) if clouds else 999
    
    return vis_val, cloud_val

def analyze_hazards(taf):
    """偵測危險天氣關鍵字"""
    hazards = []
    if "TS" in taf: hazards.append("⚡雷雨")
    if "+RA" in taf: hazards.append("🌧️大雨")
    if "SN" in taf: hazards.append("❄️下雪")
    if "FG" in taf: hazards.append("🌫️霧")
    return hazards

def fetch_all_tafs(icao):
    """抓取該機場所有可用的 TAF 版本"""
    url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return [line.strip() for line in res.text.split('\n') if line.strip()]
    except:
        pass
    return []

# --- 主畫面邏輯 ---
if icao_list:
    for icao in icao_list:
        with st.expander(f"📊 機場：{icao} (所有版本)", expanded=True):
            data = fetch_all_tafs(icao)
            
            if len(data) >= 1:
                # 1. 惡化偵測 (對比 data[0] 與 data[1])
                alert_msg = []
                if len(data) >= 2:
                    new_vis, new_cloud = get_weather_values(data[0])
                    old_vis, old_cloud = get_weather_values(data[1])
                    
                    if new_vis < old_vis:
                        alert_msg.append(f"👁️ 能見度下降 ({old_vis}m -> {new_vis}m)")
                    if new_cloud < old_cloud:
                        alert_msg.append(f"☁️ 雲幕下降 ({old_cloud*100}ft -> {new_cloud*100}ft)")
                    
                    # 檢查新出現的危險天氣
                    new_h = analyze_hazards(data[0])
                    old_h = analyze_hazards(data[1])
                    added_h = [h for h in new_h if h not in old_h]
                    if added_h:
                        alert_msg.append(f"⚠️ 新增天氣：{'/'.join(added_h)}")

                # 2. 顯示警示橫幅
                if alert_msg:
                    st.error(f"🚨 偵測到天氣變差：{ ' | '.join(alert_msg) }")
                else:
                    st.success("✅ 目前預報穩定或趨向好轉")

                # 3. 完整列出所有 TAF 紀錄
                st.write("**發布紀錄 (最新排列至最舊):**")
                for i, taf_text in enumerate(data):
                    label = "【最新版本】" if i == 0 else f"【歷史版本 {i}】"
                    st.code(f"{label} {taf_text}", language="text")
            else:
                st.info(f"查無 {icao} 資料。")
else:
    st.warning("請先輸入機場代碼。")
