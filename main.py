import os
import requests
import pandas as pd

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林代號 9238
    url = "https://www.wantgoo.com/stock/astock/agentbuy?agentId=9238"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return None, f"網頁連線失敗 (Code: {res.status_code})"

        # 使用 pandas 解析網頁中的表格
        # flavor='bs4' 搭配 beautifulsoup4 使用
        dfs = pd.read_html(res.text)
        if not dfs:
            return None, "網頁內找不到資料表格"
        
        df = dfs[0] 
        
        # 過濾買超張數 > 0 的股票
        # 假設：第 0 欄是股票，第 2 欄是買超張數 (這在大多數財經站是標準格式)
        all_buys = df[df.iloc[:, 2] > 0] 
        return all_buys, None

    except Exception as e:
        return None, f"執行異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"❌ 系統錯誤通知:\n{error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無買超標的。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        for _, row in buy_df.iterrows():
            # 取得股票名稱與買超張數
            name = str(row.iloc[0])
            amount = str(row.iloc[2])
            content += f"✅ {name}: +{amount}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"LINE Status: {response.status_code}, Response: {response.text}")

if __name__ == "__main__":
    df, err = get_kgi_shilin_real_data()
    send_line_message(df, err)
