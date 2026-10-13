import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
import hashlib
import matplotlib.font_manager as fm

# --- matplotlibの日本語化設定（Linux/Cloud環境対応） ---
plt.rcParams['axes.unicode_minus'] = False
font_names = [f.name for f in fm.fontManager.ttflist]
for target in ['Meiryo', 'MS Gothic', 'Yu Gothic', 'DejaVu Sans', 'TakaoPGothic', 'IPAexGothic']:
    if target in font_names:
        plt.rcParams['font.sans-serif'] = [target]
        break

# --- ページ設定 ---
st.set_page_config(
    page_title="遊戯王 対戦管理アプリ", 
    page_icon="🎮", 
    layout="wide"
)

# --- ファイルパスの設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FILE = os.path.join(BASE_DIR, "icon.png")
DATA_FILE = os.path.join(BASE_DIR, "yugio_match_data.csv")
DECKS_FILE = os.path.join(BASE_DIR, "yugio_deck_data.csv")
USERS_FILE = os.path.join(BASE_DIR, "yugio_users.csv")

# --- パスワードのハッシュ化 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    return make_hash(password) == hashed_password

# --- ユーザー管理関数（CSVベース） ---
def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    else:
        df_init = pd.DataFrame([{"username": "とだ", "password": make_hash("Ryoma710")}])
        df_init.to_csv(USERS_FILE, index=False)
        return df_init

def get_user_password(username_input):
    df_users = load_users()
    for _, row in df_users.iterrows():
        if str(row["username"]) == str(username_input):
            return row["password"]
    return None

def register_user(username_input, password_input):
    df_users = load_users()
    if not df_users[df_users["username"] == username_input].empty:
        return False
    hashed_pw = make_hash(password_input)
    new_row = pd.DataFrame([{"username": username_input, "password": hashed_pw}])
    df_users = pd.concat([df_users, new_row], ignore_index=True)
    df_users.to_csv(USERS_FILE, index=False)
    return True

# --- 対戦履歴データ管理関数 ---
def load_match_data_all():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        expected_cols = ["username", "list_name", "coin", "result", "deck", "memo"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=["username", "list_name", "coin", "result", "deck", "memo"])

def load_match_data(username):
    df_all = load_match_data_all()
    if df_all.empty:
        return pd.DataFrame(columns=["リスト名", "コイン", "勝敗", "デッキ", "理由"])
    
    user_df = df_all[df_all["username"] == username].copy()
    if user_df.empty:
        return pd.DataFrame(columns=["リスト名", "コイン", "勝敗", "デッキ", "理由"])
    
    res_df = pd.DataFrame({
        "リスト名": user_df["list_name"].astype(str),
        "コイン": user_df["coin"].astype(str),
        "勝敗": user_df["result"].astype(str),
        "デッキ": user_df["deck"].astype(str),
        "理由": user_df["memo"].fillna("").astype(str)
    })
    return res_df.reset_index(drop=True)

def save_match_data(username, list_name, coin, result, deck, memo):
    df_all = load_match_data_all()
    new_row = pd.DataFrame([{
        "username": username,
        "list_name": list_name,
        "coin": coin,
        "result": result,
        "deck": deck,
        "memo": memo if memo else ""
    }])
    df_all = pd.concat([df_all, new_row], ignore_index=True)
    df_all.to_csv(DATA_FILE, index=False)

def delete_last_match(username, selected_list):
    df_all = load_match_data_all()
    if df_all.empty:
        return False
    user_mask = (df_all["username"] == username) & (df_all["list_name"] == selected_list)
    user_indices = df_all[user_mask].index
    if len(user_indices) == 0:
        return False
    last_idx = user_indices[-1]
    df_all = df_all.drop(last_idx)
    df_all.to_csv(DATA_FILE, index=False)
    return True

def delete_list_data(username, selected_list):
    df_all = load_match_data_all()
    if not df_all.empty:
        df_all = df_all[~((df_all["username"] == username) & (df_all["list_name"] == selected_list))]
        df_all.to_csv(DATA_FILE, index=False)

    df_decks = load_all_decks_raw()
    if not df_decks.empty:
        df_decks = df_decks[~((df_decks["username"] == username) & (df_decks["list_name"] == selected_list))]
        df_decks.to_csv(DECKS_FILE, index=False)

def update_all_match_data_for_user(username, selected_list, new_filtered_df):
    df_all = load_match_data_all()
    if not df_all.empty:
        df_other = df_all[~((df_all["username"] == username) & (df_all["list_name"] == selected_list))]
    else:
        df_other = pd.DataFrame(columns=["username", "list_name", "coin", "result", "deck", "memo"])
    
    new_rows = []
    for _, r in new_filtered_df.iterrows():
        new_rows.append({
            "username": username,
            "list_name": selected_list,
            "coin": str(r["コイン"]),
            "result": str(r["勝敗"]),
            "deck": str(r["デッキ"]),
            "memo": str(r["理由"]) if pd.notna(r["理由"]) else ""
        })
    df_new = pd.DataFrame(new_rows)
    df_combined = pd.concat([df_other, df_new], ignore_index=True)
    df_combined.to_csv(DATA_FILE, index=False)


# --- デッキリストデータ管理関数 ---
def load_all_decks_raw():
    if os.path.exists(DECKS_FILE):
        df = pd.read_csv(DECKS_FILE)
        expected_cols = ["username", "list_name", "deck_index", "deck_name"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=["username", "list_name", "deck_index", "deck_name"])

def load_deck_lists(username):
    df_decks = load_all_decks_raw()
    user_rows = df_decks[df_decks["username"] == username]
    
    deck_lists = {}
    if not user_rows.empty:
        for _, r in user_rows.iterrows():
            list_name = str(r["list_name"])
            idx = int(r["deck_index"]) if pd.notna(r["deck_index"]) else 0
            deck_name = str(r["deck_name"]) if pd.notna(r["deck_name"]) else ""
            
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
    df_all = load_all_decks_raw()
    if not df_all.empty:
        df_other = df_all[df_all["username"] != username]
    else:
        df_other = pd.DataFrame(columns=["username", "list_name", "deck_index", "deck_name"])
    
    new_rows = []
    for list_name, decks in deck_lists.items():
        for idx, deck_name in enumerate(decks):
            new_rows.append({
                "username": username,
                "list_name": list_name,
                "deck_index": idx,
                "deck_name": deck_name if deck_name else ""
            })
    df_new = pd.DataFrame(new_rows)
    df_combined = pd.concat([df_other, df_new], ignore_index=True)
    df_combined.to_csv(DECKS_FILE, index=False)


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

# 常にエクスパンダーとテーブルを表示するように修正
with col_graph.expander("📜 対戦履歴の明細を見る（メモの直接編集が可能）", expanded=True):
    st.markdown("💡下の表の「理由」欄をクリックすると、後からでも自由に入力・編集できます。編集後は下のボタンを押して保存してください！")
    
    if not df.empty:
        df_filtered = df[df["リスト名"] == selected_list].copy()
    else:
        df_filtered = pd.DataFrame(columns=["リスト名", "コイン", "勝敗", "デッキ", "理由"])
    
    if not df_filtered.empty:
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
            edited_df["リスト名"] = selected_list
            update_all_match_data_for_user(st.session_state.username, selected_list, edited_df)
            st.success("✨ メモの変更を保存しました！")
            st.rerun()
    else:
        st.info("まだ対戦履歴がありません。左側の入力欄から記録を追加してください。")

# グラフ描画部分
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
    else:
        col_graph.info("グラフにするデータがありません。")
else:
    col_graph.info("データがありません。")