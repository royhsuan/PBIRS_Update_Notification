import os
import base64
import requests
import json
# 換成新版模組
from google import genai
from google.genai import types

# 配置
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_URL = "https://api.github.com/repos/MicrosoftDocs/powerbi-docs/contents/powerbi-docs/report-server/changelog.md"
STATE_FILE = "last_version.json"

def run_monitor():
    # 1. 抓取微軟更新文件
    resp = requests.get(GITHUB_URL)
    gh_data = resp.json()
    current_sha = gh_data['sha']
    
    # 2. 讀取上次紀錄的狀態
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {"sha": ""}

    # 3. 比對 SHA
    if state.get("sha") == current_sha:
        print("內容未變動，結束執行。")
        return False

    # 4. 內容有變，交給 Gemini 解析
    print("發現新內容，正在解析...")
    md_text = base64.b64decode(gh_data['content']).decode('utf-8')
    
    # 初始化新版 Client
    client = genai.Client(api_key=GEMINI_KEY)
    
    # 【重點】如果你在 2.0 遇到 Limit 0，請先試著改用 'gemini-1.5-flash'
    target_model = 'gemini-2.5-flash' 
    
    prompt = f"請解析此 Power BI 更新日誌並以 JSON 格式回傳最新版本資訊(version, release_date, description): {md_text[:5000]}"
    
    try:
        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
            ),
        )
        # 新版 SDK 直接用 parsed 或從 text 拿
        new_data = json.loads(response.text)
        
    except Exception as e:
        print(f"AI 解析階段出錯，可能是配額問題：{str(e)}")
        raise 
    
    # 5. 更新狀態檔案
    new_data["sha"] = current_sha
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)
    
    print(f"成功擷取新版本: {new_data.get('version', 'Unknown')}")
    return True

if __name__ == "__main__":
    run_monitor()
