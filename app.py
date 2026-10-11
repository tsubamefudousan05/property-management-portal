import base64
from datetime import date, datetime, timedelta
import json
import pandas as pd
import requests
import streamlit as st

# ==========================================
# ⚙️ ページ設定と初期化
# ==========================================
st.set_page_config(page_title="管理替え・進行管理ポータル", layout="wide")
st.cache_data.clear()

GAS_URL = "https://script.google.com/macros/s/AKfycbzADsde-SbZ_tmc4_p2lM7HjRLiuCqyDfD6v_deho-siZKQOhky8UC_OldMtLTxJ2PG/exec"


# ==========================================
# 🔐 簡易ログイン認証
# ==========================================
def check_password():
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
# 🛠️ 共通ヘルパー関数
# ==========================================
def fetch_data(sheet_name="引き継ぎ書"):
  try:
    url = f"{GAS_URL}?sheet={sheet_name}"
    res = requests.get(url)
    return res.json()
  except Exception as e:
    st.error(f"データ取得エラー ({sheet_name}): {e}")
    return {"schema": [], "headers": [], "data": []}


def upload_image_to_gas(uploaded_file):
  try:
    bytes_data = uploaded_file.getvalue()
    b64_str = base64.b64encode(bytes_data).decode("utf-8")
    payload = {
        "action": "upload_image",
        "fileData": b64_str,
        "fileName": uploaded_file.name,
        "mimeType": uploaded_file.type,
    }
    res = requests.post(GAS_URL, json=payload)
    res_json = res.json()
    if res_json.get("status") == "success":
      return res_json.get("url")
  except Exception as e:
    st.error(f"画像アップロードエラー: {e}")
  return None


def parse_fixed_date(val):
  if val is None:
    return None
  v_str = str(val).strip()
  if v_str in ["", "-", "未選択", "None", "nan", "未定", "未"]:
    return None
  if isinstance(val, (int, float)) or v_str.replace(".", "", 1).isdigit():
    try:
      val_float = float(v_str)
      if val_float > 10000:
        return date(1899, 12, 30) + timedelta(days=int(val_float))
    except Exception:
      pass
  try:
    if "T" in v_str:
      dt = datetime.fromisoformat(v_str.replace("Z", ""))
      return (dt + timedelta(hours=9)).date()
    parts = v_str.replace("-", "/").split("/")
    if len(parts) == 3:
      return date(int(parts[0]), int(parts[1]), int(parts[2]))
  except Exception:
    pass
  return None


def get_safe_property_name(row):
  for k, v in row.items():
    if "物件" in str(k) and k != "_rowId":
      val = str(v).strip()
      if val and val not in ["nan", "None", "", "未"]:
        return val
  return "（物件名未設定）"


# ==========================================
# 💾 データ保存用ダイアログ
# ==========================================
@st.dialog("📋 変更内容の確認")
def show_confirm_dialog(
    property_name,
    selected_row_id,
    edited_payload,
    uploaded_files_dict,
    target_row,
    sheet_name,
    is_new=False,
):
  if is_new:
    st.markdown(f"## ➕ 新規登録：{property_name}")
    st.markdown(
        "以下の内容で**新規データ**を登録します。内容を確認してください。"
    )
  else:
    st.markdown(f"## 🏠 {property_name}")
    st.markdown(f"**対象行番号**: {selected_row_id}")
    st.markdown("以下の内容で変更を保存します。内容を確認してください。")
  st.markdown("---")

  final_payload = {}
  for k, v in edited_payload.items():
    if k in uploaded_files_dict and uploaded_files_dict[k] is not None:
      with st.spinner(f"「{k}」の写真をアップロード中..."):
        file_url = upload_image_to_gas(uploaded_files_dict[k])
        final_payload[k] = file_url if file_url else v
    else:
      final_payload[k] = "未" if (v is None or str(v).strip() == "") else v

  if is_new:
    for k, val in final_payload.items():
      cols = st.columns([2, 4])
      with cols[0]:
        st.markdown(f"**{k}**")
      with cols[1]:
        if "http" in str(val):
          st.markdown(
              f"<a href='{val}' target='_blank'>🔗 添付ファイルを開く</a>",
              unsafe_allow_html=True,
          )
        else:
          color_code = "#ffeb3b" if val == "未" else "#00bcd4"
          st.markdown(
              f"<span style='color: {color_code};'>**{val}**</span>",
              unsafe_allow_html=True,
          )
      st.markdown("")
  else:
    diff_items = [
        {"title": k, "old": str(target_row.get(k, "未")).strip(), "new": new_v}
        for k, new_v in final_payload.items()
        if str(new_v) != str(target_row.get(k, "未")).strip()
    ]

    if diff_items:
      st.markdown("### 🔍 変更される項目")
      for item in diff_items:
        old_v = (
            "未"
            if item["old"] in ["", "-", "未選択", "None", "nan"]
            else item["old"]
        )
        cols = st.columns([2, 3, 3])
        with cols[0]:
          st.markdown(f"**{item['title']}**")
        with cols[1]:
          st.markdown(
              f"変更前: <span style='color: #ff9800;'>{old_v}</span>",
              unsafe_allow_html=True,
          )
        with cols[2]:
          val_display = (
              f"<a href='{item['new']}' target='_blank'>🔗 リンク</a>"
              if "http" in str(item["new"])
              else f"**{item['new']}**"
          )
          st.markdown(
              f"変更後: <span style='color: #4caf50;'>{val_display}</span>",
              unsafe_allow_html=True,
          )
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
    btn_label = "🚀 新規登録する" if is_new else "🚀 保存する"
    if st.button(btn_label, type="primary", use_container_width=True):
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
          st.success("正常に処理されました！")
          st.rerun()
        else:
          st.error("処理に失敗しました。")
      except Exception as e:
        st.error(f"通信エラー: {e}")


