import os
import base64
import requests
import json
from google import genai
from google.genai import types

# 配置
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_URL = "https://api.github.com/repos/MicrosoftDocs/powerbi-docs/contents/powerbi-docs/report-server/changelog.md"
STATE_FILE = "last_version.json"

def run_monitor():
    # 1. 抓取微軟原始文件
    print("正在獲取最新 Changelog...")
    resp = requests.get(GITHUB_URL)
    gh_data = resp.json()
    current_sha = gh_data['sha']
    
    # 2. 讀取狀態檔案
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)

    # 3. 比對 SHA (節省 Quota)
    if state.get("sha") == current_sha:
        print("內容未變動，略過解析。")
        return False

    # 4. 內容有變，模擬官網格式解析
    print("發現更新！正在依照官網風格生成摘要...")
    md_text = base64.b64decode(gh_data['content']).decode('utf-8')
    
    client = genai.Client(api_key=GEMINI_KEY)
    
    # 指令優化：模仿 Microsoft Learn 的呈現方式
    prompt = f"""
    請閱讀以下 Power BI Report Server 更新日誌，並針對「最新的一個版本」擷取資訊。
    輸出必須為 JSON 格式，包含以下精確欄位：
    
    1. version: 完整的版本與 Build 號。
    2. release_date: 發布日期。
    3. report_server_updates: 列出該版本中「Power BI Report Server」的所有更新要點 (繁中)。
    4. desktop_updates: 列出該版本中「Power BI Desktop (RS 版)」的所有更新要點 (繁中)。
    5. download_url: 官網下載網址 (通常在文末或標題旁)。

    內容如下：
    {md_text[:6000]}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.0 # 確保技術文件的嚴確性
            ),
        )
        new_data = json.loads(response.text)
        
    except Exception as e:
        print(f"解析失敗: {e}")
        raise 
    
    # 5. 更新狀態檔案
    new_data["sha"] = current_sha
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)
    
    print(f"解析成功！當前版本: {new_data.get('version')}")
    return True

if __name__ == "__main__":
    run_monitor()
