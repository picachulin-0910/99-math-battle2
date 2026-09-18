import streamlit as st
import random
import time
import d1_client

# 設定網頁標題與排版
st.set_page_config(
    page_title="九九乘法大對決 🎯 雙人/班級版",
    page_icon="🧮",
    layout="wide"
)

# 自訂 CSS：緊湊單頁面無捲動設計、超大題庫與按鈕、倒數計時進度條
st.markdown("""
<style>
    /* 1. 頁面邊距極度精簡，消除上下捲動 */
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        height: 2rem !important;
        background: transparent !important;
    }
    
    /* 2. PK 雙人對抗模式緊湊卡片 */
    .pk-card-red {
        background: linear-gradient(135deg, #FEE2E2, #FECACA);
        border: 2px solid #EF4444;
        border-radius: 12px;
        padding: 6px 14px;
        text-align: center;
    }
    .pk-card-blue {
        background: linear-gradient(135deg, #DBEAFE, #BFDBFE);
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 6px 14px;
        text-align: center;
    }
    .pk-score-badge {
        font-size: 36px;
        font-weight: 900;
        line-height: 1.1;
        margin: 2px 0;
    }
    
    /* 3. 超大題目顯示框（PK 模式專用緊湊版，高度適中但字體極大） */
    .pk-question-box {
        font-size: 64px !important;
        font-weight: 900;
        text-align: center;
        color: #0F172A;
        background: linear-gradient(135deg, #F8FAFC, #E2E8F0);
        padding: 6px 10px;
        border-radius: 14px;
        margin: 4px 0 6px 0;
        border: 3px solid #CBD5E1;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        line-height: 1.15;
    }

    /* 單人模式題目框 */
    .solo-question-box {
        font-size: 70px !important;
        font-weight: 900;
        text-align: center;
        color: #0F172A;
        background: linear-gradient(135deg, #F8FAFC, #E2E8F0);
        padding: 10px 16px;
        border-radius: 16px;
        margin: 6px 0 10px 0;
        border: 3px solid #CBD5E1;
        box-shadow: 0 6px 14px rgba(0,0,0,0.06);
        line-height: 1.15;
    }

    /* 4. 4 個選項按鈕：高度 85px，字體 60px 超醒目且不超出畫面 */
    div[data-testid="stColumn"] .stButton button {
        min-height: 85px !important;
        border-radius: 16px !important;
        border: 3px solid #94A3B8 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
        transition: all 0.12s ease-in-out !important;
        margin: 3px 0 !important;
        padding: 4px !important;
    }
    div[data-testid="stColumn"] .stButton button p {
        font-size: 60px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        color: #0F172A !important;
    }
    div[data-testid="stColumn"] .stButton button:hover {
        border-color: #2563EB !important;
        background-color: #F0FDF4 !important;
        transform: scale(1.02) !important;
    }
    div[data-testid="stColumn"] .stButton button:active {
        transform: scale(0.96) !important;
    }

    /* 5. 一般功能/設定/中止按鈕 */
    div[data-testid="stVerticalBlock"] > .stButton button {
        min-height: 48px !important;
        border-radius: 10px !important;
    }
    div[data-testid="stVerticalBlock"] > .stButton button p {
        font-size: 20px !important;
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
# 側邊欄：主模式切換與全班英雄榜
# =========================================================================
st.sidebar.title("🎮 遊戲模式選擇")
app_mode = st.sidebar.radio(
    "選擇要進行的活動：",
    ["⚔️ 雙人 / 分組對抗 PK 賽", "🎯 單人練習 / 全班投影搶答"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **教學小撇步**：\n"
    "- **雙人對抗**：兩位同學站在電子白板兩側，免滾動單頁面即時搶答！\n"
    "- **單人挑戰**：每題限時 10 秒，速度越快加分越多，排行榜比拼『高分＋極速』！"
)

# 側邊欄：排行榜展示（納入時間因素）
with st.sidebar.expander("🏆 全班即時英雄榜 TOP 5", expanded=True):
    top_board = d1_client.get_solo_leaderboard(5)
    if top_board:
        for idx, row in enumerate(top_board):
            t_sec = row.get('total_time', 0.0)
            t_str = f"⏱️ {t_sec:.1f}s" if t_sec > 0 else ""
            st.markdown(f"**#{idx+1} {row.get('player_name', '')}** — `{row.get('score', 0)} 分` ({t_str} / {row.get('accuracy', 0)}%)")
    else:
        st.write("尚無榜單資料，快來登錄第一筆！")

with st.sidebar.expander("📊 全班高頻錯題熱點 TOP 5", expanded=False):
    top_wrongs = d1_client.get_top_wrong_questions(5)
    if top_wrongs:
        for w in top_wrongs:
            st.markdown(f"⚠️ **{w.get('question', '')}** （答錯 {w.get('error_count', 0)} 次，正解：`{w.get('correct_answer', '')}`）")
    else:
        st.write("目前尚無錯題紀錄，大家都很棒！")

# =========================================================================
# 模式一：⚔️ 雙人 / 分組對抗 PK 賽（單頁面免滾動設計）
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
        st.subheader("⚔️ 雙人分組對抗 PK 賽 — 賽事設定")
        
        col_r, col_b = st.columns(2)
        with col_r:
            st.markdown('<div class="pk-card-red"><h4>🔴 紅隊（左方陣營）</h4></div>', unsafe_allow_html=True)
            red_name = st.text_input("紅隊名稱 / 選手姓名：", value="紅隊 迅猛龍", key="input_red")
        with col_b:
            st.markdown('<div class="pk-card-blue"><h4>🔵 藍隊（右方陣營）</h4></div>', unsafe_allow_html=True)
            blue_name = st.text_input("藍隊名稱 / 選手姓名：", value="藍隊 烈火鷹", key="input_blue")

        st.session_state.red_name = red_name
        st.session_state.blue_name = blue_name

        c1, c2 = st.columns(2)
        with c1:
            pk_mode = st.radio("📌 對戰題型：", ["標準九九乘法 (2~9)", "指定段數特訓", "進階挑戰 (1~19)"], key="pk_mode_radio")
            selected_tables = [7, 8, 9]
            if pk_mode == "指定段數特訓":
                selected_tables = st.multiselect("選擇段數：", options=list(range(2, 10)), default=[7, 8, 9])
        with c2:
            target_pts = st.select_slider("🏆 勝利條件（先搶到幾分獲勝）：", options=[3, 5, 7, 10, 15], value=5)
            st.write("")
            if st.button("🔥 雙方就位，開戰！", type="primary", use_container_width=True):
                if pk_mode == "指定段數特訓" and not selected_tables:
                    st.error("請至少選擇一個段數！")
                else:
                    start_pk_game(pk_mode, selected_tables, target_pts)
                    st.rerun()

    # --- PK 對戰進行頁（單頁面零捲動佈局）---
    elif st.session_state.pk_state == "playing":
        # 1. 頂部兩隊比分進度列
        col_left, col_mid, col_right = st.columns([5, 2, 5])
        with col_left:
            st.markdown(f'''
            <div class="pk-card-red">
                <span style="font-size:18px; font-weight:bold; color:#991B1B;">🔴 {st.session_state.red_name}</span>
                <div class="pk-score-badge" style="color:#DC2626;">{st.session_state.red_score} <span style="font-size:16px; color:#6B7280;">/ {st.session_state.target_score} 分</span></div>
            </div>
            ''', unsafe_allow_html=True)
            st.progress(min(1.0, st.session_state.red_score / st.session_state.target_score))
        
        with col_mid:
            st.markdown(f'''
            <div style="text-align:center; padding-top:6px;">
                <span style="font-size:22px; font-weight:900; color:#D97706;">⚡ VS ⚡</span><br>
                <span style="font-size:13px; color:#64748B;">先達 <b>{st.session_state.target_score} 分</b> 勝</span>
            </div>
            ''', unsafe_allow_html=True)

        with col_right:
            st.markdown(f'''
            <div class="pk-card-blue">
                <span style="font-size:18px; font-weight:bold; color:#1E40AF;">🔵 {st.session_state.blue_name}</span>
                <div class="pk-score-badge" style="color:#2563EB;">{st.session_state.blue_score} <span style="font-size:16px; color:#6B7280;">/ {st.session_state.target_score} 分</span></div>
            </div>
            ''', unsafe_allow_html=True)
            st.progress(min(1.0, st.session_state.blue_score / st.session_state.target_score))

        # 2. 即時戰況廣播（單行緊湊）
        if st.session_state.pk_msg:
            st.markdown(f'<div style="text-align:center; font-size:15px; font-weight:bold; color:#1E293B; background:#FEF3C7; padding:2px 8px; border-radius:6px; margin:2px 0;">{st.session_state.pk_msg}</div>', unsafe_allow_html=True)

        # 3. 中央超大題目（緊湊無浪費空間）
        q = st.session_state.pk_q
        st.markdown(f'<div class="pk-question-box">{q["a"]} × {q["b"]} = ?</div>', unsafe_allow_html=True)

        # 4. 左右兩側搶答按鈕（2x2 格局，按鍵高度 85px，字體 60px）
        col_r_btns, col_spacer, col_b_btns = st.columns([5, 1, 5])
        opts = q["options"]

        with col_r_btns:
            st.markdown('<div style="font-size:16px; font-weight:bold; color:#DC2626; text-align:center; margin-bottom:2px;">👈 🔴 紅隊點選區</div>', unsafe_allow_html=True)
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
            st.markdown('<div style="font-size:16px; font-weight:bold; color:#2563EB; text-align:center; margin-bottom:2px;">👉 🔵 藍隊點選區</div>', unsafe_allow_html=True)
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

        # 5. 底部微型中止控制按鈕
        st.write("")
        col_abort, _ = st.columns([2, 10])
        with col_abort:
            if st.button("⏹️ 中止比賽", type="secondary"):
                st.session_state.pk_state = "setup"
                st.rerun()

    # --- PK 勝利結算頁 ---
    elif st.session_state.pk_state == "ended":
        st.balloons()
        st.subheader("🏆 比賽結束！冠軍出爐！")

        if not st.session_state.get("pk_saved", False):
            d1_client.save_pk_record(
                st.session_state.red_name,
                st.session_state.blue_name,
                st.session_state.red_score,
                st.session_state.blue_score,
                st.session_state.winner,
                st.session_state.target_score,
                st.session_state.pk_mode
            )
            st.session_state.pk_saved = True
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FEF3C7, #FDE68A); padding: 30px; border-radius: 18px; text-align: center; border: 3px solid #F59E0B; margin: 15px 0;">
            <h1 style="font-size: 52px; color: #B45309; margin: 0;">👑 恭喜 {st.session_state.winner} 榮獲冠軍！ 👑</h1>
            <p style="font-size: 24px; color: #78350F; font-weight: bold; margin: 10px 0 0 0;">最終比分： 🔴 {st.session_state.red_score} 比 🔵 {st.session_state.blue_score}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 原班人馬再戰一場", type="primary", use_container_width=True):
                start_pk_game(st.session_state.pk_mode, st.session_state.pk_table_nums, st.session_state.target_score)
                st.rerun()
        with c2:
            if st.button("⚙️ 重新設定選手與規則", use_container_width=True):
                st.session_state.pk_state = "setup"
                st.rerun()

        st.write("---")
        st.subheader("📜 最近對戰戰報")
        pk_history = d1_client.get_pk_recent_matches(5)
        if pk_history:
            formatted_pk = []
            for r in pk_history:
                formatted_pk.append({
                    "獲勝隊伍": r.get("winner", ""),
                    "🔴 紅隊": f"{r.get('red_name', '')} ({r.get('red_score', 0)}分)",
                    "🔵 藍隊": f"{r.get('blue_name', '')} ({r.get('blue_score', 0)}分)",
                    "題型模式": r.get("game_mode", ""),
                    "對戰時間": r.get("created_at", "")[:19] if r.get("created_at") else ""
                })
            st.dataframe(formatted_pk, use_container_width=True)

# =========================================================================
# 模式二：🎯 單人練習 / 全班投影搶答（每題限時 10 秒與時間排名）
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
    if "q_start_time" not in st.session_state:
        st.session_state.q_start_time = time.time()

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
        st.session_state.q_start_time = time.time()
        st.session_state.game_state = "playing"

    def handle_solo_timeout():
        """處理 10 秒時間到的超時邏輯"""
        curr_idx = st.session_state.question_idx
        if curr_idx >= len(st.session_state.questions):
            return
        curr_q = st.session_state.questions[curr_idx]
        st.session_state.combo = 0
        st.session_state.feedback = ("wrong", f"⏰ 時間到（超過 10 秒未答）！正確答案是：{curr_q['a']} × {curr_q['b']} = {curr_q['answer']}")
        st.session_state.history.append({
            "question": f"{curr_q['a']} × {curr_q['b']}",
            "your_choice": "⏰ 超時未答",
            "correct_answer": curr_q["answer"],
            "is_correct": False,
            "time_spent": 10.0
        })
        st.session_state.question_idx += 1
        if st.session_state.question_idx >= len(st.session_state.questions):
            st.session_state.game_state = "ended"
        else:
            st.session_state.q_start_time = time.time()

    def check_solo_answer(user_choice):
        curr_idx = st.session_state.question_idx
        if curr_idx >= len(st.session_state.questions):
            return
        curr_q = st.session_state.questions[curr_idx]
        
        elapsed = time.time() - st.session_state.q_start_time
        if elapsed > 10.5:
            handle_solo_timeout()
            st.rerun()
            return

        time_spent = round(min(10.0, elapsed), 1)
        is_correct = (user_choice == curr_q["answer"])
        
        if is_correct:
            # 答對得分：基礎10分 + 速度加成(剩餘秒數×2) + 連擊加成(連擊×2)
            time_left = max(0.0, 10.0 - elapsed)
            time_bonus = int(time_left * 2)
            combo_bonus = st.session_state.combo * 2
            earned = 10 + time_bonus + combo_bonus
            st.session_state.score += earned
            st.session_state.combo += 1
            if st.session_state.combo > st.session_state.max_combo:
                st.session_state.max_combo = st.session_state.combo
            st.session_state.feedback = ("correct", f"🎉 答對了！耗時 {time_spent} 秒（+{earned}分：基礎10 + 速度{time_bonus} + 連擊{combo_bonus}）")
        else:
            st.session_state.combo = 0
            st.session_state.feedback = ("wrong", f"❌ 答錯了！耗時 {time_spent} 秒，正確答案是 {curr_q['a']} × {curr_q['b']} = {curr_q['answer']}")
        
        st.session_state.history.append({
            "question": f"{curr_q['a']} × {curr_q['b']}",
            "your_choice": user_choice,
            "correct_answer": curr_q["answer"],
            "is_correct": is_correct,
            "time_spent": time_spent
        })
        
        st.session_state.question_idx += 1
        if st.session_state.question_idx >= len(st.session_state.questions):
            st.session_state.game_state = "ended"
        else:
            st.session_state.q_start_time = time.time()

    # --- 獨立 Fragment：10 秒倒數計時元件（每秒局部刷新，保證按鈕點擊完全不延遲）---
    @st.fragment(run_every=1)
    def render_solo_countdown():
        if st.session_state.game_state != "playing":
            return
        
        elapsed = time.time() - st.session_state.q_start_time
        remaining = max(0.0, 10.0 - elapsed)
        
        if remaining <= 0.0:
            handle_solo_timeout()
            st.rerun(scope="app")
            return
        
        pct = min(1.0, max(0.0, remaining / 10.0))
        if remaining > 6.0:
            color = "#10B981"
            icon = "🟢"
        elif remaining > 3.0:
            color = "#F59E0B"
            icon = "🟡"
        else:
            color = "#EF4444"
            icon = "🔴"
            
        rem_display = int(remaining) + (1 if (remaining % 1 > 0.05) else 0)
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#F8FAFC; border:2px solid {color}; border-radius:10px; padding:4px 14px; margin:4px 0;">
            <span style="font-size:17px; font-weight:bold; color:{color};">
                {icon} 剩餘時間：<span style="font-size:28px; font-weight:900;">{rem_display}</span> 秒
            </span>
            <span style="font-size:13px; color:#64748B;">（每題限時 10 秒，越快答對分數越高！）</span>
        </div>
        """, unsafe_allow_html=True)
        st.progress(pct)

    # --- 單人設定頁 ---
    if st.session_state.game_state == "setup":
        st.subheader("🧮 個人挑戰 / 全班計時搶答模式")
        st.info("⏱️ **新規則升級**：每一題皆有 **10 秒作答倒數**！答得越快額外獎勵越高，個人排行榜綜合比拼「**總分高＋總耗時少**」！")
        
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
            if st.button("🚀 開始挑戰（每題限時10秒）！", type="primary", use_container_width=True):
                if mode == "指定段數特訓" and not selected_tables:
                    st.error("請選擇段數！")
                else:
                    start_solo_game(mode, selected_tables, q_count)
                    st.rerun()

    # --- 單人遊戲進行中 ---
    elif st.session_state.game_state == "playing":
        curr_idx = st.session_state.question_idx
        curr_q = st.session_state.questions[curr_idx]
        
        # 1. 頂部進度、分數、連擊狀態
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("進度", f"第 {curr_idx + 1} / {st.session_state.total_questions} 題")
        col_b.metric("目前得分", f"{st.session_state.score} 分")
        combo_str = f"🔥 {st.session_state.combo} 連擊！" if st.session_state.combo > 1 else "—"
        col_c.metric("連擊", combo_str)
        
        # 2. 10 秒倒數計時元件
        render_solo_countdown()
        
        # 3. 前一題即時反饋
        if st.session_state.feedback:
            fb_type, fb_msg = st.session_state.feedback
            if fb_type == "correct":
                st.success(fb_msg)
            else:
                st.error(fb_msg)
                
        # 4. 超大題目
        st.markdown(f'<div class="solo-question-box">{curr_q["a"]} × {curr_q["b"]} = ?</div>', unsafe_allow_html=True)
        
        # 5. 4 個超大選項按鈕
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

        st.write("")
        if st.button("⏹️ 中途結束挑戰"):
            st.session_state.game_state = "ended"
            st.rerun()

    # --- 單人結算頁（顯示時間數據與時間加權英雄榜）---
    elif st.session_state.game_state == "ended":
        st.balloons()
        st.header("🏁 挑戰結束！成績結算")
        
        total = len(st.session_state.history)
        correct_count = sum(1 for h in st.session_state.history if h["is_correct"])
        accuracy = (correct_count / total * 100) if total > 0 else 0
        total_time_spent = sum(h.get("time_spent", 0.0) for h in st.session_state.history)
        avg_time = (total_time_spent / total) if total > 0 else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏆 最終總分", f"{st.session_state.score} 分")
        col2.metric("⏱️ 總作答時間", f"{total_time_spent:.1f} 秒", f"平均每題 {avg_time:.1f} 秒")
        col3.metric("🎯 答對率", f"{accuracy:.1f} %", f"{correct_count}/{total} 題")
        col4.metric("🔥 最高連擊", f"{st.session_state.max_combo} 次")
        
        # 錯題檢討
        wrong_history = [h for h in st.session_state.history if not h["is_correct"]]
        if wrong_history:
            st.subheader("📝 錯題與超時檢討：")
            for item in wrong_history:
                st.write(f"- ❌ **{item['question']}**（選了：{item['your_choice']}，耗時：{item.get('time_spent', 0):.1f}s，正解：**{item['correct_answer']}**）")
            
            if not st.session_state.get("wrong_saved", False):
                d1_client.record_wrong_answers(wrong_history, st.session_state.get("solo_mode", "標準九九乘法"))
                st.session_state.wrong_saved = True

        # 登錄全班英雄榜
        st.write("---")
        st.subheader("🎖️ 登錄全班英雄榜")
        if not st.session_state.get("solo_saved", False):
            c_name, c_btn = st.columns([3, 1])
            with c_name:
                p_name = st.text_input("請輸入座號或姓名登錄成績：", placeholder="例如：07號 小明", key="player_name_input")
            with c_btn:
                st.write("")
                st.write("")
                if st.button("📤 登錄成績", type="primary", use_container_width=True):
                    if p_name.strip():
                        d1_client.save_solo_score(
                            p_name.strip(),
                            st.session_state.get("solo_mode", "標準九九乘法"),
                            st.session_state.score,
                            round(accuracy, 1),
                            st.session_state.max_combo,
                            total,
                            total_time_spent
                        )
                        st.session_state.solo_saved = True
                        st.success(f"🎉 太棒了，{p_name.strip()}！成績已成功登錄英雄榜！")
                        st.rerun()
                    else:
                        st.warning("請先輸入姓名或座號！")
        else:
            st.success("✅ 你的成績已成功登錄在全班英雄榜！")

        # 英雄榜顯示（含時間排序）
        st.subheader("🏆 全班即時英雄榜 TOP 10")
        st.caption("💡 **排名機制**：先比較【總得分（越高越好）】；若分數相同，則由【總作答時間（越短越好）】勝出！")
        leaderboard = d1_client.get_solo_leaderboard(10)
        if leaderboard:
            formatted_board = []
            for idx, r in enumerate(leaderboard):
                rank_str = f"🥇 第 {idx+1} 名" if idx == 0 else (f"🥈 第 {idx+1} 名" if idx == 1 else (f"🥉 第 {idx+1} 名" if idx == 2 else f"第 {idx+1} 名"))
                t_val = r.get("total_time", 0.0)
                formatted_board.append({
                    "排名": rank_str,
                    "選手姓名": r.get("player_name", ""),
                    "挑戰題型": r.get("game_mode", ""),
                    "🏆 總得分": f"{r.get('score', 0)} 分",
                    "⏱️ 總作答時間": f"{t_val:.1f} 秒" if t_val > 0 else "—",
                    "🎯 答對率": f"{r.get('accuracy', 0)}%",
                    "🔥 最高連擊": f"{r.get('max_combo', 0)} 次",
                    "完成時間": r.get("created_at", "")[:19] if r.get("created_at") else ""
                })
            st.dataframe(formatted_board, use_container_width=True)
        else:
            st.info("💡 目前尚無排行榜紀錄，趕快成為第一位登錄的好手！")
                
        st.write("")
        if st.button("🔄 再玩一次", type="primary", use_container_width=True):
            st.session_state.game_state = "setup"
            st.rerun()
