import os
import requests
import pandas as pd
from datetime import datetime

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林代號：9238
    # 直接請求證交所的「當日大戶/分點進出統計」API
    # 注意：證交所 API 通常在 18:30 後才會有當日資料
    
    today = datetime.now().strftime('%Y%m%d')
    # 證交所公開資料 API
    url = "https://www.twse.com.tw/exchangeReport/TWT43U?response=json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        data = res.json()
        
        if data['stat'] != 'OK':
            return None, f"證交所目前未提供資料 (stat: {data['stat']})"

        # 證交所回傳的資料在 'data' 欄位中
        # 欄位說明：[證券代號, 證券名稱, 買進分點代號, 買進分點名稱, 買進張數, ...]
        full_df = pd.DataFrame(data['data'])
        
        # 過濾出買進分點為 9238 (凱基士林) 的資料
        # 假設證交所欄位：index 2 是分點代號, index 3 是分點名稱, index 0 是股票代號, index 4 是買進張數
        kgi_data = full_df[full_df[2] == '9238'].copy()
        
        if kgi_data.empty:
            return pd.DataFrame(), None
            
        # 整理輸出格式
        output_df = kgi_data[[0, 1, 4]].copy()
        output_df.columns = ['代號', '名稱', '張數']
        return output_df, None

    except Exception as e:
        return None, f"API 存取異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 監控回報: {error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無進出標的 (或資料尚未產製)。"
    else:
        content = f"📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        for _, row in buy_df.iterrows():
            content += f"✅ {row['代號']} {row['名稱']}: +{row['張數']}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    df, err = get_kgi_shilin_real_data()
    send_line_message(df, err)
