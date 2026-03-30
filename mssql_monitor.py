import os
import base64
import requests
import json
import datetime
from google import genai
from google.genai import types

# 配置
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
# 這是微軟官方維護「所有 SQL 版本最新狀態」的 Markdown 路徑
SQL_GITHUB_URL = "https://api.github.com/repos/MicrosoftDocs/sql-docs/contents/docs/database-engine/install-windows/latest-updates-for-microsoft-sql-server.md"
STATE_FILE = "mssql_versions.json"

def run_sql_monitor():
    now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] === 開始執行 MSSQL 版本監控 ===")

    try:
        # 1. 抓取 GitHub 原始碼
        resp = requests.get(SQL_GITHUB_URL)
        gh_data = resp.json()
        current_sha = gh_data['sha']

        # 2. 比對上次紀錄
        last_sha = ""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                if isinstance(old_data, list) and len(old_data) > 0:
                    # 假設我們把 SHA 存在 meta 資訊裡
                    last_sha = old_data[0].get("_metadata", {}).get("sha", "")

        if last_sha == current_sha:
            print(f"[{now}] MSSQL 文件無變動，略過解析。")
            return

        # 3. 交給 Gemini 解析複雜表格
        print(f"[{now}] 偵測到 MSSQL 文件更新，正在解析各版本 CU...")
        md_text = base64.b64decode(gh_data['content']).decode('utf-8')
        
        client = genai.Client(api_key=GEMINI_KEY)
        
        prompt = f"""
        你是一位資深的 SQL Server DBA。請解析以下 Markdown 文件中的 SQL Server 最新更新表格。
        
        要求：
        1. 提取 2022, 2019, 2017, 2016 等主流版本的最新更新。
        2. 每個版本請包含：大版本名稱 (Product version)、最新更新名稱 (Latest update)、Build 號碼、發布日期。
        3. 將結果整理為 JSON 陣列。
        4. 另外在陣列最後一個物件加入 _metadata，包含檢查時間。

        文件內容：
        {md_text[:15000]}
        """
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.0)
        )
        
        new_versions = json.loads(response.text)
        
        # 加入 SHA 紀錄
        meta_info = {"_metadata": {"sha": current_sha, "last_checked": now}}
        if isinstance(new_versions, list):
            new_versions.insert(0, meta_info)
        
        # 4. 儲存結果
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_versions, f, indent=4, ensure_ascii=False)
            
        print(f"[{now}] MSSQL 版本庫已更新。")

    except Exception as e:
        print(f"[{now}] 執行出錯: {e}")

if __name__ == "__main__":
    run_monitor_sql()
