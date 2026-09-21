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

# 接続先GAS（Google Apps Script）のURL（※必要に応じてご自身のURLに書き換えてください）
GAS_URL = "YOUR_GAS_WEB_APP_URL_HERE"

# サンプル表示用のデータ読み込みやUI構築処理をここに記述
st.success("認証に成功しました！ポータルシステムへようこそ。")

# データ取得ボタンやテーブル表示のロジック
# （既存の処理をここに繋げてください）