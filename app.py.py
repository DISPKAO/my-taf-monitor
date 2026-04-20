import streamlit as st
import requests
import re

st.set_page_config(page_title="專業 TAF 深度監控", layout="wide")
st.title("✈️ 航空氣象 TAF 完整歷史監控與比對")

# --- 側邊欄 ---
input_icao = st.sidebar.text_input("輸入機場代碼", value="WSSS, RCTP, RCSS")
icao_list = [code.strip().upper() for code in re.split(r'[ ,]+', input_icao) if code.strip()]

def format_and_highlight(taf):
    """處理換行排版與紅字標註"""
    # 1. 強制換行：在 TEMPO, BECMG, FM, PROB 前面加上換行
    formatted = re.sub(r"\s(TEMPO|BECMG|FM|PROB\d{2})\s", r"<br>&nbsp;&nbsp;<b>\1</b> ", taf)
    
    # 2. 標註危險天氣 (紅字加粗)
    hazards = r"(\+RA|\+SHRA|TSRA|TSSH|TS|VCTS|VCSH|SN|FG|FZFG|BLSN|SQ|SS|DS)"
    formatted = re.sub(f"({hazards})", r'<span style="color:red; font-weight:bold;">\1</span>', formatted)
    
    # 3. 標註低能見度 (< 0800m)
    def vis_replacer(match):
        v = int(match.group(1))
        if v < 800:
            return f' <span style="color:red; font-weight:bold;">{match.group(1)}</span> '
        return f" {match.group(1)} "
    formatted = re.sub(r"\s(\d{4})\s", vis_replacer, formatted)
    
    # 4. 標註低雲幕 (BKN/OVC 001-005)
    formatted = re.sub(r"((?:BKN|OVC)00[1-5])", r'<span style="color:red; font-weight:bold;">\1</span>', formatted)
    
    return formatted

def get_worst(taf_block):
    """分析報文中最差數值"""
    vis_vals = [int(v) for v in re.findall(r"\b(\d{4})\b", taf_block)]
    min_v = min(vis_vals) if vis_vals else 9999
    clouds = [int(c[1]) for c in re.findall(r"(BKN|OVC)(\d{3})", taf_block)]
    min_c = min(clouds) if clouds else 999
    has_ts = any(x in taf_block for x in ["TS", "+RA", "FG", "SN"])
    return min_v, min_c, has_ts

def fetch_history_data(icao):
    """增加 &prior=4 參數以抓取歷史版本"""
    # 關鍵修正：加入 &prior=4
    url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=json&prior=4"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # 確保按時間排序 (最新在前面)
            return sorted(data, key=lambda x: x.get('issueTime', ''), reverse=True)
    except: pass
    return []

# --- 主畫面 ---
if icao_list:
    for icao in icao_list:
        with st.expander(f"📊 機場：{icao}", expanded=True):
            data_list = fetch_history_data(icao)
            
            if len(data_list) >= 1:
                # 版本比對警告
                if len(data_list) >= 2:
                    v1_raw = data_list[0].get('rawTAF', '')
                    v2_raw = data_list[1].get('rawTAF', '')
                    v1_v, v1_c, v1_t = get_worst(v1_raw)
                    v2_v, v2_c, v2_t = get_worst(v2_raw)
                    
                    diff = []
                    if v1_v < v2_v: diff.append(f"👁️ 能見度下降({v1_v}m)")
                    if v1_c < v2_c: diff.append(f"☁️ 雲幕下降({v1_c*100}ft)")
                    if v1_t and not v2_t: diff.append("⚠️ 新增危險天氣")
                    
                    if diff: st.error(f"🚨 偵測到報文惡化：{' | '.join(diff)}")
                    else: st.success("✅ 與前版相比天氣趨勢平穩")

                # 顯示清單
                for i, item in enumerate(data_list):
                    raw = item.get('rawTAF', '')
                    time = item.get('issueTime', 'N/A')
                    label = f"【最新版本】 (發布: {time})" if i == 0 else f"【歷史版本 {i}】 (發布: {time})"
                    
                    st.markdown(f"**{label}**")
                    st.markdown(
                        f'''<div style="background-color: #f9f9f9; padding: 15px; border-left: 5px solid {"#ff4b4b" if i==0 else "#ccc"}; 
                        border-radius: 5px; font-family: 'Courier New', monospace; font-size: 15px; line-height: 1.7;">
                        {format_and_highlight(raw)}
                        </div>''', unsafe_allow_html=True
                    )
            else:
                st.info(f"查無 {icao} 資料。")
