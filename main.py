import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林代號：9238
    # 使用 NLOG 或備份資料源，這些站點對自動化程式較友善
    url = "https://nlog.cc/t/stock/broker/9238" 
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200:
            return None, f"連線失敗，狀態碼: {res.status_code}"

        # 讀取 HTML 表格
        dfs = pd.read_html(io.StringIO(res.text))
        if not dfs:
            return None, "找不到資料表格"
            
        # NLOG 的結構中，通常第一個表格是買超排行
        df = dfs[0]
        
        # 清洗資料：過濾買超張數 > 0
        # 欄位通常為：股票名稱 (index 0), 買超 (index 1)
        # 我們將資料轉為數值後過濾
        df.columns = ['股票', '買超', '賣超', '合計'] # 根據實際結構命名
        df['買超'] = pd.to_numeric(df['買超'], errors='coerce').fillna(0)
        
        all_buys = df[df['買超'] > 0].copy()
        
        return all_buys, None

    except Exception as e:
        return None, f"抓取異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 凱基士林資料更新失敗\n原因: {error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無買超標的。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        # 取前 50 筆（避免訊息過長導致 LINE 拒收）
        for _, row in buy_df.head(50).iterrows():
            name = str(row['股票']).split(' ')[0] # 去除多餘空格
            amount = int(row['買超'])
            content += f"✅ {name}: +{amount}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    df, err = get_kgi_shilin_real_data()
    send_line_message(df, err)
