import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
import hashlib
import gspread
from google.oauth2.service_account import Credentials

# --- matplotlibの日本語化設定 ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Meiryo', 'MS Gothic', 'Yu Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# --- ページ設定 ---
st.set_page_config(
    page_title="遊戯王 対戦管理アプリ", 
    page_icon="🎮", 
    layout="wide"
)

# --- ファイルパスの設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FILE = os.path.join(BASE_DIR, "icon.png")
CRED_FILE = os.path.join(BASE_DIR, "credentials.json")

# --- Googleスプレッドシート接続の初期化（シンプル確実版） ---
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 1. ローカル環境（credentials.jsonがある場合）
    if os.path.exists(CRED_FILE):
        creds = Credentials.from_service_account_file(CRED_FILE, scopes=scope)
    # 2. Streamlit Cloud環境（Secretsから直接読み込む場合）
    elif "gcp_service_account" in st.secrets:
        sec = st.secrets["gcp_service_account"]
        raw_key = str(sec["private_key"])
        fixed_key = raw_key.replace("\\n", "\n")
        
        key_dict = {
            "type": sec["type"],
            "project_id": sec["project_id"],
            "private_key_id": sec["private_key_id"],
            "private_key": fixed_key,
            "client_email": sec["client_email"],
            "client_id": sec["client_id"],
            "auth_uri": sec["auth_uri"],
            "token_uri": sec["token_uri"],
            "auth_provider_x509_cert_url": sec["auth_provider_x509_cert_url"],
            "client_x509_cert_url": sec["client_x509_cert_url"],
            "universe_domain": sec.get("universe_domain", "googleapis.com")
        }
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
    else:
        st.error("❌ 認証情報（credentials.json または Streamlit Secrets）が見つかりません。")
        st.stop()
        
    client = gspread.authorize(creds)
    return client

def get_worksheet(sheet_name):
    try:
        client = get_gspread_client()
        spreadsheet = client.open("遊戯王対戦管理データ")
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet
    except Exception as e:
        st.error(f"❌ Googleスプレッドシート「遊戯王対戦管理データ」のシート「{sheet_name}」が見つかりません。スプレッドシート名やタブ名を確認してください。\nエラー詳細: {e}")
        st.stop()


# --- パスワードのハッシュ化 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    return make_hash(password) == hashed_password


# --- データベース操作（スプレッドシート版） ---

# 1. ユーザー認証関連
def get_user_password(username_input):
    ws = get_worksheet("users")
    records = ws.get_all_records()
    for row in records:
        if str(row.get("username")) == str(username_input):
            return row.get("password")
    return None

def register_user(username_input, password_input):
    ws = get_worksheet("users")
    records = ws.get_all_records()
    for row in records:
        if str(row.get("username")) == str(username_input):
            return False
    hashed_pw = make_hash(password_input)
    ws.append_row([username_input, hashed_pw])
    return True


# 2. 対戦履歴関連
def load_match_data(username):
    ws = get_worksheet("match_logs")
    records = ws.get_all_records()
    
    user_rows = [r for r in records if str(r.get("username")) == str(username)]
    
    if not user_rows:
        return pd.DataFrame(columns=["リスト名", "コイン", "勝敗", "デッキ", "理由"])
    
    df = pd.DataFrame(user_rows)
    if "list_name" in df.columns:
        if "memo" not in df.columns:
            df["memo"] = ""
            
        df = df[["list_name", "coin", "result", "deck", "memo"]]
        df.columns = ["リスト名", "コイン", "勝敗", "デッキ", "理由"]
    else:
        return pd.DataFrame(columns=["リスト名", "コイン", "勝敗", "デッキ", "理由"])
    return df

def save_match_data(username, list_name, coin, result, deck, memo):
    ws = get_worksheet("match_logs")
    ws.append_row([username, list_name, coin, result, deck, memo])

def delete_last_match(username, list_name):
    ws = get_worksheet("match_logs")
    data = ws.get_all_values()
    if len(data) <= 1:
        return False
    
    rows = data[1:]
    target_idx = -1
    for i in range(len(rows) - 1, -1, -1):
        row = rows[i]
        if len(row) >= 2 and row[0] == username and row[1] == list_name:
            target_idx = i + 2
            break
            
    if target_idx != -1:
        ws.delete_rows(target_idx)
        return True
    return False

