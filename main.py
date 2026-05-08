import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林代號 9238。這裡使用「神秘金字塔」或「玩股網」的公開路徑邏輯
    # 這裡示範抓取網頁資料的標準寫法
    url = "https://www.wantgoo.com/stock/astock/agentbuy?agentId=9238"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return None, f"網頁連線失敗，狀態碼：{res.status_code}"

        # 使用 pandas 讀取網頁表格
        dfs = pd.read_html(res.text)
        if not dfs:
            return None, "找不到資料表格"
        
        df = dfs[0] # 通常第一個表格就是買超排行
        
        # 根據實際網頁欄位調整，假設欄位 0 是股票名稱，欄位 2 是買超張數
        # 這裡先過濾出買進的標的
        all_buys = df[df.iloc[:, 2] > 0] 
        return all_buys, None

    except Exception as e:
        return None, f"發生異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"❌ 抓取錯誤: {error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日凱基士林無買超資料。"
    else:
        content = "📋 【凱基士林】今日全部買超清單\n"
        content += "--------------------------\n"
        # 這裡根據實際表格欄位 index 取值，通常 0 是名稱，2 是張數
        for _, row in buy_df.iterrows():
            content += f"✅ {row.iloc[0]}: +{row.iloc[2]}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"LINE 傳送狀態: {response.status_code}, 回傳: {response.text}")

if __name__ == "__main__":
    df, err = get_kgi_shilin_real_data()
    send_line_message(df, err)

