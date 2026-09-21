from datetime import datetime, date, timedelta
import json
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="管理替え・進行管理ポータル", layout="wide")

# ==========================================
# 🔐 簡易ログイン認証
# ==========================================
def check_password():
    """パスワード認証を行う関数"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown("### 🔒 ログイン認証")
        password = st.text_input("パスワードを入力してください", type="password")
        
        if st.button("ログイン", use_container_width=True):
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
GAS_URL = "https://script.google.com/macros/s/AKfycbzADsde-SbZ_tmc4_p2lM7HjRLiuCqyDfD6v_deho-siZKQOhky8UC_OldMtLTxJ2PG/exec"


@st.cache_data(ttl=300)
def fetch_data():
  try:
    res = requests.get(GAS_URL)
    return res.json()
  except Exception as e:
    st.error(f"データ取得エラー: {e}")
    return {"schema": [], "headers": [], "data": []}


response_data = fetch_data()
schema = response_data.get("schema", [])
headers = response_data.get("headers", [])
data = response_data.get("data", [])

st.title("🏠 管理替え・進行管理ポータル")

# 操作モードの切替
mode = st.radio(
    "操作モード",
    ["📋 一覧表示・管理", "➕ 新規物件追加", "⚙️ 部署別・進捗ステータスビュー"],
    horizontal=True,
)


# 日付を安全にパースする関数
def parse_fixed_date(val):
  if val is None:
    return None

  if isinstance(val, (int, float)):
    if val < 10000:
      return None
    try:
      base_date = date(1899, 12, 30)
      return base_date + timedelta(days=int(val))
    except Exception:
      pass

  v_str = str(val).strip()
  if v_str in ["-", "", "未選択", "nan", "None"]:
    return None

  if v_str.isdigit():
    val_int = int(v_str)
    if val_int < 10000:
      return None
    try:
      base_date = date(1899, 12, 30)
      return base_date + timedelta(days=val_int)
    except Exception:
      pass

  try:
    if "T" in v_str:
      clean_iso = v_str.replace("Z", "")
      dt = datetime.fromisoformat(clean_iso)
      dt = dt + timedelta(hours=9)
      return dt.date()

    v_str = v_str.replace("-", "/")
    parts = v_str.split("/")
    if len(parts) == 3:
      return date(int(parts[0]), int(parts[1]), int(parts[2]))
  except Exception:
    pass
  return None


if mode == "📋 一覧表示・管理":
  if data:
    st.markdown("### 🔍 部署フィルター選択")
    
    available_depts = sorted(list(set(s.get("department", "") for s in schema if s.get("department") and s.get("department") != "総合")))
    dep_options = ["すべて（総合）"] + available_depts

    filter_dep = st.selectbox(
        "📂 表示する部署を選択",
        dep_options,
        key="filter_dep_select"
    )

    filtered_data = []
    for row in data:
      filtered_data.append(row)

    if filtered_data:
      col_list, col_form = st.columns([3, 7])

      if filter_dep == "すべて（総合）":
        target_schema = schema
      else:
        target_schema = [s for s in schema if s.get("department") == filter_dep or s.get("department") == "総合"]

      with col_list:
        st.subheader(f"📊 対象データ一覧（全 {len(filtered_data)} 件）")

        display_data = []
        for row in filtered_data:
          new_row = row.copy()
          for k, v in new_row.items():
            if k in ["管理契約開始日", "集金開始月"] and v:
              fixed_date = parse_fixed_date(v)
              if fixed_date:
                new_row[k] = fixed_date.strftime("%Y/%m/%d")
            if k != "_rowId" and (v is None or str(v).strip() in ["", "-", "未選択", "None", "nan"]):
              new_row[k] = "未"
          display_data.append(new_row)

        df_display = pd.DataFrame(display_data)

        valid_titles = [s["title"] for s in target_schema]
        columns_to_show = ["_rowId", "物件名称"] + [t for t in valid_titles if t != "物件名称" and t in df_display.columns]
        existing_cols = [c for c in columns_to_show if c in df_display.columns]
        df_display_filtered = df_display[existing_cols]

        # 🌟 エラーの起きる .style を廃止し、純粋で高速な dataframe 表示に切り替え
        event = st.dataframe(
            df_display_filtered,
            use_container_width=True,
            height=580,
            selection_mode="single-row",
            on_select="rerun",
            key="data_table_selection",
        )

      if "active_index" not in st.session_state:
        st.session_state.active_index = 0

      selected_rows = []
      if event and hasattr(event, "selection") and event.selection:
        if hasattr(event.selection, "rows"):
          selected_rows = event.selection.rows
        elif isinstance(event.selection, dict):
          selected_rows = event.selection.get("rows", [])

      with col_form:
        head_col1, head_col2, head_col3 = st.columns([2, 1, 1])

        if st.session_state.active_index >= len(filtered_data):
          st.session_state.active_index = 0
        target_row = filtered_data[st.session_state.active_index]
        selected_row_id = target_row["_rowId"]

        property_name = str(target_row.get("物件名称", "")).strip()
        if not property_name:
          property_name = "（物件名未設定）"

        with head_col1:
          st.subheader(f"✏️ 選択中：{property_name} （行番号 {selected_row_id}）")

        with head_col2:
          load_clicked = st.button("📥 選択行を読込", use_container_width=True)
          if load_clicked and selected_rows:
            st.session_state.active_index = selected_rows[0]
            st.rerun()

        with head_col3:
          top_save_clicked = st.button(
              "💾 変更を保存", type="primary", use_container_width=True
          )

        form_version_key = f"row_{selected_row_id}_dep_{filter_dep}"

        with st.container(height=500):
          edited_payload = {}

          grouped_items = {}
          for s in target_schema:
            g = s["group"]
            if g not in grouped_items:
              grouped_items[g] = []
            grouped_items[g].append(s)

          for group_name, items in grouped_items.items():
            st.markdown(f"### 📌 【 {group_name} 】")
            form_cols = st.columns(2)

            for i, s in enumerate(items):
              title = s["title"]
              raw_val = target_row.get(title, "")
              options = s["options"]
              unique_key = f"{form_version_key}_{group_name}_{i}_{title}"

              target_col = form_cols[i % 2]
              with target_col:
                label_col, status_col = st.columns([2, 1])
                with label_col:
                  is_mi_form = str(raw_val).strip() in ["", "-", "未選択", "None", "nan", "未"]
                  if is_mi_form:
                    st.markdown(f"<span style='color: #ffeb3b;'>**{title}**</span>", unsafe_allow_html=True)
                  else:
                    st.markdown(f"**{title}**")

                with status_col:
                  current_status = "済" if str(raw_val).strip() not in ["", "-", "未選択", "None", "nan", "未"] else "未"
                  status_choice = st.radio(
                      f"状態_{unique_key}",
                      ["未", "済"],
                      index=0 if current_status == "未" else 1,
                      horizontal=True,
                      key=f"status_{unique_key}",
                      label_visibility="collapsed"
                  )

                if title in ["管理契約開始日", "集金開始月"]:
                  if status_choice == "未":
                    edited_payload[title] = "未"
                  else:
                    parsed_d = parse_fixed_date(raw_val)
                    d_default = parsed_d if parsed_d else date.today()
                    chosen_date = st.date_input(
                        f"{title} (日付)",
                        value=d_default,
                        key=f"date_{unique_key}",
                        label_visibility="collapsed",
                    )
                    edited_payload[title] = chosen_date.strftime("%Y/%m/%d")

                elif len(options) > 0:
                  if status_choice == "未":
                    edited_payload[title] = "未"
                  else:
                    current_val = str(raw_val).strip()
                    if current_val in ["-", "", "未選択", "未"]:
                      current_val = options[0]

                    try:
                      default_idx = options.index(current_val)
                    except ValueError:
                      default_idx = 0

                    chosen_radio = st.radio(
                        f"{title} (選択)",
                        options,
                        index=default_idx,
                        key=f"rad_{unique_key}",
                        horizontal=True,
                        label_visibility="collapsed",
                    )
                    edited_payload[title] = chosen_radio

                else:
                  if status_choice == "未":
                    edited_payload[title] = "未"
                  else:
                    typed_val = st.text_input(
                        f"{title} (自由記述)",
                        value=str(raw_val).strip() if raw_val and str(raw_val) != "未" else "",
                        placeholder="直接入力する場合ここに記載",
                        key=f"txt_{unique_key}",
                        label_visibility="collapsed",
                    )
                    edited_payload[title] = typed_val.strip()

            st.markdown("---")

          if top_save_clicked:
            payload = {
                "action": "update",
                "rowId": selected_row_id,
                "payload": edited_payload,
            }
            try:
              res = requests.post(GAS_URL, json=payload)
              if res.status_code == 200:
                st.success("正常に更新されました！")
                st.cache_data.clear()
                st.rerun()
              else:
                st.error("更新に失敗しました。")
            except Exception as e:
              st.error(f"通信エラー: {e}")
    else:
      st.info("条件に一致する物件はありません。")
  else:
    st.info("現在蓄積されているデータはありません。「新規物件追加」からデータを登録してください。")

elif mode == "➕ 新規物件追加":
  st.subheader("➕ 新規物件の追加登録")

  available_depts_add = sorted(list(set(s.get("department", "") for s in schema if s.get("department") and s.get("department") != "総合")))
  add_dep_options = available_depts_add + ["総合"] if available_depts_add else ["総合"]

  add_dep = st.radio(
      "登録する担当課ビューを切り替え",
      add_dep_options,
      horizontal=True,
      key="add_dep_radio",
  )

  target_schema = [
      s for s in schema if s.get("department") == add_dep or s.get("department") == "総合"
  ]

  new_save_clicked = st.button(
      "💾 新規データを登録する", type="primary", use_container_width=True
  )

  with st.container(height=500):
    new_payload = {}
    grouped_items = {}
    for s in target_schema:
      g = s["group"]
      if g not in grouped_items:
        grouped_items[g] = []
      grouped_items[g].append(s)

    for group_name, items in grouped_items.items():
      st.markdown(f"### 📌 【 {group_name} 】")
      cols = st.columns(2)

      for i, s in enumerate(items):
        title = s["title"]
        options = s["options"]
        unique_key = f"add_{add_dep}_{group_name}_{i}_{title}"

        target_col = cols[i % 2]
        with target_col:
          label_col, status_col = st.columns([2, 1])
          with label_col:
            st.markdown(f"**{title}**")
          with status_col:
            status_choice = st.radio(
                f"状態_add_{unique_key}",
                ["未", "済"],
                index=1,
                horizontal=True,
                key=f"status_add_{unique_key}",
                label_visibility="collapsed"
            )

          if title in ["管理契約開始日", "集金開始月"]:
            if status_choice == "未":
              new_payload[title] = "未"
            else:
              chosen_date = st.date_input(
                  f"{title} (日付)",
                  value=date.today(),
                  key=f"date_{unique_key}",
                  label_visibility="collapsed",
              )
              new_payload[title] = chosen_date.strftime("%Y/%m/%d")
          elif len(options) > 0:
            if status_choice == "未":
              new_payload[title] = "未"
            else:
              default_idx = options.index("未選択") if "未選択" in options else 0
              chosen_radio = st.radio(
                  f"{title} (選択)",
                  options,
                  index=default_idx,
                  key=f"rad_{unique_key}",
                  horizontal=True,
                  label_visibility="collapsed",
                )
              new_payload[title] = chosen_radio
          else:
            if status_choice == "未":
              new_payload[title] = "未"
            else:
              typed_val = st.text_input(
                  f"{title} (自由記述)",
                  placeholder="直接入力する場合ここに記載",
                  key=f"txt_{unique_key}",
                  label_visibility="collapsed",
              )
              new_payload[title] = typed_val.strip()

      st.markdown("---")

    if new_save_clicked:
      payload = {"action": "save", "payload": new_payload}
      try:
        res = requests.post(GAS_URL, json=payload)
        if res.status_code == 200:
          st.success("正常に新規登録されました！")
          st.cache_data.clear()
          st.rerun()
        else:
          st.error("登録に失敗しました。")
      except Exception as e:
        st.error(f"通信エラー: {e}")

elif mode == "⚙️ 部署別・進捗ステータスビュー":
  st.subheader("⚙️ 部署別・進捗ステータス確認モード")
  st.info("※「📋 一覧表示・管理」タブ側のフィルター機能に統合されました。")