def delete_list_data(username, list_name):
    ws_logs = get_worksheet("match_logs")
    data_logs = ws_logs.get_all_values()
    if len(data_logs) > 1:
        header = data_logs[0]
        rows = data_logs[1:]
        new_rows = [header] + [r for r in rows if not (len(r) >= 2 and r[0] == username and r[1] == list_name)]
        ws_logs.clear()
        ws_logs.update(new_rows)
        
    ws_decks = get_worksheet("user_decks")
    data_decks = ws_decks.get_all_values()
    if len(data_decks) > 1:
        header_d = data_decks[0]
        rows_d = data_decks[1:]
        new_rows_d = [header_d] + [r for r in rows_d if not (len(r) >= 2 and r[0] == username and r[1] == list_name)]
        ws_decks.clear()
        ws_decks.update(new_rows_d)

def update_all_match_data_for_user(username, list_name, new_df_filtered):
    ws = get_worksheet("match_logs")
    data = ws.get_all_values()
    if not data:
        return
    header = data[0]
    rows = data[1:]
    
    other_rows = [r for r in rows if not (len(r) >= 2 and r[0] == username and r[1] == list_name)]
    
    updated_user_rows = []
    for _, r in new_df_filtered.iterrows():
        updated_user_rows.append([username, list_name, r["コイン"], r["勝敗"], r["デッキ"], r["理由"]])
        
    final_data = [header] + other_rows + updated_user_rows
    ws.clear()
    ws.update(final_data)


# 3. デッキリスト関連
def load_deck_lists(username):
    ws = get_worksheet("user_decks")
    records = ws.get_all_records()
    
    user_rows = [r for r in records if str(r.get("username")) == str(username)]
    
    deck_lists = {}
    if user_rows:
        for r in user_rows:
            list_name = str(r.get("list_name"))
            idx = int(r.get("deck_index", 0))
            deck_name = str(r.get("deck_name", ""))
            
            if list_name not in deck_lists:
                deck_lists[list_name] = [""] * 10
            if 0 <= idx < 10:
                deck_lists[list_name][idx] = deck_name
    else:
        deck_lists = {
            "リスト1": ["エルフェン", "ドラテ(烙印ドラテ)", "獄神", "純烙印", "道化の一座", "妖精伝姫", "キラーチューン", "M∀LICE", "召喚獣(召喚獣ドラテ)", "閃刀姫"]
        }
    return deck_lists

def save_deck_lists(username, deck_lists):
    ws = get_worksheet("user_decks")
    data = ws.get_all_values()
    header = data[0] if len(data) > 0 else ["username", "list_name", "deck_index", "deck_name"]
    
    rows = data[1:] if len(data) > 1 else []
    other_user_rows = [r for r in rows if len(r) >= 1 and r[0] != username]
    
    new_user_rows = []
    for list_name, decks in deck_lists.items():
        for idx, deck_name in enumerate(decks):
            new_user_rows.append([username, list_name, idx, deck_name])
            
    final_data = [header] + other_user_rows + new_user_rows
    ws.clear()
    ws.update(final_data)


# ==========================================
# ログイン・新規登録画面の制御
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.title("🎮 遊戯王 対戦管理アプリ")
        st.markdown("### ログインまたは新規登録してください")
        
        choice = st.selectbox("メニュー", ["ログイン", "新規アカウント登録"])
        username_input = st.text_input("ユーザー名")
        password_input = st.text_input("パスワード", type="password")
        
        if choice == "ログイン":
            if st.button("🚀 ログイン"):
                stored_pw = get_user_password(username_input)
                
                if stored_pw and check_password(password_input, stored_pw):
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.session_state.deck_lists = load_deck_lists(username_input)
                    st.success("ログイン成功しました！")
                    st.rerun()
                else:
                    st.error("ユーザー名またはパスワードが間違っています。")
        else:
            if st.button("✨ 登録する"):
                if not username_input or not password_input:
                    st.warning("ユーザー名とパスワードを入力してください。")
                else:
                    success = register_user(username_input, password_input)
                    if success:
                        st.success("アカウント登録が完了しました！「ログイン」に切り替えてログインしてください。")
                    else:
                        st.error("このユーザー名はすでに使われています。")
    st.stop()


# ==========================================
# ログイン後のメインアプリ画面
# ==========================================

if 'deck_lists' not in st.session_state:
    st.session_state.deck_lists = load_deck_lists(st.session_state.username)

