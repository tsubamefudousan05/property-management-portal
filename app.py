from datetime import datetime, date, timedelta
import base64
import json
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="管理替え・進行管理ポータル", layout="wide")

# 🌟 キャッシュを完全にクリアして常に最新データを取得する
st.cache_data.clear()

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

if not check_password():
    st.stop()

# ==========================================
# 🏠 メインアプリケーション
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbzADsde-SbZ_tmc4_p2lM7HjRLiuCqyDfD6v_deho-siZKQOhky8UC_OldMtLTxJ2PG/exec"


def fetch_data(sheet_name="引き継ぎ書"):
  try:
    url = f"{GAS_URL}?sheet={sheet_name}"
    res = requests.get(url)
    return res.json()
  except Exception as e:
    st.error(f"データ取得エラー ({sheet_name}): {e}")
    return {"schema": [], "headers": [], "data": []}


# 🌟 画像ファイルをアップロードしてGoogleドライブのURLを取得するヘルパー関数
def upload_image_to_gas(uploaded_file):
  try:
    bytes_data = uploaded_file.getvalue()
    b64_str = base64.b64encode(bytes_data).decode("utf-8")
    payload = {
        "action": "upload_image",
        "fileData": b64_str,
        "fileName": uploaded_file.name,
        "mimeType": uploaded_file.type
    }
    res = requests.post(GAS_URL, json=payload)
    res_json = res.json()
    if res_json.get("status") == "success":
      return res_json.get("url")
  except Exception as e:
    st.error(f"画像アップロードエラー: {e}")
  return None


# 🌟 タイトルと「パスワードなしでデータを再取得するリロードボタン」を配置
col_title, col_reload = st.columns([5, 1])
with col_title:
    st.title("🏠 管理替え・進行管理ポータル")
with col_reload:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 最新に更新", use_container_width=True, help="パスワードを再入力せずにデータを最新状態に更新します"):
        st.cache_data.clear()
        st.rerun()

# 🌟 必要な3つのモードだけに絞り込み
mode = st.radio(
    "操作モード",
    ["📋 引き継ぎ書・管理", "🏁 管理終了案件", "🔄 オーナーチェンジ案件"],
    horizontal=True,
)


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
  if v_str in ["-", "", "未選択", "nan", "None", "未定", "未"]:
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


# 🌟 表記揺れやスペースに関わらず、安全に物件名を抽出するヘルパー関数
def get_safe_property_name(row):
  for k, v in row.items():
    if "物件" in str(k) and k != "_rowId":
      val = str(v).strip()
      if val and val not in ["nan", "None", "", "未"]:
        return val
  return "（物件名未設定）"


