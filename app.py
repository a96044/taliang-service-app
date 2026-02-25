import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- 1. 初始化雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data(worksheet_name):
    """讀取 Google 試算表資料"""
    return conn.read(worksheet=worksheet_name, ttl="0").fillna("")

def save_gsheet_data(worksheet_name, df):
    """更新 Google 試算表資料"""
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- 2. 系統頁面設定 ---
st.set_page_config(page_title="大量科技維修雲端系統", layout="wide")

# 初始化登入狀態
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 3. 登入介面 ---
if not st.session_state.logged_in:
    st.title("🌐 大量科技 - 維修雲端系統")
    st.info("外勤人員請登入以存取最新 SOP 與維修履歷")
    
    with st.form("login_form"):
        u = st.text_input("人員帳號")
        p = st.text_input("密碼", type="password")
        submit_login = st.form_submit_button("登入系統", use_container_width=True)
        
        if submit_login:
            try:
                users_df = load_gsheet_data("使用者權限")
                # 確保比對時型態一致
                match = users_df[(users_df['帳號'].astype(str) == str(u)) & (users_df['密碼'].astype(str) == str(p))]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.u_name = match.iloc[0]['姓名']
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤")
            except Exception as e:
                st.error("⚠️ 連線失敗！請確認 Secrets 中的 Spreadsheet 網址與權限設定。")

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
        q = st.text_input("🔍 搜尋關鍵字 (客戶、機台、故障類型...)")
        
        try:
            df = load_gsheet_data("維修紀錄")
            if not df.empty:
                # 修正後的搜尋邏輯：確保括號完整且支援不分大小寫
                if q:
                    mask = df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)
                    disp_df = df[mask]
                else:
                    disp_df = df
                
                st.write(f"找到 {len(disp_df)} 筆紀錄")
                
                for i, r in disp_df.iterrows():
                    header = f"【{r['客戶名稱']}】{r['機台號碼']} | {r['故障類型']}"
                    with st.expander(header):
                        st.markdown(f"**🗓 紀錄日期：** {r['紀錄日期']}")
                        st.markdown(f"**負責工程師：** {r['負責工程師']}")
                        st.markdown(f"**🛠 異常原因：**\n{r['異常原因']}")
                        st.markdown(f"**✅ 排除方式：**\n{r['排除方式']}")
                        
                        st.write("**📄 SOP 相關連結：**")
                        sop_data = str(r['SOP列表']).strip()
                        if sop_data and sop_data != "nan":
                            links = sop_data.split(";")
                            l_cols = st.columns(min(len(links), 4))
                            for idx, item in enumerate(links):
                                item = item.strip()
                                if "|" in item:
                                    l_name, l_url = item.split("|", 1)
                                else:
                                    l_name, l_url = "查看內容", item
                                with l_cols[idx % 4]:
                                    st.link_button(f"📖 {l_name}", l_url, use_container_width=True)
            else:
                st.warning("目前雲端資料庫尚無紀錄")
        except Exception as e:
            st.error(f"資料讀取錯誤，請確認工作表名稱是否為『維修紀錄』")

    # --- 功能 B：新增紀錄 ---
    elif menu == "📝 新增維修回報":
        st.title("✍️ 填寫維修紀錄")
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            c_name = c1.text_input("客戶名稱")
            c_id = c2.text_input("機台號碼")
            c_type = st.selectbox("故障類型", ["控制器", "影像裝置", "周邊設備", "機構元件", "電器元件", "其他"])
            c_err = st.text_area("異常原因")
            c_sop = st.text_area("排除步驟")
            c_links = st.text_input("SOP連結 (格式: 名稱|網址;名稱|網址)")
            
            submit_data = st.form_submit_button("上傳至雲端資料庫", use_container_width=True)
            
            if submit_data:
                if c_name and c_id:
                    with st.spinner("同步中..."):
                        df = load_gsheet_data("維修紀錄")
                        new_row = pd.DataFrame([{
                            "編號": str(len(df)+1), 
                            "客戶名稱": c_name, 
                            "機台號碼": c_id,
                            "故障類型": c_type, 
                            "異常原因": c_err, 
                            "排除方式": c_sop,
                            "SOP列表": c_links, 
                            "紀錄日期": str(date.today()),
                            "負責工程師": st.session_state.u_name
                        }])
                        updated_df = pd.concat([df, new_row], ignore_index=True)
                        save_gsheet_data("維修紀錄", updated_df)
                        st.success("✅ 資料已同步至雲端！")
                else:
                    st.error("客戶名稱與機台號碼為必填欄位")