col_title, col_img = st.columns([4, 1])
with col_title:
    st.title(f"🎮 遊戯王 対戦管理アプリ (ログイン中: {st.session_state.username} さん)")
    st.markdown("✨ お気に入りのデッキと勝率をスマートに管理しよう！")

with col_img:
    if os.path.exists(IMAGE_FILE):
        st.image(IMAGE_FILE, width=120)

if st.sidebar.button("🚪 ログアウト"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    if 'deck_lists' in st.session_state:
        del st.session_state.deck_lists
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# サイドバー：リストの選択・管理 ＆ 削除機能
# ==========================================
st.sidebar.header("📂 デッキリストを選択")

new_list_name = st.sidebar.text_input("新しいリスト名 (例: リスト2)")
if st.sidebar.button("➕ リストを追加"):
    if new_list_name and new_list_name not in st.session_state.deck_lists:
        st.session_state.deck_lists[new_list_name] = [""] * 10
        save_deck_lists(st.session_state.username, st.session_state.deck_lists)
        st.sidebar.success(f"「{new_list_name}」を追加しました！")
        st.rerun()
    elif not new_list_name:
        st.sidebar.warning("リスト名を入力してください。")
    else:
        st.sidebar.warning("すでに存在するリスト名です。")

list_names = list(st.session_state.deck_lists.keys())
selected_list = st.sidebar.selectbox("使用するリスト", list_names)

st.sidebar.markdown("---")
st.sidebar.subheader(f"📝 「{selected_list}」のデッキ編集")

updated_decks = []
for i in range(10):
    current_name = st.session_state.deck_lists[selected_list][i]
    new_name = st.sidebar.text_input(f"デッキ {i+1}", value=current_name, key=f"deck_{selected_list}_{i}")
    updated_decks.append(new_name)

if st.sidebar.button("💾 変更を保存"):
    st.session_state.deck_lists[selected_list] = updated_decks
    save_deck_lists(st.session_state.username, st.session_state.deck_lists)
    st.sidebar.success("保存しました！")
    st.rerun()

st.sidebar.markdown("---")
if len(st.session_state.deck_lists) > 1:
    if st.sidebar.button(f"🗑️ 「{selected_list}」を削除する"):
        del st.session_state.deck_lists[selected_list]
        save_deck_lists(st.session_state.username, st.session_state.deck_lists)
        delete_list_data(st.session_state.username, selected_list)
        st.sidebar.success(f"「{selected_list}」を削除しました！")
        st.rerun()
else:
    st.sidebar.info("ℹ️ リストが1つしかないため削除できません。")

active_decks = [d for d in st.session_state.deck_lists[selected_list] if d.strip() != ""]


# ==========================================
# メイン画面
# ==========================================
col_input, col_graph = st.columns([1, 1])

# --- 左側：入力欄 ＆ 成績サマリー ---
with col_input:
    st.subheader(f"📋 対戦結果の記録 ({selected_list})")
    
    if active_decks:
        deck_text = " / ".join([f"**{i+1}**: {name}" for i, name in enumerate(active_decks)])
        st.info(f"**【デッキ番号】**\n\n {deck_text}")
    else:
        st.warning("⚠️ サイドバーからデッキ名を入力してください。")

    with st.form("record_form", clear_on_submit=True):
        st.markdown("**【入力ルール】**")
        st.markdown("半角数字で `[コイン] [勝敗] [デッキ番号]` をスペース区切りで入力")
        st.markdown("・コイン: `1`=○, `2`=✖  /  勝敗: `1`=○, `2`=✖")
        
        user_input = st.text_input("入力欄 (例: 1 1 3)")
        memo_input = st.text_input("対戦の理由・メモ (任意 例: G通った、事故など)")
        submitted = st.form_submit_button("🚀 記録する")
        
        if submitted:
            parts = user_input.split()
            if len(parts) != 3:
                st.error("❌ 3つの数字をスペース区切りで入力してください（例: 1 1 3）")
            elif not active_decks:
                st.error("❌ デッキが登録されていません。")
            else:
                try:
                    c_idx, w_idx, d_idx = int(parts[0]), int(parts[1]), int(parts[2])
                    coin_dict = {1: "○", 2: "✖"}
                    win_dict = {1: "○", 2: "✖"}
                    
                    c_val = coin_dict.get(c_idx, "")
                    w_val = win_dict.get(w_idx, "")
                    
                    if d_idx < 1 or d_idx > len(active_decks):
                        st.error(f"❌ デッキ番号は 1 〜 {len(active_decks)} の間で入力してください。")
                    else:
                        d_val = active_decks[d_idx - 1]
                        
                        save_match_data(st.session_state.username, selected_list, c_val, w_val, d_val, memo_input)
                        
                        st.success(f"👉 記録しました！ コイン:{c_val} / 勝敗:{w_val} / デッキ:{d_val}")
                        st.rerun()
                except ValueError:
                    st.error("❌ 半角数字で入力してください。")

    if st.button("↩️ 直前の記録を1件削除する"):
        success = delete_last_match(st.session_state.username, selected_list)
        if success:
            st.success("🗑️ 直前の記録を削除しました！")
            st.rerun()
        else:
            st.warning("⚠️ 削除できる記録がありません。")

    st.markdown("---")
    st.subheader("📊 成績サマリー")

    df = load_match_data(st.session_state.username)
    if not df.empty:
        df_filtered = df[df["リスト名"] == selected_list]
        total_matches = len(df_filtered)
        
        if total_matches > 0:
            coin_counts = df_filtered["コイン"].value_counts()
            front_count = coin_counts.get("○", 0)
            back_count = coin_counts.get("✖", 0)
            front_pct = (front_count / total_matches) * 100
            back_pct = (back_count / total_matches) * 100
            
            win_counts = df_filtered["勝敗"].value_counts()
            total_wins = win_counts.get("○", 0)
            win_rate = (total_wins / total_matches) * 100
            
            summary_data = {
                "項目": ["総試合数", "コイン確率", "勝率 [%]"],
                "詳細 / 表(○)": [total_matches, f"{front_pct:.1f}% ({front_count}回)", f"{win_rate:.1f}% ({total_wins}勝)"],
                "裏(✖)": ["-", f"{back_pct:.1f}% ({back_count}回)", f"-"]
            }
            st.table(pd.DataFrame(summary_data))
        else:
            st.info(f"「{selected_list}」のデータはまだありません。")
    else:
        st.info("データがありません。")


# --- 右側：円グラフ ＆ 履歴明細（直接編集対応） ---
col_graph.subheader(f"🍩 デッキ使用割合 ({selected_list})")

df = load_match_data(st.session_state.username)
if not df.empty:
    df_filtered = df[df["リスト名"] == selected_list].copy()
    
    if not df_filtered.empty and "デッキ" in df_filtered.columns:
        deck_counts = df_filtered["デッキ"].value_counts()
        
        if len(deck_counts) > 0:
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.pie(
                deck_counts, 
                labels=deck_counts.index, 
                autopct='%1.1f%%', 
                startangle=90,
                colors=plt.cm.Pastel1.colors,
                textprops={'fontsize': 12}
            )
            ax.axis('equal')
            col_graph.pyplot(fig)
        else:
            col_graph.info("グラフにするデータがありません。")
        
        with col_graph.expander("📜 対戦履歴の明細を見る（メモの直接編集が可能）"):
            st.markdown("💡下の表の「理由」欄をクリックすると、後からでも自由に入力・編集できます。編集後は下のボタンを押して保存してください！")
            
            df_display = df_filtered[["コイン", "勝敗", "デッキ", "理由"]].reset_index(drop=True)
            
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "コイン": st.column_config.TextColumn("コイン", disabled=True),
                    "勝敗": st.column_config.TextColumn("勝敗", disabled=True),
                    "デッキ": st.column_config.TextColumn("デッキ", disabled=True),
                    "理由": st.column_config.TextColumn("理由 (クリックして編集可能)", width="large"),
                },
                use_container_width=True,
                key=f"editor_{selected_list}"
            )
            
            if st.button("💾 メモの変更を保存する"):
                df_all = load_match_data(st.session_state.username)
                df_other = df_all[df_all["リスト名"] != selected_list]
                
                edited_df["リスト名"] = selected_list
                edited_df = edited_df[["リスト名", "コイン", "勝敗", "デッキ", "理由"]]
                
                df_combined = pd.concat([df_other, edited_df], ignore_index=True)
                
                update_all_match_data_for_user(st.session_state.username, selected_list, df_combined[df_combined["リスト名"] == selected_list])
                st.success("✨ メモの変更をスプレッドシートに保存しました！")
                st.rerun()
    else:
        col_graph.info("グラフにするデータがありません。")
else:
    col_graph.info("データがありません。")