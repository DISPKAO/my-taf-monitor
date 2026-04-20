import streamlit as st
import requests
import re

st.set_page_config(page_title="專業 TAF 監控比對系統", layout="wide")

st.title("✈️ 航空氣象 TAF 完整監控與版本比對")

# --- 側邊欄 ---
st.sidebar.header("監控參數")
input_icao = st.sidebar.text_input("機場代碼 (如: RCTP, RCSS, WSSS)", value="WSSS, RCTP")
icao_list = [code.strip().upper() for code in re.split(r'[ ,]+', input_icao) if code.strip()]

def highlight_taf(taf):
    """標註危險關鍵字與低能見度"""
    text = str(taf)
    # 標註危險天氣
    hazards = r"(\+RA|\+SHRA|TSRA|TSSH|TS|VCTS|VCSH|SN|FG|FZFG|BLSN|SQ|SS|DS|DU|FU|HZ)"
    text = re.sub(hazards, r'<span style="color:red; font-weight:bold;">\1</span>', text)
    
    # 標註低能見度 (< 0800m)
    def vis_check(match):
        v = int(match.group(1))
        if v < 800:
            return f' <span style="color:red; font-weight:bold;">{match.group(1)}</span> '
        return match.group(0)
    text = re.sub(r"\s(\d{4})\s", vis_check, text)
    
    # 標註低雲幕 (BKN/OVC 001-005)
    text = re.sub(r"((?:BKN|OVC)00[1-5])", r'<span style="color:red; font-weight:bold;">\1</span>', text)
    return text

def get_worst_values(taf_block):
    """從整份報文(含TEMPO)中抓取最差的能見度與雲幕值"""
    # 抓取所有 4 位數能見度
    vis_list = [int(v) for v in re.findall(r"\s(\d{4})\s", taf_block)]
    min_vis = min(vis_list) if vis_list else 9999
    
    # 抓取所有雲幕高度
    cloud_list = [int(c[1]) for c in re.findall(r"(BKN|OVC)(\d{3})", taf_block)]
    min_cloud = min(cloud_list) if cloud_list else 999
    
    # 抓取是否有雷雨等現象
    has_ts = any(x in taf_block for x in ["TS", "+RA", "FG", "SN"])
    
    return min_vis, min_cloud, has_ts

def fetch_data(icao):
    """獲取完整資料並切割版本"""
    url = f"https://aviationweather.gov/api/data/taf?ids={icao}"
    try:
        res = requests.get(url, timeout=10)
        content = res.text.strip()
        # 依據 TAF + 機場代碼 切割
        versions = re.split(r'(?=TAF\s' + icao + r')', content)
        return [v.strip() for v in versions if v.strip()]
    except:
        return []

# --- 主畫面 ---
if icao_list:
    for icao in icao_list:
        with st.expander(f"📊 機場：{icao}", expanded=True):
            data = fetch_data(icao)
            
            if len(data) >= 1:
                # --- 版本比對邏輯 ---
                if len(data) >= 2:
                    v1_vis, v1_cloud, v1_ts = get_worst_values(data[0])
                    v2_vis, v2_cloud, v2_ts = get_worst_values(data[1])
                    
                    diff_msg = []
                    if v1_vis < v2_vis:
                        diff_msg.append(f"👁️ 能見度轉差 ({v2_vis}m ➡️ {v1_vis}m)")
                    if v1_cloud < v2_cloud:
                        diff_msg.append(f"☁️ 雲幕轉低 ({v2_cloud*100}ft ➡️ {v1_cloud*100}ft)")
                    if v1_ts and not v2_ts:
                        diff_msg.append("⚠️ 新增危險天氣現象")
                    
                    if diff_msg:
                        st.error(f"🚨 **較前版惡化：** {' | '.join(diff_msg)}")
                    else:
                        st.success("✅ 與前版相比：天氣狀況穩定或趨向好轉")
                
                # --- 顯示完整報文 ---
                for i, full_taf in enumerate(data):
                    ver_label = "【最新發布版本】" if i == 0 else f"【歷史版本 {i}】"
                    st.markdown(f"**{ver_label}**")
                    
                    # 處理換行與標紅
                    display_text = full_taf.replace('\n', '<br>&nbsp;&nbsp;&nbsp;&nbsp;')
                    st.markdown(
                        f'''<div style="background-color: #f9f9f9; padding: 15px; 
                        border-left: 5px solid {"#ff4b4b" if i==0 else "#ccc"}; 
                        border-radius: 5px; font-family: monospace; font-size: 15px; line-height: 1.6;">
                        {highlight_taf(display_text)}
                        </div>''', 
                        unsafe_allow_html=True
                    )
            else:
                st.info(f"查無 {icao} 資料")
