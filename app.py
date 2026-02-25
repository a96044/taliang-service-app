import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- 1. 初始化雲端連線 ---
# 注意：部署後需在 Streamlit Cloud Secrets 設定憑證
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data(worksheet_name):
    """讀取 Google 試算表資料"""
    return conn.read(worksheet=worksheet_name, ttl="0").fillna("")

def save_gsheet_data(worksheet_name, df):
    """更新 Google 試算表資料"""
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- 2. 系統頁面設定 (手機優化) ---
st.set_page_config(page_title="大量科技維修雲端系統", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 3. 登入介面 ---
if not st.session_state.logged_in:
    st.title("🌐 大量科技 - 維修雲端系統")
    st.info("外勤人員請登入以存取最新 SOP 與維修履歷")
    
    with st.form("login_form"):
        u = st.text_input("人員帳號")
        p = st.text_input("密碼", type="password")
        if st.form_submit_button("登入系統", use_container_width=True):
            try:
                users_df = load_gsheet_data("使用者權限")
                match = users_df[(users_df['帳號'].astype(str) == u) & (users_df['密碼'].astype(str) == p)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.u_name = match.iloc[0]['姓名']
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤")
            except Exception as e:
                st.error(f"連線失敗，請檢查 Secrets 設定。")

# --- 4. 主系統介面 ---
else:
    st.sidebar.title(f"👤 {st.session_state.u_name}")
    menu = st.sidebar.radio("功能選單", ["🔍 履歷查詢", "📝 新增維修回報"])
    if st.sidebar.button("登出系統"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 功能 A：履歷查詢 ---
    if menu == "🔍 履歷查詢":
        st.title("⚙️ 維修紀錄檢索")
        q = st.text_input("🔍 搜尋 (輸入機台、客戶或故障關鍵字)")
        
        try:
            df = load_gsheet_data("維修紀錄")
            if not df.empty:
                # 模糊搜尋邏輯
                disp_df = df[df.apply(lambda r: r.astype(str).str