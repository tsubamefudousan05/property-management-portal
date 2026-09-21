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
            return response.json()
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

if raw_data is not None and "data" in raw_data:
    # "data" キーの中身を取り出してDataFrameに変換
    df = pd.DataFrame(raw_data["data"])
    
    if not df.empty:
        # ステータスや担当者などのフィルター機能（必要に応じて）
        if "管理取得担当者" in df.columns:
            staffs = ["すべて"] + list(df["管理取得担当者"].unique())
            selected_staff = st.sidebar.selectbox("管理取得担当者で絞り込み", staffs)
            if selected_staff != "すべて":
                df = df[df["管理取得担当者"] == selected_staff]

        # データテーブルの表示
        st.dataframe(df, use_container_width=True)
    else:
        st.info("データが空です。")
else:
    st.warning("⚠️ 期待したデータ形式で取得できませんでした。")