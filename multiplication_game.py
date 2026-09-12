import streamlit as st
import random
import pandas as pd

# 引入 Cloudflare D1 資料庫連線模組
try:
    import d1_client
except Exception:
    d1_client = None

# 設定網頁標題與排版
st.set_page_config(
    page_title="九九乘法大對決 🎯 雙人/班級版 (Cloudflare D1 雲端後台)",
    page_icon="🧮",
    layout="wide"
)

# 自訂 CSS 提升教室大螢幕對戰視覺效果（題目與選項按鈕全部 75px 超大字體）
st.markdown("""
<style>
    /* 題目超大字體 */
    .big-question {
        font-size: 75px !important;
        font-weight: 900;
        text-align: center;
        color: #1E293B;
        background: linear-gradient(135deg, #F8FAFC, #E2E8F0);
        padding: 20px;
        border-radius: 20px;
        margin: 15px 0;
        border: 3px solid #CBD5E1;
        box-shadow: 0 8px 16px rgba(0,0,0,0.06);
    }
    
    /* 隊伍資訊卡片 */
    .team-card-red {
        background: linear-gradient(135deg, #FEE2E2, #FECACA);
        border: 3px solid #EF4444;
        border-radius: 18px;
        padding: 16px;
        text-align: center;
    }
    .team-card-blue {
        background: linear-gradient(135deg, #DBEAFE, #BFDBFE);
        border: 3px solid #3B82F6;
        border-radius: 18px;
        padding: 16px;
        text-align: center;
    }
    .team-score {
        font-size: 52px;
        font-weight: 900;
        margin: 8px 0;
    }
    .red-score { color: #DC2626; }
    .blue-score { color: #2563EB; }
    .vs-badge {
        font-size: 36px;
        font-weight: 900;
        text-align: center;
        color: #D97706;
        padding-top: 35px;
    }
    .action-prompt {
        font-size: 26px;
        font-weight: 900;
        text-align: center;
        margin-bottom: 12px;
    }

    /* 4 個選項按鈕：設定與題目一樣大的超巨字體 (75px) 與超大觸控面積 */
    div[data-testid="stColumn"] .stButton button {
        min-height: 125px !important;
        border-radius: 22px !important;
        border: 4px solid #94A3B8 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 8px 18px rgba(0,0,0,0.1) !important;
        transition: all 0.12s ease-in-out !important;
        margin: 6px 0 !important;
    }
    div[data-testid="stColumn"] .stButton button p {
        font-size: 72px !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        color: #0F172A !important;
    }
    div[data-testid="stColumn"] .stButton button:hover {
        border-color: #2563EB !important;
        background-color: #F0FDF4 !important;
        transform: scale(1.03) !important;
        box-shadow: 0 12px 24px rgba(0,0,0,0.15) !important;
    }
    div[data-testid="stColumn"] .stButton button:active {
        transform: scale(0.96) !important;
    }

    /* 一般功能/設定按鈕維持適中大小 */
    div[data-testid="stVerticalBlock"] > .stButton button {
        min-height: 55px !important;
        border-radius: 12px !important;
    }
    div[data-testid="stVerticalBlock"] > .stButton button p {
        font-size: 24px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 共用題目產生函式 -----------------
def generate_single_question(mode, table_nums):
    """產生單題題目與 4 個選項"""
    if mode == "指定段數特訓":
        a = random.choice(table_nums)
        b = random.randint(1, 9)
    elif mode == "進階挑戰 (1~19)":
        a = random.randint(2, 19)
        b = random.randint(2, 19)
    else:  # 全隨機標準九九乘法 (2~9)
        a = random.randint(2, 9)
        b = random.randint(2, 9)
    
    correct_ans = a * b
    distractors = set()
    distractors.add((a + 1) * b)
    distractors.add(a * (b + 1))
    distractors.add((a - 1) * b if a > 1 else (a + 2) * b)
    distractors.add(a * (b - 1) if b > 1 else a * (b + 2))
    distractors.add(correct_ans + random.choice([-2, -1, 1, 2, 10, -10]))
    
    distractors = [d for d in distractors if d != correct_ans and d > 0]
    random.shuffle(distractors)
    wrong_choices = distractors[:3]
    
    while len(wrong_choices) < 3:
        fake = random.randint(max(1, correct_ans - 10), correct_ans + 10)
        if fake != correct_ans and fake not in wrong_choices:
            wrong_choices.append(fake)
    
    options = [correct_ans] + wrong_choices
    random.shuffle(options)
    
    return {
        "a": a,
        "b": b,
        "answer": correct_ans,
        "options": options
    }

# =========================================================================
# 側邊欄：主模式切換與雲端數據看板
# =========================================================================
st.sidebar.title("🎮 遊戲模式選擇")
app_mode = st.sidebar.radio(
    "選擇要進行的活動：",
    ["⚔️ 雙人 / 分組對抗 PK 賽", "🎯 單人練習 / 全班投影搶答"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **教學小撇步**：\n"
    "- **雙人對抗**：兩位同學站在電子白板左右兩側，看誰先按對！\n"
    "- **全班搶答**：適合老師投影在黑板帶全班計時刷題。"
)

# 雲端後台狀態與即時摘要
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ 雲端教學數據庫 (D1)")

if d1_client:
    # 錯題熱點診斷
    with st.sidebar.expander("📊 全班錯題熱點 TOP 5"):
        try:
            top_wrongs = d1_client.get_top_wrong_questions(5)
            if top_wrongs:
                for idx, w in enumerate(top_wrongs, 1):
                    st.markdown(f"**{idx}. `{w['question']}`** ➔ 累計錯了 **{w['error_count']}** 次（正解: `{w['correct_answer']}`）")
            else:
                st.caption("目前尚無錯題紀錄，大家表現優異！")
        except Exception as e:
            st.caption(f"尚未連線資料庫: {e}")

    # 即時英雄榜預覽
    with st.sidebar.expander("🏆 即時搶答榜 TOP 5"):
        try:
            top_solos = d1_client.get_solo_leaderboard(5)
            if top_solos:
                for idx, s in enumerate(top_solos, 1):
                    st.markdown(f"**第 {idx} 名**：{s['player_name']} — **{s['score']} 分** ({s['accuracy']}%)")
            else:
                st.caption("尚無排行榜數據")
        except Exception as e:
            st.caption(f"尚未連線資料庫: {e}")

# =========================================================================
# 模式一：⚔️ 雙人 / 分組對抗 PK 賽
# =========================================================================
if app_mode == "⚔️ 雙人 / 分組對抗 PK 賽":
    if "pk_state" not in st.session_state:
        st.session_state.pk_state = "setup"
    if "red_score" not in st.session_state:
        st.session_state.red_score = 0
    if "blue_score" not in st.session_state:
        st.session_state.blue_score = 0
    if "target_score" not in st.session_state:
        st.session_state.target_score = 5
    if "pk_q" not in st.session_state:
        st.session_state.pk_q = None
    if "pk_msg" not in st.session_state:
        st.session_state.pk_msg = None
    if "winner" not in st.session_state:
        st.session_state.winner = None
    if "pk_saved" not in st.session_state:
        st.session_state.pk_saved = False

    def start_pk_game(mode, table_nums, target):
        st.session_state.pk_mode = mode
        st.session_state.pk_table_nums = table_nums
        st.session_state.target_score = target
        st.session_state.red_score = 0
        st.session_state.blue_score = 0
        st.session_state.winner = None
        st.session_state.pk_msg = None
        st.session_state.pk_saved = False
        st.session_state.pk_q = generate_single_question(mode, table_nums)
        st.session_state.pk_state = "playing"

    def handle_pk_answer(team, chosen_val):
        curr_q = st.session_state.pk_q
        if chosen_val == curr_q["answer"]:
            if team == "red":
                st.session_state.red_score += 1
                st.session_state.pk_msg = f"🔴 **{st.session_state.red_name} 搶答成功！** （{curr_q['a']} × {curr_q['b']} = {curr_q['answer']}）"
            else:
                st.session_state.blue_score += 1
                st.session_state.pk_msg = f"🔵 **{st.session_state.blue_name} 搶答成功！** （{curr_q['a']} × {curr_q['b']} = {curr_q['answer']}）"
            
            if st.session_state.red_score >= st.session_state.target_score:
                st.session_state.winner = f"🔴 {st.session_state.red_name}"
                st.session_state.pk_state = "ended"
            elif st.session_state.blue_score >= st.session_state.target_score:
                st.session_state.winner = f"🔵 {st.session_state.blue_name}"
                st.session_state.pk_state = "ended"
            else:
                st.session_state.pk_q = generate_single_question(st.session_state.pk_mode, st.session_state.pk_table_nums)
        else:
            if team == "red":
                st.session_state.red_score = max(0, st.session_state.red_score - 1)
                st.session_state.pk_msg = f"❌ 🔴 {st.session_state.red_name} 答錯（選了 {chosen_val}），扣 1 分！換藍隊搶答！"
            else:
                st.session_state.blue_score = max(0, st.session_state.blue_score - 1)
                st.session_state.pk_msg = f"❌ 🔵 {st.session_state.blue_name} 答錯（選了 {chosen_val}），扣 1 分！換紅隊搶答！"

    # --- PK 設定頁 ---
    if st.session_state.pk_state == "setup":
        st.title("⚔️ 雙人分組對抗 PK 賽 — 賽事設定")
        
        col_r, col_b = st.columns(2)
        with col_r:
            st.markdown('<div class="team-card-red"><h3>🔴 紅隊（左方陣營）</h3></div>', unsafe_allow_html=True)
            red_name = st.text_input("紅隊名稱 / 選手姓名：", value="紅隊 迅猛龍", key="input_red")
        with col_b:
            st.markdown('<div class="team-card-blue"><h3>🔵 藍隊（右方陣營）</h3></div>', unsafe_allow_html=True)
            blue_name = st.text_input("藍隊名稱 / 選手姓名：", value="藍隊 烈火鷹", key="input_blue")

        st.session_state.red_name = red_name
        st.session_state.blue_name = blue_name

        st.write("---")
        c1, c2 = st.columns(2)
        with c1:
            pk_mode = st.radio("📌 對戰題型：", ["標準九九乘法 (2~9)", "指定段數特訓", "進階挑戰 (1~19)"], key="pk_mode_radio")
            selected_tables = [7, 8, 9]
            if pk_mode == "指定段數特訓":
                selected_tables = st.multiselect("選擇段數：", options=list(range(2, 10)), default=[7, 8, 9])
        with c2:
            target_pts = st.select_slider("🏆 勝利條件（先搶到幾分獲勝）：", options=[3, 5, 7, 10, 15], value=5)
            st.write("")
            st.write("")
            if st.button("🔥 雙方就位，開戰！", type="primary", use_container_width=True):
                if pk_mode == "指定段數特訓" and not selected_tables:
                    st.error("請至少選擇一個段數！")
                else:
                    start_pk_game(pk_mode, selected_tables, target_pts)
                    st.rerun()

    # --- PK 對戰進行頁 ---
    elif st.session_state.pk_state == "playing":
        col_left, col_mid, col_right = st.columns([4, 2, 4])
        with col_left:
            st.markdown(f'''
            <div class="team-card-red">
                <h2>🔴 {st.session_state.red_name}</h2>
                <div class="team-score red-score">{st.session_state.red_score} <span style="font-size:24px; color:#6B7280;">/ {st.session_state.target_score} 分</span></div>
            </div>
            ''', unsafe_allow_html=True)
            st.progress(min(1.0, st.session_state.red_score / st.session_state.target_score))
        
        with col_mid:
            st.markdown('<div class="vs-badge">⚡ VS ⚡</div>', unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center; color:#64748B;'>先達 <b>{st.session_state.target_score} 分</b> 獲勝</p>", unsafe_allow_html=True)

        with col_right:
            st.markdown(f'''
            <div class="team-card-blue">
                <h2>🔵 {st.session_state.blue_name}</h2>
                <div class="team-score blue-score">{st.session_state.blue_score} <span style="font-size:24px; color:#6B7280;">/ {st.session_state.target_score} 分</span></div>
            </div>
            ''', unsafe_allow_html=True)
            st.progress(min(1.0, st.session_state.blue_score / st.session_state.target_score))

        # 即時廣播提示
        if st.session_state.pk_msg:
            st.info(st.session_state.pk_msg)

        # 中央超大題目
        q = st.session_state.pk_q
        st.markdown(f'<div class="big-question">{q["a"]} × {q["b"]} = ?</div>', unsafe_allow_html=True)

        # 雙人點擊按鈕區（左右兩側各一套 4 個超大數字）
        col_r_btns, col_spacer, col_b_btns = st.columns([4, 1, 4])
        opts = q["options"]

        with col_r_btns:
            st.markdown('<div class="action-prompt" style="color:#DC2626;">👈 紅隊點選區</div>', unsafe_allow_html=True)
            r_c1, r_c2 = st.columns(2)
            with r_c1:
                if st.button(f"{opts[0]}", key="r_opt_0", use_container_width=True):
                    handle_pk_answer("red", opts[0])
                    st.rerun()
                if st.button(f"{opts[2]}", key="r_opt_2", use_container_width=True):
                    handle_pk_answer("red", opts[2])
                    st.rerun()
            with r_c2:
                if st.button(f"{opts[1]}", key="r_opt_1", use_container_width=True):
                    handle_pk_answer("red", opts[1])
                    st.rerun()
                if st.button(f"{opts[3]}", key="r_opt_3", use_container_width=True):
                    handle_pk_answer("red", opts[3])
                    st.rerun()

        with col_spacer:
            st.write("")

        with col_b_btns:
            st.markdown('<div class="action-prompt" style="color:#2563EB;">👉 藍隊點選區</div>', unsafe_allow_html=True)
            b_c1, b_c2 = st.columns(2)
            with b_c1:
                if st.button(f"{opts[0]}", key="b_opt_0", use_container_width=True):
                    handle_pk_answer("blue", opts[0])
                    st.rerun()
                if st.button(f"{opts[2]}", key="b_opt_2", use_container_width=True):
                    handle_pk_answer("blue", opts[2])
                    st.rerun()
            with b_c2:
                if st.button(f"{opts[1]}", key="b_opt_1", use_container_width=True):
                    handle_pk_answer("blue", opts[1])
                    st.rerun()
                if st.button(f"{opts[3]}", key="b_opt_3", use_container_width=True):
                    handle_pk_answer("blue", opts[3])
                    st.rerun()

        st.write("")
        if st.button("⏹️ 中止比賽返回設定"):
            st.session_state.pk_state = "setup"
            st.rerun()

    # --- PK 勝利結算頁 ---
    elif st.session_state.pk_state == "ended":
        st.balloons()
        st.title("🏆 比賽結束！冠軍出爐！")
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FEF3C7, #FDE68A); padding: 40px; border-radius: 20px; text-align: center; border: 4px solid #F59E0B; margin: 20px 0;">
            <h1 style="font-size: 60px; color: #B45309;">👑 恭喜 {st.session_state.winner} 榮獲冠軍！ 👑</h1>
            <p style="font-size: 28px; color: #78350F; font-weight: bold;">最終比分： 🔴 {st.session_state.red_score} 比 🔵 {st.session_state.blue_score}</p>
        </div>
        """, unsafe_allow_html=True)

        # 自動將對抗賽戰報記錄至 Cloudflare D1
        if d1_client and not st.session_state.get("pk_saved", False):
            try:
                d1_client.save_pk_record(
                    st.session_state.red_name,
                    st.session_state.blue_name,
                    st.session_state.red_score,
                    st.session_state.blue_score,
                    st.session_state.winner,
                    st.session_state.target_score,
                    st.session_state.get("pk_mode", "標準對決")
                )
                st.session_state.pk_saved = True
            except Exception:
                pass
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 原班人馬再戰一場", type="primary", use_container_width=True):
                start_pk_game(st.session_state.pk_mode, st.session_state.pk_table_nums, st.session_state.target_score)
                st.rerun()
        with c2:
            if st.button("⚙️ 重新設定選手與規則", use_container_width=True):
                st.session_state.pk_state = "setup"
                st.rerun()

        # 顯示最近對戰歷史紀錄
        if d1_client:
            st.write("---")
            st.subheader("📜 最近對抗賽戰報 (Cloudflare D1)")
            try:
                history = d1_client.get_pk_recent_matches(5)
                if history:
                    df_pk = pd.DataFrame(history)
                    df_pk = df_pk.rename(columns={
                        "red_name": "紅隊",
                        "blue_name": "藍隊",
                        "red_score": "紅得分",
                        "blue_score": "藍得分",
                        "winner": "獲勝陣營",
                        "game_mode": "題型",
                        "created_at": "對戰時間"
                    })
                    st.dataframe(df_pk, use_container_width=True)
            except Exception:
                pass