# 🌟 保存確認用のモーダルダイアログ
@st.dialog("📋 変更内容の確認")
def show_confirm_dialog(property_name, selected_row_id, edited_payload, uploaded_files_dict, target_row, sheet_name="引き継ぎ書", is_new=False):
    if is_new:
        st.markdown(f"## ➕ 新規登録：{property_name}")
        st.markdown("以下の内容で**新規データ**を登録します。内容を確認してください。")
    else:
        st.markdown(f"## 🏠 {property_name}")
        st.markdown(f"**対象行番号**: {selected_row_id}")
        st.markdown("以下の内容で変更を保存します。内容を確認してください。")
    st.markdown("---")
    
    # 🌟 アップロードファイルがある場合はGASへ送信してURLに変換
    final_payload = {}
    for k, v in edited_payload.items():
        if k in uploaded_files_dict and uploaded_files_dict[k] is not None:
            with st.spinner(f"「{k}」の写真をアップロード中..."):
                file_url = upload_image_to_gas(uploaded_files_dict[k])
                if file_url:
                    final_payload[k] = file_url
                else:
                    final_payload[k] = v
        else:
            if v is None or str(v).strip() == "":
                final_payload[k] = "未"
            else:
                final_payload[k] = v

    if is_new:
        for k, val in final_payload.items():
            cols = st.columns([2, 4])
            with cols[0]:
                st.markdown(f"**{k}**")
            with cols[1]:
                if "http" in str(val):
                    st.markdown(f"<a href='{val}' target='_blank'>🔗 添付ファイルを開く</a>", unsafe_allow_html=True)
                else:
                    color_code = "#ffeb3b" if val == "未" else "#00bcd4"
                    st.markdown(f"<span style='color: {color_code};'>**{val}**</span>", unsafe_allow_html=True)
            st.markdown("")
    else:
        diff_items = []
        for k, new_v in final_payload.items():
            old_v = str(target_row.get(k, "")).strip()
            if old_v in ["", "-", "未選択", "None", "nan"]:
                old_v = "未"
            if str(new_v) != str(old_v):
                diff_items.append({"title": k, "old": old_v, "new": new_v})

        if diff_items:
            st.markdown("### 🔍 変更される項目")
            for item in diff_items:
                cols = st.columns([2, 3, 3])
                with cols[0]:
                    st.markdown(f"**{item['title']}**")
                with cols[1]:
                    st.markdown(f"変更前: <span style='color: #ff9800;'>{item['old']}</span>", unsafe_allow_html=True)
                with cols[2]:
                    val_display = f"<a href='{item['new']}' target='_blank'>🔗 リンク</a>" if "http" in str(item['new']) else f"**{item['new']}**"
                    st.markdown(f"変更後: <span style='color: #4caf50;'>{val_display}</span>", unsafe_allow_html=True)
                st.markdown("")
        else:
            st.info("変更された項目はありません。")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ キャンセル", use_container_width=True):
            st.rerun()
    with c2:
        action_type = "save" if is_new else "update"
        btn_label = "🚀 この内容で新規登録する" if is_new else "🚀 この内容で保存する"
        primary_btn = st.button(btn_label, type="primary", use_container_width=True)
        if primary_btn:
            payload = {
                "action": action_type,
                "sheet": sheet_name,
                "payload": final_payload,
            }
            if not is_new:
                payload["rowId"] = selected_row_id

            try:
              res = requests.post(GAS_URL, json=payload)
              if res.status_code == 200:
                msg = "正常に新規登録されました！" if is_new else "正常に更新されました！"
                st.success(msg)
                st.rerun()
              else:
                st.error("処理に失敗しました。")
            except Exception as e:
              st.error(f"通信エラー: {e}")


