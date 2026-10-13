import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
import hashlib

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

# --- ファイルパスの設定（クラウド上でも安全に動く構成） ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FILE = os.path.join(BASE_DIR, "icon.png")
DATA_FILE = os.path.join(BASE_DIR, "yugio_match_data.csv")
DECKS_FILE = os.path.join(BASE_DIR, "yugio_deck_data.csv")

# --- パスワードのハッシュ化 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    return make_hash(password) == hashed_password

# --- 簡易ユーザー管理（初期ユーザー用） ---
# ※Web版で確実に動かすため、初期アカウントやファイルベースで管理します
@st.cache_data
def get_default_user():
    return {"とだ": make_hash("Ryoma710")}

# --- データ読み書き関数（CSVベース・確実動作版） ---
def load_all_matches():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["username", "リスト名", "コイン", "勝敗", "デッキ", "理由"])

def save_match_row(username, list_name, coin, result, deck, memo):
    df = load_all_matches()
    new_row = pd.DataFrame([{
        "username": username,
        "リスト名": list_name,
        "コイン": coin,
        "勝敗": result,
        "デッキ": deck,
        "理由": memo
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def load_all_decks():
    if os.path.exists(DECKS_FILE):
        return pd.read_csv(DECKS_FILE)
    else:
        # デフォルトデッキ
        default_decks = []
        initial_list = ["エルフェン", "ドラテ(烙印ドラテ)", "獄神", "純烙印", "道化の一座", "妖精伝姫", "キラーチューン", "M∀LICE", "召喚獣(召喚獣ドラテ)", "閃刀姫"]
        for idx, d_name in enumerate(initial_list):
            default_decks.append({"username": "とだ", "list_name": "リスト1", "deck_index": idx, "deck_name": d_name})
        df = pd.DataFrame(default_decks)
        df.to_csv(DECKS_FILE, index=False)
        return df

def save_user_decks(username, deck_lists):
    df_all = load_all_decks()
    # 該当ユーザー以外のデータを保持
    df_other = df_all[df_all["username"] != username]
    
    new_rows = []
    for list_name, decks in deck_lists.items():
        for idx, deck_name in enumerate(decks):
            new_rows.append({
                "username": username,
                "list_name": list_name,
                "deck_index": idx,
                "deck_name": deck_name
            })
    df_new = pd.DataFrame(new_rows)
    df_combined = pd.concat([df_other, df_new], ignore_index=True)
    df_combined.to_csv(DECKS_FILE, index=False)


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
        st.markdown("### ログインしてください")
        
        username_input = st.text_input("ユーザー名", value="とだ")
        password_input = st.text_input("パスワード", type="password", value="Ryoma710")
        
        if st.button("🚀 ログイン"):
            users = get_default_user()
            if username_input in users and check_password(password_input, users[username_input]):
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.success("ログイン成功しました！")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが間違っています。")
    st.stop()


# ==========================================
# ログイン後のメインアプリ画面
# ==========================================
username = st.session_state.username

# デッキリストの読み込み
df_decks = load_all_decks()
user_deck_rows = df_decks[df_decks["username"] == username]

deck_lists = {}
if not user_deck_rows.empty:
    for _, r in user_deck_rows.iterrows():
        l_name = str(r["list_name"])
        idx = int(r["deck_index"])
        d_name = str(r["deck_name"])
        if l_name not in deck_lists:
            deck_lists[l_name] = [""] * 10
        if 0 <= idx < 10:
            deck_lists[l_name][idx] = d_name
else:
    deck_lists = {"リスト1": ["エルフェン", "ドラテ(烙印ドラテ)", "獄神", "純烙印", "道化の一座", "妖精伝姫", "キラーチューン", "M∀LICE", "召喚獣(召喚獣ドラテ)", "閃刀姫"]}

col_title, col_img = st.columns([4, 1])
with col_title:
    st.title(f"🎮 遊戯王 対戦管理アプリ (ログイン中: {username} さん)")
    st.markdown("✨ お気に入りのデッキと勝率をスマートに管理しよう！")

with col_img:
    if os.path.exists(IMAGE_FILE):
        st.image(IMAGE_FILE, width=120)

if st.sidebar.button("🚪 ログアウト"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.sidebar.markdown("---")

# サイドバー：リスト選択・管理
st.sidebar.header("📂 デッキリストを選択")
list_names = list(deck_lists.keys())
selected_list = st.sidebar.selectbox("使用するリスト", list_names)

st.sidebar.markdown("---")
st.sidebar.subheader(f"📝 「{selected_list}」のデッキ編集")

updated_decks = []
for i in range(10):
    current_name = deck_lists[selected_list][i] if selected_list in deck_lists and i < len(deck_lists[selected_list]) else ""
    new_name = st.sidebar.text_input(f"デッキ {i+1}", value=current_name, key=f"deck_{selected_list}_{i}")
    updated_decks.append(new_name)

if st.sidebar.button("💾 変更を保存"):
    deck_lists[selected_list] = updated_decks
    save_user_decks(username, deck_lists)
    st.sidebar.success("保存しました！")
    st.rerun()

active_decks = [d for d in deck_lists[selected_list] if d.strip() != ""]

# =================.=========
# メイン画面
# ==========================================
col_input, col_graph = st.columns([1, 1])

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
                        save_match_row(username, selected_list, c_val, w_val, d_val, memo_input)
                        st.success(f"👉 記録しました！ コイン:{c_val} / 勝敗:{w_val} / デッキ:{d_val}")
                        st.rerun()
                except ValueError:
                    st.error("❌ 半角数字で入力してください。")

    st.markdown("---")
    st.subheader("📊 成績サマリー")

    df_matches = load_all_matches()
    user_matches = df_matches[(df_matches["username"] == username) & (df_matches["リスト名"] == selected_list)]
    
    if not user_matches.empty:
        total_matches = len(user_matches)
        coin_counts = user_matches["コイン"].value_counts()
        front_count = coin_counts.get("○", 0)
        back_count = coin_counts.get("✖", 0)
        front_pct = (front_count / total_matches) * 100 if total_matches > 0 else 0
        back_pct = (back_count / total_matches) * 100 if total_matches > 0 else 0
        
        win_counts = user_matches["勝敗"].value_counts()
        total_wins = win_counts.get("○", 0)
        win_rate = (total_wins / total_matches) * 100 if total_matches > 0 else 0
        
        summary_data = {
            "項目": ["総試合数", "コイン確率", "勝率 [%]"],
            "詳細 / 表(○)": [total_matches, f"{front_pct:.1f}% ({front_count}回)", f"{win_rate:.1f}% ({total_wins}勝)"],
            "裏(✖)": ["-", f"{back_pct:.1f}% ({back_count}回)", f"-"]
        }
        st.table(pd.DataFrame(summary_data))
    else:
        st.info(f"「{selected_list}」のデータはまだありません。")

# --- 右側：円グラフ ---
col_graph.subheader(f"🍩 デッキ使用割合 ({selected_list})")

df_matches = load_all_matches()
user_matches = df_matches[(df_matches["username"] == username) & (df_matches["リスト名"] == selected_list)]

if not user_matches.empty and "デッキ" in user_matches.columns:
    deck_counts = user_matches["デッキ"].value_counts()
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