# =========================================================================
# 模式二：🎯 單人練習 / 全班投影搶答
# =========================================================================
elif app_mode == "🎯 單人練習 / 全班投影搶答":
    if "game_state" not in st.session_state:
        st.session_state.game_state = "setup"
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "combo" not in st.session_state:
        st.session_state.combo = 0
    if "max_combo" not in st.session_state:
        st.session_state.max_combo = 0
    if "question_idx" not in st.session_state:
        st.session_state.question_idx = 0
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "feedback" not in st.session_state:
        st.session_state.feedback = None
    if "solo_saved" not in st.session_state:
        st.session_state.solo_saved = False
    if "wrong_saved" not in st.session_state:
        st.session_state.wrong_saved = False

    def start_solo_game(mode, table_nums, count):
        st.session_state.solo_mode = mode
        st.session_state.questions = [generate_single_question(mode, table_nums) for _ in range(count)]
        st.session_state.total_questions = count
        st.session_state.question_idx = 0
        st.session_state.score = 0
        st.session_state.combo = 0
        st.session_state.max_combo = 0
        st.session_state.history = []
        st.session_state.feedback = None
        st.session_state.solo_saved = False
        st.session_state.wrong_saved = False
        st.session_state.game_state = "playing"

    def check_solo_answer(user_choice):
        curr_q = st.session_state.questions[st.session_state.question_idx]
        is_correct = (user_choice == curr_q["answer"])
        
        if is_correct:
            st.session_state.score += 10 + (st.session_state.combo * 2)
            st.session_state.combo += 1
            if st.session_state.combo > st.session_state.max_combo:
                st.session_state.max_combo = st.session_state.combo
            st.session_state.feedback = ("correct", f"🎉 答對了！ {curr_q['a']} × {curr_q['b']} = {curr_q['answer']}")
        else:
            st.session_state.combo = 0
            st.session_state.feedback = ("wrong", f"❌ 答錯了！正確答案是 {curr_q['a']} × {curr_q['b']} = {curr_q['answer']}")
        
        st.session_state.history.append({
            "question": f"{curr_q['a']} × {curr_q['b']}",
            "your_choice": user_choice,
            "correct_answer": curr_q["answer"],
            "is_correct": is_correct
        })
        
        st.session_state.question_idx += 1
        if st.session_state.question_idx >= len(st.session_state.questions):
            st.session_state.game_state = "ended"

    st.title("🧮 全班投影 / 個人計時搶答模式")

    if st.session_state.game_state == "setup":
        mode = st.radio("📌 選擇挑戰模式：", ["標準九九乘法 (2~9 隨機)", "指定段數特訓", "進階挑戰 (1~19)"], key="solo_mode_radio")
        selected_tables = [7, 8, 9]
        if mode == "指定段數特訓":
            selected_tables = st.multiselect("選擇加強練習段數：", options=list(range(2, 10)), default=[7, 8, 9], key="solo_tables")
            
        c1, c2 = st.columns(2)
        with c1:
            q_count = st.slider("🎯 題目數量：", min_value=5, max_value=30, value=10, step=5, key="solo_count")
        with c2:
            st.write("")
            st.write("")
            if st.button("🚀 開始計時搶答！", type="primary", use_container_width=True):
                if mode == "指定段數特訓" and not selected_tables:
                    st.error("請選擇段數！")
                else:
                    start_solo_game(mode, selected_tables, q_count)
                    st.rerun()

    elif st.session_state.game_state == "playing":
        curr_idx = st.session_state.question_idx
        curr_q = st.session_state.questions[curr_idx]
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("進度", f"第 {curr_idx + 1} / {st.session_state.total_questions} 題")
        col_b.metric("得分", f"{st.session_state.score} 分")
        combo_str = f"🔥 {st.session_state.combo} 連擊！" if st.session_state.combo > 1 else "—"
        col_c.metric("連擊", combo_str)
        st.progress((curr_idx) / st.session_state.total_questions)
        
        if st.session_state.feedback:
            fb_type, fb_msg = st.session_state.feedback
            if fb_type == "correct":
                st.success(fb_msg)
            else:
                st.error(fb_msg)
                
        st.markdown(f'<div class="big-question">{curr_q["a"]} × {curr_q["b"]} = ?</div>', unsafe_allow_html=True)
        
        opts = curr_q["options"]
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"{opts[0]}", key="s_0", use_container_width=True):
                check_solo_answer(opts[0])
                st.rerun()
            if st.button(f"{opts[2]}", key="s_2", use_container_width=True):
                check_solo_answer(opts[2])
                st.rerun()
        with c2:
            if st.button(f"{opts[1]}", key="s_1", use_container_width=True):
                check_solo_answer(opts[1])
                st.rerun()
            if st.button(f"{opts[3]}", key="s_3", use_container_width=True):
                check_solo_answer(opts[3])
                st.rerun()

    elif st.session_state.game_state == "ended":
        st.balloons()
        st.header("🏁 搶答結束！成績結算")
        total = len(st.session_state.history)
        correct_count = sum(1 for h in st.session_state.history if h["is_correct"])
        accuracy = (correct_count / total * 100) if total > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總分", f"{st.session_state.score} 分")
        c2.metric("答對率", f"{accuracy:.1f} %", f"{correct_count}/{total}")
        c3.metric("最高連擊", f"🔥 {st.session_state.max_combo} 次")
        
        wrong_history = [h for h in st.session_state.history if not h["is_correct"]]
        if wrong_history:
            st.subheader("📝 錯題檢討：")
            for item in wrong_history:
                st.write(f"- ❌ **{item['question']}**（選了 {item['your_choice']}，正解：**{item['correct_answer']}**）")
            
            # 自動收集錯題到 Cloudflare D1
            if d1_client and not st.session_state.get("wrong_saved", False):
                try:
                    d1_client.record_wrong_answers(wrong_history, st.session_state.get("solo_mode", "標準九九乘法"))
                    st.session_state.wrong_saved = True
                except Exception:
                    pass

        # ----------------- 登錄雲端英雄榜 -----------------
        st.write("---")
        st.subheader("🏆 登錄全班英雄榜 (Cloudflare D1)")
        
        if not st.session_state.get("solo_saved", False):
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                p_name = st.text_input("請輸入你的座號或姓名：", key="p_name_input", placeholder="例如：08號 烈火")
            with sc2:
                st.write("")
                st.write("")
                if st.button("📤 送出成績", type="primary", use_container_width=True):
                    if p_name.strip() and d1_client:
                        try:
                            d1_client.save_solo_score(
                                p_name.strip(),
                                st.session_state.get("solo_mode", "標準九九乘法"),
                                st.session_state.score,
                                round(accuracy, 1),
                                st.session_state.max_combo,
                                total
                            )
                            st.session_state.solo_saved = True
                            st.success(f"🎉 太棒了，{p_name}！成績已成功記錄到雲端英雄榜！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"寫入資料庫失敗: {e}")
                    elif not p_name.strip():
                        st.warning("請先輸入座號或姓名喔！")
        else:
            st.success("✅ 本次成績已成功登錄至雲端英雄榜！")

        # ----------------- 顯示全班排行榜 -----------------
        if d1_client:
            st.write("---")
            st.subheader("🌟 全班即時英雄榜 TOP 10")
            try:
                board = d1_client.get_solo_leaderboard(10)
                if board:
                    df = pd.DataFrame(board)
                    col_map = {
                        "player_name": "選手姓名 / 座號",
                        "score": "總得分",
                        "accuracy": "答對率 (%)",
                        "max_combo": "最高連擊",
                        "game_mode": "挑戰模式",
                        "created_at": "挑戰時間"
                    }
                    df = df.rename(columns=col_map)
                    df.index = range(1, len(df) + 1)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.caption("目前英雄榜尚無資料，快成為第一位登錄的挑戰者吧！")
            except Exception:
                pass
                
        st.write("")
        if st.button("🔄 再玩一次", use_container_width=True):
            st.session_state.game_state = "setup"
            st.rerun()
