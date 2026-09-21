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

# 🔗 接続先GAS（Google Apps Script）のウェブアプリURLを設定
GAS_URL = "https://script.google.com/macros/s/AKfycbzADsde-SbZ_tmc4_p2lM7HjRLiuCqyDfD6v_deho-siZKQOhky8UC_OldMtLTxJ2PG/exec"

# --- データ取得関数 ---
@st.cache_data(ttl=60)
def load_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data)
        else:
            st.error(f"データ取得に失敗しました (ステータスコード: {response.status_code})")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"通信エラーが発生しました: {e}")
        return pd.DataFrame()

# --- サイドバー・操作エリア ---
st.sidebar.header("⚙️ メニュー・操作")
if st.sidebar.button("🔄 データを再読み込み"):
    st.cache_data.clear()
    st.rerun()

# --- メインコンテンツ：データ表示 ---
st.subheader("📋 物件・進行管理一覧")

# データ読み込み実行
df = load_data()

if not df.empty:
    # 検索・フィルター機能（必要に応じて列名を合わせてください）
    if "ステータス" in df.columns:
        statuses = ["すべて"] + list(df["ステータス"].unique())
        selected_status = st.sidebar.selectbox("ステータスで絞り込み", statuses)
        if selected_status != "すべて":
            df = df[df["ステータス"] == selected_status]

    # データテーブルの表示
    st.dataframe(df, use_container_width=True)
else:
    if GAS_URL == "ここに実際のGASのURLを貼り付けてください":
        st.warning("⚠️ スクリプト内の `GAS_URL` に実際のGoogle Apps ScriptのURLを設定してください。")
    else:
        st.info("現在表示できるデータがないか、読み込みを待っています。")