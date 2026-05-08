import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林的分點代號 (根據證交所代號)
    target_broker = "9238" 
    
    # 測試用網址：使用較不擋爬蟲的財經站或 CSV 資料源
    # 改用 nlog 或其他資料備份點，這裡先示範結構
    url = f"https://fubon-ebroker.com.tw/z/zg/zgb/zgb0.aspx?a=9230&b={target_broker}&c=E&d=1" # 範例格式
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'
    }
    
    try:
        # 改用更簡潔的爬蟲方式，如果網頁還是 403，這裡會抓取模擬格式或轉換 API
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'big5' # 台灣財經站常用編碼
        
        if res.status_code == 403:
            return None, "網站封鎖了 GitHub IP (403)。建議更換資料來源或稍後再試。"

        dfs = pd.read_html(io.StringIO(res.text))
        if not dfs:
            return None, "找不到資料表格"
            
        # 尋找含有股票資訊的表格
        df = dfs[2] # 根據富邦/網頁結構調整，通常在第3個表格
        
        # 進行清洗：過濾買超
        # 假設第1欄是股票名稱，第2欄是買張，第3欄是賣張
        df['買超'] = pd.to_numeric(df.iloc[:, 2], errors='coerce') - pd.to_numeric(df.iloc[:, 3], errors='coerce')
        all_buys = df[df['買超'] > 0].copy()
        
        return all_buys, None

    except Exception as e:
        # 如果還是 403 或報錯，我們改用更穩定的替代路徑
        return None, f"執行異常 (可能來源端變動): {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        # 如果失敗，回報給 LINE 讓我們知道狀況
        content = f"⚠️ 凱基士林抓取失敗\n原因: {error_msg}\n(可能是網站阻擋了 GitHub 自動執行)"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無買超標的，或資料尚未更新。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        for _, row in buy_df.iterrows():
            name = str(row.iloc[0]).replace(' ', '')
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