# ==========================================
# 🏠 ヘッダー・操作モード設定
# ==========================================
col_title, col_reload = st.columns([5, 1])
with col_title:
  st.title("🏠 管理替え・進行管理ポータル")
with col_reload:
  st.markdown("<br>", unsafe_allow_html=True)
  if st.button(
      "🔄 最新に更新",
      use_container_width=True,
      help="データを最新状態に更新します",
  ):
    st.cache_data.clear()
    st.rerun()

mode = st.radio(
    "操作モード",
    ["📋 引き継ぎ書・管理", "🏁 管理終了案件", "🔄 オーナーチェンジ案件"],
    horizontal=True,
)

mode_config = {
    "📋 引き継ぎ書・管理": {"sheet": "引き継ぎ書", "date_keys": ["集金開始月"]},
    "🏁 管理終了案件": {
        "sheet": "管理終了",
        "date_keys": ["終了日", "終了予定日"],
    },
    "🔄 オーナーチェンジ案件": {
        "sheet": "オーナーチェンジ",
        "date_keys": ["決済日"],
    },
}

target_sheet = mode_config[mode]["sheet"]
date_keys = mode_config[mode]["date_keys"]

response_data = fetch_data(target_sheet)
schema = response_data.get("schema", [])
data = response_data.get("data", [])

if not data and not schema:
  st.info("データがありません。")
  st.stop()


def get_sort_key(row):
  for key in date_keys:
    d = parse_fixed_date(row.get(key, ""))
    if d:
      return (0, d)
  return (1, date.max)


sorted_data = sorted(data, key=get_sort_key)

# ==========================================
# 📐 メインレイアウト：左右分割（左側: 4.5 / 右側: 5.5）
# ==========================================
left_col, right_col = st.columns([4.5, 5.5], gap="large")

# ------------------------------------------
# 👈 左側：上部（検索・フィルター）＋ 下部（対象データ一覧）
# ------------------------------------------
with left_col:
  st.markdown("### 🔍 検索・フィルター選択")

  property_options = ["未選択（物件を選んでください）", "➕ 【新規物件を追加する】"]
  property_map = {}

  for row in sorted_data:
    p_name = get_safe_property_name(row)
    display_date_str = "日付未設定"
    for key in date_keys:
      d = parse_fixed_date(row.get(key, ""))
      if d:
        display_date_str = d.strftime("%Y/%m/%d")
        break
    label = f"{p_name} （{date_keys[0]}: {display_date_str}）"
    property_options.append(label)
    property_map[label] = row

  selected_prop_label = st.selectbox(
      "🏠 物件を選択（日付順）", property_options, key="select_prop"
  )

  available_depts = sorted(
      list(
          set(
              str(s.get("department", "")).strip()
              for s in schema
              if s.get("department") and str(s.get("department")) != "総合"
          )
      )
  )
  if available_depts:
    filter_dep = st.selectbox(
        "📂 部署を選択", ["すべて（総合）"] + available_depts, key="select_dep"
    )
  else:
    filter_dep = "すべて（総合）"

  # スキーマの絞り込み
  target_schema = [
      s
      for s in schema
      if filter_dep == "すべて（総合）"
      or s.get("department", "") in [filter_dep, "総合"]
  ]
  valid_titles = [s["title"] for s in target_schema]

  st.markdown("---")

  # 左側下部：対象データ一覧
  st.markdown(f"### 📊 対象データ一覧（全 {len(data)} 件）")
  if data:
    display_data = []
    for row in data:
      new_row = row.copy()
      for k, v in new_row.items():
        if ("日" in k or "月" in k) and v:
          fixed_date = parse_fixed_date(v)
          if fixed_date:
            new_row[k] = fixed_date.strftime("%Y/%m/%d")
        if k != "_rowId" and (
            v is None or str(v).strip() in ["", "-", "未選択", "None", "nan"]
        ):
          new_row[k] = "未"
      display_data.append(new_row)

    df_display = pd.DataFrame(display_data)
    columns_to_show = ["_rowId"] + [
        c for c in df_display.columns if c in valid_titles and c != "_rowId"
    ]
    st.dataframe(
        df_display[columns_to_show],
        use_container_width=True,
        height=450,
        hide_index=True,
    )

