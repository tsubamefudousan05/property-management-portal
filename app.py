import streamlit as st
import pandas as pd
import requests
import json

# ==========================================
# 🔐 簡易ログイン認証
# ==========================================
def check_password():
    """パスワード認証を行う関数"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("### 🔒 ログイン認証")
    password = st.text_input("パスワードを入力してください", type="password")
    
    if st.button("ログイン"):
        if password == "PM77":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが間違っています。")
    return False

# 認証チェック
if not check_password():
    st.stop()

# ==========================================
# 🏠 メインアプリケーション
# ==========================================
st.set_page_config(page_title="物件管理・進行管理ポータル", layout="wide")

st.title("🏢 物件管理・進行管理ポータル")
st.markdown("---")

# 🔗 接続先GAS（Google Apps Script）のウェブアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzADsde-SbZ_tmc4_p2lM7HjRLiuCqyDfD6v_deho-siZKQOhky8UC_OldMtLTxJ2PG/exec"

# --- データ取得関数 ---
@st.cache_data(ttl=60)
def load_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            st.error(f"データ取得に失敗しました (ステータスコード: {response.status_code})")
            return None
    except Exception as e:
        st.error(f"通信エラーが発生しました: {e}")
        return None

# --- サイドバー・操作エリア ---
st.sidebar.header("⚙️ メニュー・操作")
if st.sidebar.button("🔄 データを再読み込み"):
    st.cache_data.clear()
    st.rerun()

# --- メインコンテンツ：データ表示 ---
st.subheader("📋 物件・進行管理一覧")

# データ読み込み実行
raw_data = load_data()

if raw_data is not None:
    # デバッグ用に取得したデータをそのまま表示（形式を確認するため）
    st.write("取得したデータの中身:", raw_data)
    
    try:
        df = pd.DataFrame(raw_data)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("データが空です。")
    except Exception as e:
        st.warning(f"DataFrameへの変換でエラーが発生しました: {e}")
else:
    st.info("現在表示できるデータがありません。")