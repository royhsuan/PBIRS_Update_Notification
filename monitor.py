import os
import base64
import requests
import json
import google.generativeai as genai

# 1. 配置
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_URL = "https://api.github.com/repos/MicrosoftDocs/powerbi-docs/contents/powerbi-docs/report-server/changelog.md"

def get_pbirs_updates():
    # 抓取 GitHub 內容
    print("正在抓取 Microsoft GitHub 更新日誌...")
    resp = requests.get(GITHUB_URL)
    if resp.status_code != 200:
        print(f"GitHub 抓取失敗: {resp.status_code}")
        return
    
    # 解碼 Base64
    content_b64 = resp.json()['content']
    markdown_text = base64.b64decode(content_b64).decode('utf-8')

    # 設定 Gemini
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""
    你是一個專業的 Power BI 專家。請分析以下更新日誌並提取『最新的一個版本』。
    請嚴格輸出 JSON 格式，包含：version, release_date, description (繁體中文摘要), download_link。
    
    內容：
    {markdown_text[:5000]}  # 避免內容過長，取前5000字
    """

    # 呼叫 Gemini
    print("正在交由 Gemini 3 Flash 分析...")
    response = model.generate_content(
        prompt, 
        generation_config={"response_mime_type": "application/json"}
    )
    
    update_info = json.loads(response.text)
    print("\n[ 發現最新版本資訊 ]")
    print(json.dumps(update_info, indent=4, ensure_ascii=False))
    
    # 這裡可以加入寫入 MSSQL 的邏輯 (例如使用 pyodbc)
    return update_info

if __name__ == "__main__":
    get_pbirs_updates()
