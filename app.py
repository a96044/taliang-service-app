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
        st.error(f"連線初始化失敗：{e}")
        return None

# 初始化連線物件
client = get_gspread_client()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MnXuXbZX8bTtEp5S9s409HyCb9nxPEovy9C2GnpCsT4/edit"

def load_data(worksheet_name):
    """讀取資料 (用於登入驗證與查詢)"""
    if client is None: return pd.DataFrame()
    try:
        sh = client.open_by_url(SHEET_URL)
        sheet = sh.worksheet(worksheet_name)
        data = sheet.get_all_records()
        if not data:
            headers = sheet.row_values(1)
            return pd.DataFrame(columns=headers)
        return pd.DataFrame(data).fillna("")
    except Exception as e:
        st.error(f"❌ 讀取資料失敗 [{worksheet_name}]: {e}")
        return pd.DataFrame()

def append_data(worksheet_name, data_list):
    """【核心更新】在末尾追加資料，防止多人同時寫入覆蓋"""
    if client is None: return False
    try:
        sh = client.open_by_url(SHEET_URL)
        sheet = sh.worksheet(worksheet_name)
        # 直接追加一行到最後，這是解決多人衝突的最佳方案
        sheet.append_row(data_list)
        return True
    except Exception as e:
        st.error(f"❌ 資料追加至雲端失敗：{e}")
        return False

# --- 2. 系統設定 ---
st.set_page_config(page_title="大量科技售服雲端系統", layout="wide", page_icon="⚙️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

SHEET_USERS = "users"
SHEET_RECORDS = "records"

# --- 3. 登入邏輯 ---



