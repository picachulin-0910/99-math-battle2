import os
import requests
import streamlit as st

# 從 Streamlit secrets 或本機環境變數讀取 Cloudflare 設定
def get_config():
    # 優先從 st.secrets 取得（Streamlit Cloud 部署用）
    account_id = None
    database_id = None
    api_token = None
    
    try:
        if hasattr(st, "secrets"):
            account_id = st.secrets.get("CLOUDFLARE_ACCOUNT_ID")
            database_id = st.secrets.get("CLOUDFLARE_DATABASE_ID")
            api_token = st.secrets.get("CLOUDFLARE_API_TOKEN")
    except Exception:
        pass

    # 備援從環境變數取得
    account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "552a6685ffeecbcef95ea22dad129efc")
    database_id = database_id or os.getenv("CLOUDFLARE_DATABASE_ID", "6122857e-c49b-4217-9048-50c37f1d9f2b")
    api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN", "")

    return account_id, database_id, api_token

def execute_d1_query(sql: str, params: list = None):
    """執行 Cloudflare D1 查詢或寫入"""
    account_id, database_id, api_token = get_config()
    
    if not api_token:
        # 若未設定 Token，給予清楚友善的提示
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {"sql": sql}
    if params:
        payload["params"] = params
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        if data.get("success"):
            results = data.get("result", [{}])[0].get("results", [])
            return results
        else:
            errors = data.get("errors", [])
            st.error(f"資料庫存取失敗: {errors}")
            return None
    except Exception as e:
        st.error(f"連線 Cloudflare D1 發生異常: {e}")
        return None

# ----------------- 專屬業務邏輯函式 -----------------

def save_solo_score(player_name: str, game_mode: str, score: int, accuracy: float, max_combo: int, total_questions: int):
    """儲存單人/全班搶答成績"""
    sql = """
    INSERT INTO solo_records (player_name, game_mode, score, accuracy, max_combo, total_questions)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    return execute_d1_query(sql, [player_name, game_mode, score, accuracy, max_combo, total_questions])

def get_solo_leaderboard(limit: int = 10):
    """取得單人搶答英雄榜（依分數由高至低）"""
    sql = """
    SELECT player_name, game_mode, score, accuracy, max_combo, created_at
    FROM solo_records
    ORDER BY score DESC, accuracy DESC, max_combo DESC
    LIMIT ?;
    """
    return execute_d1_query(sql, [limit])

def save_pk_record(red_name: str, blue_name: str, red_score: int, blue_score: int, winner: str, target_score: int, game_mode: str):
    """儲存雙人對戰紀錄"""
    sql = """
    INSERT INTO pk_records (red_name, blue_name, red_score, blue_score, winner, target_score, game_mode)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    return execute_d1_query(sql, [red_name, blue_name, red_score, blue_score, winner, target_score, game_mode])

def get_pk_recent_matches(limit: int = 10):
    """取得最近的對抗賽戰報"""
    sql = """
    SELECT red_name, blue_name, red_score, blue_score, winner, game_mode, created_at
    FROM pk_records
    ORDER BY id DESC
    LIMIT ?;
    """
    return execute_d1_query(sql, [limit])

def record_wrong_answers(wrong_list: list, game_mode: str):
    """批次記錄學生答錯的題目（供錯題診斷分析）"""
    for item in wrong_list:
        sql = """
        INSERT INTO wrong_answers (question, chosen_answer, correct_answer, game_mode)
        VALUES (?, ?, ?, ?);
        """
        execute_d1_query(sql, [
            item.get("question", ""),
            item.get("your_choice", 0),
            item.get("correct_answer", 0),
            game_mode
        ])

def get_top_wrong_questions(limit: int = 5):
    """取得全班最容易出錯的熱門題目排行榜"""
    sql = """
    SELECT question, COUNT(*) as error_count, correct_answer
    FROM wrong_answers
    GROUP BY question
    ORDER BY error_count DESC
    LIMIT ?;
    """
    return execute_d1_query(sql, [limit])