# ------------------------------------------
# 👉 右側：入力・編集フォーム
# ------------------------------------------
with right_col:
  if selected_prop_label == "未選択（物件を選んでください）":
    st.info("👈 左側のセレクトボックスから物件を選択してください。")
  else:
    is_new = selected_prop_label == "➕ 【新規物件を追加する】"
    target_row = {} if is_new else property_map[selected_prop_label]
    selected_row_id = None if is_new else target_row.get("_rowId")
    property_name = "新規物件" if is_new else get_safe_property_name(target_row)

    head_col1, head_col2 = st.columns([3.5, 2.5])
    with head_col1:
      if is_new:
        st.subheader(f"➕ {target_sheet}：新規登録")
      else:
        st.subheader(f"✏️ 選択中：{property_name}")
        st.caption(f"対象行番号: {selected_row_id}")

    with head_col2:
      action_btn_label = "💾 新規登録" if is_new else "💾 変更を保存"
      save_clicked = st.button(
          action_btn_label, type="primary", use_container_width=True
      )

    with st.container(height=650):
      edited_payload = {}
      uploaded_files_dict = {}

      grouped_items = {}
      for s in target_schema:
        g = s.get("group", "基本情報")
        grouped_items.setdefault(g, []).append(s)

      for group_name, items in grouped_items.items():
        st.markdown(f"### 📌 【 {group_name} 】")
        # 右カラム幅に合わせて2列配置
        form_cols = st.columns(2)

        for i, s in enumerate(items):
          title = s["title"]
          options = s.get("options", [])
          raw_val = target_row.get(title, "") if not is_new else ""

          unique_key = (
              f"{target_sheet}_{'new' if is_new else str(selected_row_id)}_{group_name}_{i}_{title}"
          )

          with form_cols[i % 2]:
            label_col, status_col = st.columns([2.5, 1.5])

            is_mi_form = (
                True
                if is_new
                else (
                    str(raw_val).strip()
                    in ["", "-", "未選択", "None", "nan", "未", "未定"]
                )
            )

            with label_col:
              color = "#ffeb3b" if is_mi_form else "#00bcd4"
              st.markdown(
                  f"<span style='color: {color};"
                  f" font-size: 0.9em;'>**{title}**</span>",
                  unsafe_allow_html=True,
              )

            with status_col:
              status_choice = st.radio(
                  f"状態_{unique_key}",
                  ["未", "済"],
                  index=0 if is_mi_form else 1,
                  horizontal=True,
                  key=f"status_{unique_key}",
                  label_visibility="collapsed",
              )

            if status_choice == "未":
              edited_payload[title] = (
                  "未定" if ("日" in title or "月" in title) else "未"
              )
            else:
              if "写真" in title or "画像" in title or "添付" in title:
                if not is_new and raw_val and str(raw_val).startswith("http"):
                  st.markdown(
                      f"<a href='{raw_val}' target='_blank'>🔗"
                      " 現在のファイルを開く</a>",
                      unsafe_allow_html=True,
                  )
                uploaded_file = st.file_uploader(
                    f"{title}",
                    type=["jpg", "jpeg", "png", "heic"],
                    key=f"file_{unique_key}",
                    label_visibility="collapsed",
                )
                if uploaded_file:
                  uploaded_files_dict[title] = uploaded_file
                  edited_payload[title] = uploaded_file.name
                else:
                  edited_payload[title] = raw_val if not is_new else "未"

              elif "日" in title or "月" in title:
                parsed_d = parse_fixed_date(raw_val) if not is_new else None
                d_default = parsed_d if parsed_d else date.today()
                chosen_date = st.date_input(
                    title,
                    value=d_default,
                    key=f"date_{unique_key}",
                    label_visibility="collapsed",
                )
                edited_payload[title] = chosen_date.strftime("%Y/%m/%d")

              elif len(options) > 0:
                select_choices = ["未"] + [
                    opt for opt in options if opt != "未"
                ]
                current_val = str(raw_val).strip() if not is_new else ""
                if (
                    current_val in ["-", "", "未選択", "None", "nan", "未"]
                    or current_val not in select_choices
                ):
                  default_idx = 0
                else:
                  default_idx = select_choices.index(current_val)

                chosen_select = st.selectbox(
                    title,
                    select_choices,
                    index=default_idx,
                    key=f"sel_{unique_key}",
                    label_visibility="collapsed",
                )
                edited_payload[title] = chosen_select

              else:
                txt_val = (
                    str(raw_val).strip()
                    if not is_new and not is_mi_form
                    else ""
                )
                typed_val = st.text_input(
                    title,
                    value=txt_val,
                    placeholder="入力",
                    key=f"txt_{unique_key}",
                    label_visibility="collapsed",
                )
                edited_payload[title] = typed_val.strip()

        st.markdown("---")

    if save_clicked:
      if is_new:
        for k, v in edited_payload.items():
          if "物件" in k and v and v != "未":
            property_name = v
            break
      show_confirm_dialog(
          property_name,
          selected_row_id,
          edited_payload,
          uploaded_files_dict,
          target_row,
          target_sheet,
          is_new=is_new,
      )