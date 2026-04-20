import streamlit as st
import requests
import re

st.set_page_config(page_title="專業 TAF 全報文監控系統", layout="wide")

st.title("✈️ 航空氣象 TAF 監控 (完整報文版)")

# --- 側邊欄 ---
st.sidebar.header("監控參數")
input_icao = st.sidebar.text_input("機場代碼 (如: RCTP, RCSS, WSSS)", value="WSSS, RCTP")
icao_list = [code.strip().upper() for code in re.split(r'[ ,]+', input_icao) if code.strip()]

def highlight_taf(taf):
    """強化紅字標註邏輯"""
    text = str(taf)
    # 標註危險天氣 (TS, RA, SN, FG, 加上大雨符號)
    hazards = r"(\+RA|\+SHRA|TSRA|TSSH|TS|VCTS|VCSH|SN|FG|FZFG|BLSN|SQ|SS|DS|DU|FU|HZ)"
    text = re.sub(hazards, r'<span style="color:red; font-weight:bold;">\1</span>', text)
    
    # 標註低能見度 (< 0800m)
    def vis_check(match):
        v = int(match.group(1))
        if v < 800:
            return f' <span style="color:red; font-weight:bold;">{match.group(1)}</span> '
        return match.group(0)
    
    # 匹配 4 位數字能見度
    text = re.sub(r"\s(\d{4})\s", vis_check, text)
    
    # 標註低雲幕 (BKN/OVC 001-005)
    text = re.sub(r"((?:BKN|OVC)00[1-5])", r'<span style="color:red; font-weight:bold;">\1</span>', text)
    
    return text

def fetch_full_taf(icao):
    """抓取完整報文並依 TAF 開頭切割版本"""
    # 移除 format=raw，讓它回傳完整的多行格式
    url = f"https://aviationweather.gov/api/data/taf?ids={icao}"
    try:
        res = requests.get(url, timeout=10)
        content = res.text.strip()
        # 利用 "TAF" 這個關鍵字來切割不同的發布版本
        # (使用正則表達式在 TAF 字樣前切分)
        taf_versions = re.split(r'(?=TAF\s' + icao + r')', content)
        # 過濾掉空字串並去除多餘換行
        return [t.strip() for t in taf_versions if t.strip()]
    except:
        return []

# --- 主畫面 ---
if icao_list:
    for icao in icao_list:
        with st.expander(f"📊 機場：{icao} (完整報文監控)", expanded=True):
            data = fetch_full_taf(icao)
            
            if data:
                for i, full_taf in enumerate(data):
                    label = "【最新發布版本】" if i == 0 else f"【歷史版本 {i}】"
                    st.markdown(f"**{label}**")
                    
                    # 處理換行：將 TAF 報文中的換行符號轉為 HTML 的 <br> 標籤
                    formatted_taf = full_taf.replace('\n', '<br>&nbsp;&nbsp;&nbsp;&nbsp;')
                    
                    # 顯示標色後的完整報文
                    st.markdown(
                        f'''<div style="background-color: #f9f9f9; padding: 15px; 
                        border-left: 5px solid {"#ff4b4b" if i==0 else "#ccc"}; 
                        border-radius: 5px; font-family: 'Courier New', Courier, monospace; 
                        font-size: 15px; line-height: 1.6; color: #333;">
                        {highlight_taf(formatted_taf)}
                        </div>''', 
                        unsafe_allow_html=True
                    )
                    st.write("") 
            else:
                st.info(f"目前無法取得 {icao} 的完整資料。")