# ==========================================
# 📋 モード1：引き継ぎ書・管理
# ==========================================
if mode == "📋 引き継ぎ書・管理":
  response_data = fetch_data("引き継ぎ書")
  schema = response_data.get("schema", [])
  data = response_data.get("data", [])

  if data:
    filtered_data = []
    for row in data:
      filtered_data.append(row)

    col_selectors, col_table = st.columns([4, 6])

    with col_selectors:
      st.markdown("### 🔍 検索・フィルター選択")
      
      def get_sort_key(row):
        date_val = parse_fixed_date(row.get("集金開始月", ""))
        if date_val:
          return (0, date_val)
        return (1, date.max)

      sorted_filtered_data = sorted(filtered_data, key=get_sort_key)
      
      property_options = ["未選択（物件を選んでください）", "➕ 【新規物件を追加する】"]
      property_map = {}
      for row in sorted_filtered_data:
        p_name = get_safe_property_name(row)
        raw_date = row.get("集金開始月", "")
        parsed_d = parse_fixed_date(raw_date)
        date_str = parsed_d.strftime("%Y/%m/%d") if parsed_d else (str(raw_date) if raw_date else "日付未設定")
        
        label = f"{p_name} （集金開始月: {date_str}）"
        property_options.append(label)
        property_map[label] = row

      selected_prop_label = st.selectbox(
          "🏠 物件を選択（日付順）",
          property_options,
          key="direct_property_select_hiki"
      )

      available_depts = sorted(list(set(s.get("department", "") for s in schema if s.get("department", "") and s.get("department", "") != "総合")))
      dep_options = ["すべて（総合）"] + available_depts

      filter_dep = st.selectbox(
          "📂 部署を選択",
          dep_options,
          key="filter_dep_select_hiki"
      )

    if filter_dep != "すべて（総合）":
      target_schema = [s for s in schema if s.get("department", "") == filter_dep or s.get("department", "") == "総合"]
    else:
      target_schema = schema

    with col_table:
      st.markdown(f"### 📊 対象データ一覧（全 {len(filtered_data)} 件）")

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
      columns_to_show = ["_rowId"] + [t for t in df_display.columns if t != "_rowId"]
      
      seen = set()
      unique_columns_to_show = []
      for c in columns_to_show:
        if c not in seen and c in df_display.columns:
          seen.add(c)
          unique_columns_to_show.append(c)

      df_display_filtered = df_display[unique_columns_to_show]

      st.dataframe(
          df_display_filtered,
          use_container_width=True,
          height=250,
          hide_index=True,
      )

    st.markdown("---")

    if selected_prop_label == "➕ 【新規物件を追加する】":
      st.subheader("➕ 引き継ぎ書：新規物件の追加登録")
      new_save_clicked = st.button("💾 新規データを登録する", type="primary", use_container_width=True, key="new_btn_hiki")

      with st.container(height=600):
        new_payload = {}
        uploaded_files_dict = {}
        grouped_items = {}
        for s in target_schema:
          g = s["group"]
          if g not in grouped_items:
            grouped_items[g] = []
          grouped_items[g].append(s)

        for group_name, items in grouped_items.items():
          st.markdown(f"### 📌 【 {group_name} 】")
          form_cols = st.columns(4)

          for i, s in enumerate(items):
            title = s["title"]
            options = s["options"]
            unique_key = f"new_hiki_{group_name}_{i}_{title}"

            target_col = form_cols[i % 4]
            with target_col:
              label_col, status_col = st.columns([2, 1])
              with label_col:
                st.markdown(f"<span style='color: #ffeb3b; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)
              with status_col:
                status_choice = st.radio(
                    f"状態_{unique_key}",
                    ["未", "済"],
                    index=0,
                    horizontal=True,
                    key=f"status_{unique_key}",
                    label_visibility="collapsed"
                )

              # 📸 写真・画像・添付項目の場合
              if "写真" in title or "画像" in title or "添付" in title:
                if status_choice == "未":
                  new_payload[title] = "未"
                else:
                  uploaded_file = st.file_uploader(
                      f"{title} (ファイル)",
                      type=["jpg", "jpeg", "png", "heic"],
                      key=f"file_{unique_key}",
                      label_visibility="collapsed"
                  )
                  if uploaded_file is not None:
                    uploaded_files_dict[title] = uploaded_file
                    new_payload[title] = uploaded_file.name
                  else:
                    new_payload[title] = "未"

              elif title in ["管理契約開始日", "集金開始月"]:
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
                      placeholder="入力",
                      key=f"txt_{unique_key}",
                      label_visibility="collapsed",
                  )
                  new_payload[title] = typed_val.strip()

          st.markdown("---")

        if new_save_clicked:
          p_name_val = "新規物件"
          for k, v in new_payload.items():
            if "物件" in k and v and v != "未":
              p_name_val = v
              break
          show_confirm_dialog(p_name_val, None, new_payload, uploaded_files_dict, {}, "引き継ぎ書", is_new=True)

    elif selected_prop_label == "未選択（物件を選んでください）":
      st.info("👆 上のセレクトボックスから物件を選択、または「➕ 【新規物件を追加する】」を選択してください。")
    else:
      target_row = property_map[selected_prop_label]
      selected_row_id = target_row["_rowId"]
      property_name = get_safe_property_name(target_row)

      head_col1, head_col3 = st.columns([4, 1])

      with head_col1:
        st.subheader(f"✏️ 選択中：{property_name} （行番号 {selected_row_id}）")

      with head_col3:
        top_save_clicked = st.button(
            "💾 変更を保存", type="primary", use_container_width=True, key="save_hiki"
        )

      form_version_key = f"row_{selected_row_id}_dep_{filter_dep}"

      with st.container(height=600):
        edited_payload = {}
        uploaded_files_dict = {}

        grouped_items = {}
        for s in target_schema:
          g = s["group"]
          if g not in grouped_items:
            grouped_items[g] = []
          grouped_items[g].append(s)

        for group_name, items in grouped_items.items():
          st.markdown(f"### 📌 【 {group_name} 】")
          form_cols = st.columns(4)

          for i, s in enumerate(items):
            title = s["title"]
            raw_val = target_row.get(title, "")
            options = s["options"]
            unique_key = f"{form_version_key}_{group_name}_{i}_{title}"

            target_col = form_cols[i % 4]
            with target_col:
              label_col, status_col = st.columns([2, 1])
              with label_col:
                is_mi_form = str(raw_val).strip() in ["", "-", "未選択", "None", "nan", "未"]
                if is_mi_form:
                  st.markdown(f"<span style='color: #ffeb3b; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)
                else:
                  st.markdown(f"<span style='color: #00bcd4; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)

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

              # 📸 写真・画像・添付項目の場合
              if "写真" in title or "画像" in title or "添付" in title:
                if status_choice == "未":
                  edited_payload[title] = "未"
                else:
                  if raw_val and str(raw_val).startswith("http"):
                    st.markdown(f"<a href='{raw_val}' target='_blank'>🔗 現在のファイルを開く</a>", unsafe_allow_html=True)
                  
                  uploaded_file = st.file_uploader(
                      f"{title} (ファイル入替)",
                      type=["jpg", "jpeg", "png", "heic"],
                      key=f"file_{unique_key}",
                      label_visibility="collapsed"
                  )
                  if uploaded_file is not None:
                    uploaded_files_dict[title] = uploaded_file
                    edited_payload[title] = uploaded_file.name
                  else:
                    edited_payload[title] = raw_val

              elif title in ["管理契約開始日", "集金開始月"]:
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
                      placeholder="入力",
                      key=f"txt_{unique_key}",
                      label_visibility="collapsed",
                  )
                  edited_payload[title] = typed_val.strip()

          st.markdown("---")

        if top_save_clicked:
          show_confirm_dialog(property_name, selected_row_id, edited_payload, uploaded_files_dict, target_row, "引き継ぎ書", is_new=False)
  else:
    st.info("データがありません。")


# ==========================================
# 🏁 モード2：管理終了案件
# ==========================================
elif mode == "🏁 管理終了案件":
  response_data = fetch_data("管理終了")
  schema = response_data.get("schema", [])
  data = response_data.get("data", [])

  def get_kanryo_sort_key(row):
    d = parse_fixed_date(row.get("終了日", "")) or parse_fixed_date(row.get("終了予定日", ""))
    if d:
      return (0, d)
    return (1, date.max)

  sorted_data = sorted(data, key=get_kanryo_sort_key) if data else []
  prop_options = ["未選択（物件を選んでください）", "➕ 【新規物件を追加する】"]
  prop_map = {}

  for row in sorted_data:
    p_name = get_safe_property_name(row)
    end_d = parse_fixed_date(row.get("終了日", ""))
    if not end_d:
      end_d = parse_fixed_date(row.get("終了予定日", ""))
    
    date_str = end_d.strftime("%Y/%m/%d") if end_d else "未定"
    label = f"{p_name} （終了日: {date_str}）"
    prop_options.append(label)
    prop_map[label] = row

  col_selectors, col_table = st.columns([4, 6])

  with col_selectors:
    st.markdown("### 🔍 検索・選択")
    selected_label = st.selectbox(
        "🏠 管理終了物件を選択",
        prop_options,
        key="select_kanryo"
    )

  with col_table:
    st.markdown(f"### 📊 管理終了案件一覧（全 {len(data)} 件）")
    if data:
      display_kanryo_data = []
      for row in data:
        new_row = row.copy()
        for k, v in new_row.items():
          if ("日" in k or "月" in k) and v:
            fixed_date = parse_fixed_date(v)
            if fixed_date:
              new_row[k] = fixed_date.strftime("%Y/%m/%d")
          if k != "_rowId" and (v is None or str(v).strip() in ["", "-", "未選択", "None", "nan"]):
            new_row[k] = "未"
        display_kanryo_data.append(new_row)

      df_kanryo = pd.DataFrame(display_kanryo_data)
      st.dataframe(df_kanryo, use_container_width=True, height=250, hide_index=True)
    else:
      st.info("データがありません。")

  st.markdown("---")

  if selected_label == "➕ 【新規物件を追加する】":
    st.subheader("➕ 管理終了案件：新規物件の追加登録")
    new_save_btn = st.button("💾 新規データを登録する", type="primary", use_container_width=True, key="new_btn_kanryo")

    with st.container(height=600):
      new_payload = {}
      grouped = {}
      for s in schema:
        g = s.get("group", "基本情報")
        if g not in grouped:
          grouped[g] = []
        grouped[g].append(s)

      if not schema and data:
        items = [{"title": k, "options": [], "group": "基本情報"} for k in data[0].keys() if k != "_rowId"]
        grouped = {"基本情報": items}

      for g_name, items in grouped.items():
        st.markdown(f"### 📌 【 {g_name} 】")
        f_cols = st.columns(4)
        for i, s in enumerate(items):
          title = s["title"]
          opts = s.get("options", [])
          u_key = f"new_kanryo_{i}_{title}"

          with f_cols[i % 4]:
            label_col, status_col = st.columns([2, 1])
            with label_col:
              st.markdown(f"<span style='color: #ffeb3b; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)
            with status_col:
              status_choice = st.radio(
                  f"状態_{u_key}",
                  ["未", "済"],
                  index=0,
                  horizontal=True,
                  key=f"status_{u_key}",
                  label_visibility="collapsed"
              )

            if "日" in title or "月" in title:
              if status_choice == "未":
                new_payload[title] = "未定"
              else:
                chosen_d = st.date_input(title, value=date.today(), key=f"date_{u_key}", label_visibility="collapsed")
                new_payload[title] = chosen_d.strftime("%Y/%m/%d")
            elif len(opts) > 0:
              if status_choice == "未":
                new_payload[title] = "未"
              else:
                val = st.selectbox(title, opts, key=f"sel_{u_key}", label_visibility="collapsed")
                new_payload[title] = val
            else:
              if status_choice == "未":
                new_payload[title] = "未"
              else:
                txt = st.text_input(title, placeholder="入力", key=f"txt_{u_key}", label_visibility="collapsed")
                new_payload[title] = txt.strip()
        st.markdown("---")

      if new_save_btn:
        p_name_val = "新規管理終了物件"
        for k, v in new_payload.items():
          if "物件" in k and v and v != "未":
            p_name_val = v
            break
        show_confirm_dialog(p_name_val, None, new_payload, {}, {}, "管理終了", is_new=True)

  elif selected_label != "未選択（物件を選んでください）":
    target_row = prop_map[selected_label]
    row_id = target_row["_rowId"]
    p_name = get_safe_property_name(target_row)

    head_col1, head_col3 = st.columns([4, 1])
    with head_col1:
      st.subheader(f"✏️ 選択中：{p_name} （行番号 {row_id}）")
    with head_col3:
      save_btn = st.button("💾 管理終了データを保存", type="primary", use_container_width=True, key="save_kanryo")

    with st.container(height=600):
      edited_payload = {}
      grouped = {}
      for s in schema:
        g = s.get("group", "基本情報")
        if g not in grouped:
          grouped[g] = []
        grouped[g].append(s)

      if not schema:
        items = [{"title": k, "options": [], "group": "基本情報"} for k in target_row.keys() if k != "_rowId"]
        grouped = {"基本情報": items}

      for g_name, items in grouped.items():
        st.markdown(f"### 📌 【 {g_name} 】")
        f_cols = st.columns(4)
        for i, s in enumerate(items):
          title = s["title"]
          raw_val = target_row.get(title, "")
          opts = s.get("options", [])
          u_key = f"kanryo_{row_id}_{i}_{title}"

          with f_cols[i % 4]:
            label_col, status_col = st.columns([2, 1])
            with label_col:
              is_mi_form = str(raw_val).strip() in ["", "-", "未選択", "None", "nan", "未", "未定"]
              if is_mi_form:
                st.markdown(f"<span style='color: #ffeb3b; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)
              else:
                st.markdown(f"<span style='color: #00bcd4; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)

            with status_col:
              current_status = "済" if str(raw_val).strip() not in ["", "-", "未選択", "None", "nan", "未", "未定"] else "未"
              status_choice = st.radio(
                  f"状態_{u_key}",
                  ["未", "済"],
                  index=0 if current_status == "未" else 1,
                  horizontal=True,
                  key=f"status_{u_key}",
                  label_visibility="collapsed"
              )

            if "日" in title or "月" in title:
              if status_choice == "未":
                edited_payload[title] = "未定"
              else:
                parsed_d = parse_fixed_date(raw_val)
                d_val = parsed_d if parsed_d else date.today()
                chosen_d = st.date_input(title, value=d_val, key=f"date_{u_key}", label_visibility="collapsed")
                edited_payload[title] = chosen_d.strftime("%Y/%m/%d")
            elif len(opts) > 0:
              if status_choice == "未":
                edited_payload[title] = "未"
              else:
                cur = str(raw_val).strip()
                idx = opts.index(cur) if cur in opts else 0
                val = st.selectbox(title, opts, index=idx, key=f"sel_{u_key}", label_visibility="collapsed")
                edited_payload[title] = val
            else:
              if status_choice == "未":
                edited_payload[title] = "未"
              else:
                txt = st.text_input(title, value=str(raw_val) if raw_val and str(raw_val)!="nan" else "", key=f"txt_{u_key}", label_visibility="collapsed")
                edited_payload[title] = txt.strip()
        st.markdown("---")

      if save_btn:
        show_confirm_dialog(p_name, row_id, edited_payload, {}, target_row, "管理終了", is_new=False)
  else:
    st.info("👆 上のセレクトボックスから管理終了物件を選択、または新規追加を選択してください。")


# ==========================================
# 🔄 モード3：オーナーチェンジ案件
# ==========================================
elif mode == "🔄 オーナーチェンジ案件":
  response_data = fetch_data("オーナーチェンジ")
  schema = response_data.get("schema", [])
  data = response_data.get("data", [])

  def get_oc_sort_key(row):
    d = parse_fixed_date(row.get("決済日", ""))
    if d:
      return (0, d)
    return (1, date.max)

  sorted_data = sorted(data, key=get_oc_sort_key) if data else []
  prop_options = ["未選択（物件を選んでください）", "➕ 【新規物件を追加する】"]
  prop_map = {}

  for row in sorted_data:
    p_name = get_safe_property_name(row)
    pay_d = parse_fixed_date(row.get("決済日", ""))
    date_str = pay_d.strftime("%Y/%m/%d") if pay_d else "未定"
    
    label = f"{p_name} （決済日: {date_str}）"
    prop_options.append(label)
    prop_map[label] = row

  col_selectors, col_table = st.columns([4, 6])

  with col_selectors:
    st.markdown("### 🔍 検索・選択")
    selected_label = st.selectbox(
        "🏠 オーナーチェンジ物件を選択",
        prop_options,
        key="select_oc"
    )

  with col_table:
    st.markdown(f"### 📊 オーナーチェンジ案件一覧（全 {len(data)} 件）")
    if data:
      display_oc_data = []
      for row in data:
        new_row = row.copy()
        for k, v in new_row.items():
          if ("日" in k or "月" in k) and v:
            fixed_date = parse_fixed_date(v)
            if fixed_date:
              new_row[k] = fixed_date.strftime("%Y/%m/%d")
          if k != "_rowId" and (v is None or str(v).strip() in ["", "-", "未選択", "None", "nan"]):
            new_row[k] = "未"
        display_oc_data.append(new_row)

      df_oc = pd.DataFrame(display_oc_data)
      st.dataframe(df_oc, use_container_width=True, height=250, hide_index=True)
    else:
      st.info("データがありません。")

  st.markdown("---")

  if selected_label == "➕ 【新規物件を追加する】":
    st.subheader("➕ オーナーチェンジ案件：新規物件の追加登録")
    new_save_btn = st.button("💾 新規データを登録する", type="primary", use_container_width=True, key="new_btn_oc")

    with st.container(height=600):
      new_payload = {}
      grouped = {}
      for s in schema:
        g = s.get("group", "基本情報")
        if g not in grouped:
          grouped[g] = []
        grouped[g].append(s)

      if not schema and data:
        items = [{"title": k, "options": [], "group": "基本情報"} for k in data[0].keys() if k != "_rowId"]
        grouped = {"基本情報": items}

      for g_name, items in grouped.items():
        st.markdown(f"### 📌 【 {g_name} 】")
        f_cols = st.columns(4)
        for i, s in enumerate(items):
          title = s["title"]
          opts = s.get("options", [])
          u_key = f"new_oc_{i}_{title}"

          with f_cols[i % 4]:
            label_col, status_col = st.columns([2, 1])
            with label_col:
              st.markdown(f"<span style='color: #ffeb3b; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)
            with status_col:
              status_choice = st.radio(
                  f"状態_{u_key}",
                  ["未", "済"],
                  index=0,
                  horizontal=True,
                  key=f"status_{u_key}",
                  label_visibility="collapsed"
              )

            if "日" in title or "月" in title:
              if status_choice == "未":
                new_payload[title] = "未定"
              else:
                chosen_d = st.date_input(title, value=date.today(), key=f"date_{u_key}", label_visibility="collapsed")
                new_payload[title] = chosen_d.strftime("%Y/%m/%d")
            elif len(opts) > 0:
              if status_choice == "未":
                new_payload[title] = "未"
              else:
                val = st.selectbox(title, opts, key=f"sel_{u_key}", label_visibility="collapsed")
                new_payload[title] = val
            else:
              if status_choice == "未":
                new_payload[title] = "未"
              else:
                txt = st.text_input(title, placeholder="入力", key=f"txt_{u_key}", label_visibility="collapsed")
                new_payload[title] = txt.strip()
        st.markdown("---")

      if new_save_btn:
        p_name_val = "新規オーナーチェンジ物件"
        for k, v in new_payload.items():
          if "物件" in k and v and v != "未":
            p_name_val = v
            break
        show_confirm_dialog(p_name_val, None, new_payload, {}, {}, "オーナーチェンジ", is_new=True)

  elif selected_label != "未選択（物件を選んでください）":
    target_row = prop_map[selected_label]
    row_id = target_row["_rowId"]
    p_name = get_safe_property_name(target_row)

    head_col1, head_col3 = st.columns([4, 1])
    with head_col1:
      st.subheader(f"✏️ 選択中：{p_name} （行番号 {row_id}）")
    with head_col3:
      save_btn = st.button("💾 オーナーチェンジデータを保存", type="primary", use_container_width=True, key="save_oc")

    with st.container(height=600):
      edited_payload = {}
      grouped = {}
      for s in schema:
        g = s.get("group", "基本情報")
        if g not in grouped:
          grouped[g] = []
        grouped[g].append(s)

      if not schema:
        items = [{"title": k, "options": [], "group": "基本情報"} for k in target_row.keys() if k != "_rowId"]
        grouped = {"基本情報": items}

      for g_name, items in grouped.items():
        st.markdown(f"### 📌 【 {g_name} 】")
        f_cols = st.columns(4)
        for i, s in enumerate(items):
          title = s["title"]
          raw_val = target_row.get(title, "")
          opts = s.get("options", [])
          u_key = f"oc_{row_id}_{i}_{title}"

          with f_cols[i % 4]:
            label_col, status_col = st.columns([2, 1])
            with label_col:
              is_mi_form = str(raw_val).strip() in ["", "-", "未選択", "None", "nan", "未", "未定"]
              if is_mi_form:
                st.markdown(f"<span style='color: #ffeb3b; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)
              else:
                st.markdown(f"<span style='color: #00bcd4; font-size: 0.9em;'>**{title}**</span>", unsafe_allow_html=True)

            with status_col:
              current_status = "済" if str(raw_val).strip() not in ["", "-", "未選択", "None", "nan", "未", "未定"] else "未"
              status_choice = st.radio(
                  f"状態_{u_key}",
                  ["未", "済"],
                  index=0 if current_status == "未" else 1,
                  horizontal=True,
                  key=f"status_{u_key}",
                  label_visibility="collapsed"
              )

            if "日" in title or "月" in title:
              if status_choice == "未":
                edited_payload[title] = "未定"
              else:
                parsed_d = parse_fixed_date(raw_val)
                d_val = parsed_d if parsed_d else date.today()
                chosen_d = st.date_input(title, value=d_val, key=f"date_{u_key}", label_visibility="collapsed")
                edited_payload[title] = chosen_d.strftime("%Y/%m/%d")
            elif len(opts) > 0:
              if status_choice == "未":
                edited_payload[title] = "未"
              else:
                cur = str(raw_val).strip()
                idx = opts.index(cur) if cur in opts else 0
                val = st.selectbox(title, opts, index=idx, key=f"sel_{u_key}", label_visibility="collapsed")
                edited_payload[title] = val
            else:
              if status_choice == "未":
                edited_payload[title] = "未"
              else:
                txt = st.text_input(title, value=str(raw_val) if raw_val and str(raw_val)!="nan" else "", key=f"txt_{u_key}", label_visibility="collapsed")
                edited_payload[title] = txt.strip()
        st.markdown("---")

      if save_btn:
        show_confirm_dialog(p_name, row_id, edited_payload, {}, target_row, "オーナーチェンジ", is_new=False)
  else:
    st.info("👆 上のセレクトボックスからオーナーチェンジ物件を選択、または新規追加を選択してください。")