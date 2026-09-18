import os
import json
import datetime
import requests
import streamlit as st

LOCAL_DB_FILE = os.path.join(os.path.dirname(__file__), "local_game_data.json")

def _load_local_data():
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"solo_records": [], "pk_records": [], "wrong_answers": []}

def _save_local_data(data):
    try:
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 從 Streamlit secrets 或本機環境變數讀取 Cloudflare 設定
def get_config():
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
            return None
    except Exception:
        return None

# ----------------- 專屬業務邏輯函式 -----------------

def save_solo_score(player_name: str, game_mode: str, score: int, accuracy: float, max_combo: int, total_questions: int, total_time: float = 0.0):
    """儲存單人/全班搶答成績（含時間因素）"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 儲存至本地備援檔案
    local_data = _load_local_data()
    local_data.setdefault("solo_records", []).append({
        "player_name": player_name,
        "game_mode": game_mode,
        "score": score,
        "total_time": round(total_time, 1),
        "accuracy": accuracy,
        "max_combo": max_combo,
        "total_questions": total_questions,
        "created_at": now_str
    })
    _save_local_data(local_data)

    # 2. 同步至 Cloudflare D1（若有設定 Token）
    # 嘗試寫入含 total_time 的欄位，若失敗則寫入基本欄位
    sql_with_time = """
    INSERT INTO solo_records (player_name, game_mode, score, accuracy, max_combo, total_questions, total_time)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    res = execute_d1_query(sql_with_time, [player_name, game_mode, score, accuracy, max_combo, total_questions, round(total_time, 1)])
    if res is None:
        sql_fallback = """
        INSERT INTO solo_records (player_name, game_mode, score, accuracy, max_combo, total_questions)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        execute_d1_query(sql_fallback, [player_name, game_mode, score, accuracy, max_combo, total_questions])

    return True

def get_solo_leaderboard(limit: int = 10):
    """取得單人搶答英雄榜（綜合『總分高』與『時間短』進行排名）"""
    # 嘗試從 D1 取得
    sql = """
    SELECT player_name, game_mode, score, accuracy, max_combo, total_time, created_at
    FROM solo_records
    ORDER BY score DESC, total_time ASC, accuracy DESC, max_combo DESC
    LIMIT ?;
    """
    d1_res = execute_d1_query(sql, [limit])
    
    if d1_res is not None and len(d1_res) > 0:
        return d1_res

    # 若 D1 無資料或未連線，從本地檔案載入並依據『總分降冪、時間升冪、正確率降冪』排名
    local_data = _load_local_data()
    records = local_data.get("solo_records", [])
    if not records:
        return []
    
    # 排序核心規則：總分由大到小，若同分則耗時由短到長，再比正確率
    sorted_records = sorted(
        records,
        key=lambda r: (
            -r.get("score", 0),
            r.get("total_time", 9999.0),
            -r.get("accuracy", 0),
            -r.get("max_combo", 0)
        )
    )
    return sorted_records[:limit]

def save_pk_record(red_name: str, blue_name: str, red_score: int, blue_score: int, winner: str, target_score: int, game_mode: str):
    """儲存雙人對戰紀錄"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 本地備援
    local_data = _load_local_data()
    local_data.setdefault("pk_records", []).append({
        "red_name": red_name,
        "blue_name": blue_name,
        "red_score": red_score,
        "blue_score": blue_score,
        "winner": winner,
        "target_score": target_score,
        "game_mode": game_mode,
        "created_at": now_str
    })
    _save_local_data(local_data)

    # 雲端同步
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
    d1_res = execute_d1_query(sql, [limit])
    if d1_res is not None and len(d1_res) > 0:
        return d1_res

    local_data = _load_local_data()
    records = local_data.get("pk_records", [])
    return list(reversed(records))[:limit]

def record_wrong_answers(wrong_list: list, game_mode: str):
    """批次記錄學生答錯的題目（供錯題診斷分析）"""
    local_data = _load_local_data()
    existing_wrongs = local_data.setdefault("wrong_answers", [])
    
    for item in wrong_list:
        existing_wrongs.append({
            "question": item.get("question", ""),
            "chosen_answer": item.get("your_choice", 0),
            "correct_answer": item.get("correct_answer", 0),
            "game_mode": game_mode
        })
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
    _save_local_data(local_data)

def get_top_wrong_questions(limit: int = 5):
    """取得全班最容易出錯的熱門題目排行榜"""
    sql = """
    SELECT question, COUNT(*) as error_count, correct_answer
    FROM wrong_answers
    GROUP BY question
    ORDER BY error_count DESC
    LIMIT ?;
    """
    d1_res = execute_d1_query(sql, [limit])
    if d1_res is not None and len(d1_res) > 0:
        return d1_res

    local_data = _load_local_data()
    wrongs = local_data.get("wrong_answers", [])
    if not wrongs:
        return []

    counts = {}
    answers = {}
    for w in wrongs:
        q = w.get("question", "")
        counts[q] = counts.get(q, 0) + 1
        answers[q] = w.get("correct_answer", "")

    sorted_q = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"question": q, "error_count": c, "correct_answer": answers.get(q, "")} for q, c in sorted_q]
