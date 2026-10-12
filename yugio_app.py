import streamlit as st
import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
import hashlib

# --- matplotlibの日本語化設定 ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'IPAexGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# --- ページ設定（ワイド画面） ---
st.set_page_config(
    page_title="遊戯王 対戦管理アプリ", 
    page_icon="🎮", 
    layout="wide"
)

# --- ファイルパスの設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "yugio_database.db")
IMAGE_FILE = os.path.join(BASE_DIR, "icon.png")

# --- データベースの初期化 ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # ユーザーテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    # 対戦履歴テーブル（ユーザー名ごとにデータを分離）
    c.execute('''
        CREATE TABLE IF NOT EXISTS match_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            list_name TEXT,
            coin TEXT,
            result TEXT,
            deck TEXT
        )
    ''')
    # 【追加】デッキリスト・リスト名を保存するテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_decks (
            username TEXT,
            list_name TEXT,
            deck_index INTEGER,
            deck_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- パスワードのハッシュ化（安全な保存） ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    return make_hash(password) == hashed_password

# --- データベース操作関数 ---
def load_match_data(username):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT list_name, coin, result, deck FROM match_logs WHERE username = ?", 
        conn, 
        params=(username,)
    )
    conn.close()
    # カラム名を日本語に統一
    df.columns = ["リスト名", "コイン", "勝敗", "デッキ"]
    return df

def save_match_data(username, list_name, coin, result, deck):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO match_logs (username, list_name, coin, result, deck) VALUES (?, ?, ?, ?, ?)",
        (username, list_name, coin, result, deck)
    )
    conn.commit()
    conn.close()

def delete_last_match(username, list_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 該当ユーザーかつ該当リストの最新の行のIDを取得
    c.execute(
        "SELECT id FROM match_logs WHERE username = ? AND list_name = ? ORDER BY id DESC LIMIT 1",
        (username, list_name)
    )
    row = c.fetchone()
    if row:
        row_id = row[0]
        c.execute("DELETE FROM match_logs WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def delete_list_data(username, list_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM match_logs WHERE username = ? AND list_name = ?", (username, list_name))
    c.execute("DELETE FROM user_decks WHERE username = ? AND list_name = ?", (username, list_name))
    conn.commit()
    conn.close()

# --- デッキリストの読み込み・保存関数 ---
def load_deck_lists(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT list_name, deck_index, deck_name FROM user_decks WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    
    deck_lists = {}
    if rows:
        for list_name, idx, deck_name in rows:
            if list_name not in deck_lists:
                deck_lists[list_name] = [""] * 10
            if 0 <= idx < 10:
                deck_lists[list_name][idx] = deck_name
    else:
        # 初回などデータがない場合の初期値
        deck_lists = {
            "リスト1": ["エルフェン", "ドラテ(烙印ドラテ)", "獄神", "純烙印", "道化の一座", "妖精伝姫", "キラーチューン", "M∀LICE", "召喚獣(召喚獣ドラテ)", "閃刀姫"]
        }
    return deck_lists

def save_deck_lists(username, deck_lists):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM user_decks WHERE username = ?", (username,))
    for list_name, decks in deck_lists.items():
        for idx, deck_name in enumerate(decks):
            c.execute(
                "INSERT INTO user_decks (username, list_name, deck_index, deck_name) VALUES (?, ?, ?, ?)",
                (username, list_name, idx, deck_name)
            )
    conn.commit()
    conn.close()


# ==========================================
# ログイン画面の制御
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
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ?", (username_input,))
                result = c.fetchone()
                conn.close()
                
                if result and check_password(password_input, result[0]):
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    # ログイン時にデータベースからユーザー専用のデッキリストを読み込む
                    st.session_state.deck_lists = load_deck_lists(username_input)
                    st.success("ログイン成功しました！")
                    st.rerun()
                else:
                    st.error("ユーザー名またはパスワードが間違っています。")
        else:
        # 新規登録
            if st.button("✨ 登録する"):
                if not username_input or not password_input:
                    st.warning("ユーザー名とパスワードを入力してください。")
                else:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT username FROM users WHERE username = ?", (username_input,))
                    exists = c.fetchone()
                    
                    if exists:
                        st.error("このユーザー名はすでに使われています。")
                        conn.close()
                    else:
                        hashed_pw = make_hash(password_input)
                        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username_input, hashed_pw))
                        conn.commit()
                        conn.close()
                        st.success("アカウント登録が完了しました！「ログイン」に切り替えてログインしてください。")
    st.stop()


# ==========================================
# ログイン後のメインアプリ画面
# ==========================================

# セッション状態の初期化（未だ読み込まれていない場合の保険）
if 'deck_lists' not in st.session_state:
    st.session_state.deck_lists = load_deck_lists(st.session_state.username)

# ヘッダー & イラスト表示
col_title, col_img = st.columns([4, 1])
with col_title:
    st.title(f"🎮 遊戯王 対戦管理アプリ (ログイン中: {st.session_state.username} さん)")
    st.markdown("✨ お気に入りのデッキと勝率をスマートに管理しよう！")

with col_img:
    if os.path.exists(IMAGE_FILE):
        st.image(IMAGE_FILE, width=120)

# ログアウトボタンをサイドバーに配置
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
        # データベースに保存
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
    # 【変更点】データベースにデッキリストの変更を保存する
    save_deck_lists(st.session_state.username, st.session_state.deck_lists)
    st.sidebar.success("保存しました！")
    st.rerun()

# --- デッキリストの削除機能 ---
st.sidebar.markdown("---")
if len(st.session_state.deck_lists) > 1:
    if st.sidebar.button(f"🗑️ 「{selected_list}」を削除する"):
        del st.session_state.deck_lists[selected_list]
        # データベースからも削除して保存
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
                        
                        # データベースに保存
                        save_match_data(st.session_state.username, selected_list, c_val, w_val, d_val)
                        
                        st.success(f"👉 記録しました！ コイン:{c_val} / 勝敗:{w_val} / デッキ:{d_val}")
                        st.rerun()
                except ValueError:
                    st.error("❌ 半角数字で入力してください。")

    # --- 直前の記録を削除するボタン ---
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


# --- 右側：円グラフ ＆ 履歴明細 ---
col_graph.subheader(f"🍩 デッキ使用割合 ({selected_list})")

df = load_match_data(st.session_state.username)
if not df.empty:
    df_filtered = df[df["リスト名"] == selected_list]
    
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
        
        with col_graph.expander("📜 対戦履歴の明細を見る"):
            st.dataframe(df_filtered[["コイン", "勝敗", "デッキ"]], use_container_width=True)
    else:
        col_graph.info("グラフにするデータがありません。")
else:
    col_graph.info("データがありません。")