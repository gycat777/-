import os
import requests
import pandas as pd
from datetime import datetime

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_official():
    # 凱基士林分點代碼：9238
    # 直接存取證交所當日分點進出統計 (這是官方 JSON 接口)
    url = "https://www.twse.com.tw/exchangeReport/TWT43U?response=json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        data = res.json()
        
        if data.get('stat') != 'OK':
            return None, None, f"證交所目前未提供資料 (stat: {data.get('stat')})"

        # 證交所資料結構說明：
        # data['data'] 是個清單，其中：
        # [0]證券代號, [1]證券名稱, [2]成交分點代號, [3]成交分點名稱, [4]買進張數, [5]賣出張數
        all_data = pd.DataFrame(data['data'])
        
        # 過濾成交分點代號為 '9238' 的資料 (凱基士林)
        # 注意：代號在 JSON 中可能是字串，也可能有空格
        kgi_data = all_data[all_data[2].astype(str).str.strip() == '9238'].copy()
        
        if kgi_data.empty:
            return pd.DataFrame(), pd.DataFrame(), None

        # 計算買賣超
        # 欄位 4 是買進，欄位 5 是賣出
        kgi_data['買進'] = pd.to_numeric(kgi_data[4], errors='coerce')
        kgi_data['賣出'] = pd.to_numeric(kgi_data[5], errors='coerce')
        kgi_data['買賣超'] = kgi_data['買進'] - kgi_data['賣出']
        
        # 整理輸出格式
        kgi_data['標的'] = kgi_data[0] + " " + kgi_data[1]
        
        buy_df = kgi_data[kgi_data['買賣超'] > 0].sort_values(by='買賣超', ascending=False)
        sell_df = kgi_data[kgi_data['買賣超'] < 0].sort_values(by='買賣超', ascending=True)
        sell_df['買賣超'] = sell_df['買賣超'].abs()
        
        return buy_df, sell_df, None

    except Exception as e:
        return None, None, f"證交所 API 連線異常: {str(e)}"

def send_line_message(buy_df, sell_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    
    if error_msg:
        content = f"⚠️ 凱基士林監控報錯: {error_msg}"
    elif buy_df is None or (buy_df.empty and sell_df.empty):
        content = "📋 今日【凱基士林】無成交紀錄 (或證交所尚未結算)。"
    else:
        content = "📊 【凱基士林】今日官方進出清單\n"
        content += "--------------------------\n"
        
        if not buy_df.empty:
            content += "🔥 買超前 15：\n"
            for _, row in buy_df.head(15).iterrows():
                content += f"✅ {row['標的']}: +{int(row['買賣超'])}張\n"
        
        if not sell_df.empty:
            content += "\n📉 賣超前 15：\n"
            for _, row in sell_df.head(15).iterrows():
                content += f"❌ {row['標的']}: -{int(row['買賣超'])}張\n"

    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": content}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    b, s, err = get_kgi_shilin_official()
    send_line_message(b, s, err)
