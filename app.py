import streamlit as st
import pandas as pd
from datetime import date
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 建立 Google Sheets 連線 (使用 gspread) ---
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        # 雲端環境：嘗試讀取 Secrets
        if "gspread_creds" in st.secrets:
            creds_info = json.loads(st.secrets["gspread_creds"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        # 本地環境：讀取檔案
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("a96044-35b70c947e1b.json", scope)
            
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        # 這裡會印出你畫面上看到的紅字
        st.error(f"連線初始化失敗：{e}")
        return None

# 初始化試算表物件
client = get_gspread_client()
# 你的試算表網址 (請確保這串網址在你的瀏覽器中可以開啟)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MnXuXbZX8bTtEp5S9s409HyCb9nxPEovy9C2GnpCsT4/edit"

def load_data(worksheet_name):
    if client is None: return pd.DataFrame()
    try:
        # 使用網址開啟試算表，這能避開很多 ID 解析問題
        sh = client.open_by_url(SHEET_URL)
        sheet = sh.worksheet(worksheet_name)
        data = sheet.get_all_records()
        
        if not data:
            # 如果是空表，嘗試讀取標題列避免噴錯
            headers = sheet.row_values(1)
            return pd.DataFrame(columns=headers)
            
        return pd.DataFrame(data).fillna("")
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Google API 錯誤：請確認 Cloud Console 裡的『Google Sheets API』和『Google Drive API』都已點擊『啟用』。")
        st.info(f"詳細錯誤訊息：{e}")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ 找不到名稱為 '{worksheet_name}' 的分頁標籤，請確認 Sheet 底部名稱。")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 讀取時發生非預期錯誤：{type(e).__name__} - {e}")
        return pd.DataFrame()

def save_data(worksheet_name, df):
    if client is None: return False
    try:
        sh = client.open_by_url(SHEET_URL)
        sheet = sh.worksheet(worksheet_name)
        # 清除舊資料並寫入新資料 (包含標題)
        sheet.clear()
        # 將 DataFrame 轉換為 list 格式寫入
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ 資料同步至雲端失敗：{e}")
        return False

# --- 2. 系統設定 ---
st.set_page_config(page_title="大量科技售服雲端系統", layout="wide", page_icon="⚙️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

SHEET_USERS = "users"
SHEET_RECORDS = "records"

# --- 3. 登入邏輯 ---
if not st.session_state.logged_in:
    st.title("🌐 大量科技 - 維修雲端系統")
    with st.container():
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("login_form"):
                st.subheader("🔑 人員登入")
                u = st.text_input("人員帳號")
                p = st.text_input("密碼", type="password")
                if st.form_submit_button("登入系統", use_container_width=True):
                    with st.spinner("正在驗證權限..."):
                        users_df = load_data(SHEET_USERS)
                        if not users_df.empty:
                            # 確保比對時不分型別 (全部轉字串)
                            match = users_df[(users_df['帳號'].astype(str) == str(u)) & 
                                             (users_df['密碼'].astype(str) == str(p))]
                            if not match.empty:
                                st.session_state.logged_in = True
                                st.session_state.u_name = match.iloc[0]['姓名']
                                st.session_state.u_role = match.iloc[0]['職級']
                                st.rerun()
                            else:
                                st.error("❌ 帳號或密碼錯誤")
                        else:
                            st.warning("⚠️ 無法獲取使用者名單，請聯絡系統管理員檢查 API 開關。")

# --- 4. 主功能區 ---
else:
    st.sidebar.title(f"👤 人員：{st.session_state.u_name}")
    st.sidebar.info(f"職級：{st.session_state.u_role}")
    menu = st.sidebar.radio("功能選單", ["🔍 履歷查詢", "📝 新增維修回報"])
    
    if st.sidebar.button("登出系統"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 重點：下面的 if 和 elif 必須縮排在 else 裡面，且垂直對齊 ---
    if menu == "🔍 履歷查詢":
        st.title("⚙️ 維修紀錄檢索")
        q = st.text_input("🔍 輸入關鍵字搜尋 (如：客戶名稱、機台號碼、故障內容)")
        
        with st.spinner("正在檢索雲端資料..."):
            df = load_data(SHEET_RECORDS)
            
        if not df.empty:
            disp_df = df[df.apply(lambda r: r.astype(str).str.contains(q).any(), axis=1)] if q else df
            st.write(f"📊 找到 {len(disp_df)} 筆相關紀錄")
            
            for i, r in disp_df.iterrows():
                with st.expander(f"【{r['客戶名稱']}】{r['機台號碼']} | {r['故障類型']} - {r['紀錄日期']}"):
                    col_a, col_b = st.columns(2)
                    col_a.write(f"**異常原因：**\n{r['異常原因']}")
                    col_b.write(f"**排除方式：**\n{r['排除方式']}")
                    
                    st.divider()
                    st.write("**📄 相關 SOP 連結：**")
                    sop_data = str(r['SOP列表']).strip()
                    if sop_data and sop_data != "nan":
                        links = sop_data.split(";")
                        link_cols = st.columns(2)
                        for idx, item in enumerate(links):
                            item = item.strip()
                            l_name, l_url = item.split("|", 1) if "|" in item else ("開啟 SOP", item)
                            
                            # 修正網址格式，確保手機可以點擊
                            l_url = l_url.strip()
                            if l_url and not (l_url.startswith("http://") or l_url.startswith("https://")):
                                l_url = "https://" + l_url
                            
                            with link_cols[idx % 2]:
                                st.link_button(f"📖 {l_name}", l_url, use_container_width=True)
                    else:
                        st.write("目前無相關連結")

    elif menu == "📝 新增維修回報":
        st.title("📝 新增維修履歷")
        with st.form("add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            c_name = c1.text_input("客戶名稱 *")
            c_site = c2.text_input("廠區")
            c_model = c3.text_input("機型")
            
            c4, c5 = st.columns(2)
            c_id = c4.text_input("機台號碼 *")
            c_type = c5.selectbox("故障類型", ["控制器", "影像裝置", "周邊設備", "機構元件", "電器元件", "其他"])
            
            c_err = st.text_area("異常原因 (詳細描述)")
            c_sop = st.text_area("排除方式 (維修動作紀錄)")
            c_links = st.text_input("SOP 連結 (格式範例: 名稱1|網址;名稱2|網址)")
            
            st.caption("註：* 為必填項目")
            
            if st.form_submit_button("提交並同步至雲端", use_container_width=True):
                if c_name and c_id:
                    with st.spinner("資料上傳中..."):
                        df = load_data(SHEET_RECORDS)
                        new_row = pd.DataFrame([{
                            "編號": str(len(df) + 1), 
                            "客戶名稱": c_name, 
                            "廠區": c_site, 
                            "機型": c_model,
                            "機台號碼": c_id, 
                            "故障類型": c_type, 
                            "異常原因": c_err, 
                            "排除方式": c_sop,
                            "SOP列表": c_links, 
                            "紀錄日期": str(date.today()), 
                            "負責工程師": st.session_state.u_name
                        }])
                        if save_data(SHEET_RECORDS, pd.concat([df, new_row], ignore_index=True)):
                            st.success("🎉 資料同步成功！已更新至雲端資料庫。")
                else:
                    st.error("❌ 提交失敗：『客戶名稱』與『機台號碼』不可為空。")



