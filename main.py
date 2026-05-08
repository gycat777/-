import os
import requests
import pandas as pd

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_all_buys():
    # 這裡目前是模擬數據，後續你可以接入實際爬蟲
    # 凱基士林代號為 9238
    data = {
        '股票': ['台積電', '鴻海', '長榮', '陽明', '中信金', '群創', '聯發科', '欣興', '長榮航'],
        '張數': [500, 320, 150, -450, -210, -600, 100, 50, 80]
    }
    df = pd.DataFrame(data)
    
    # 篩選出所有「買超」的股票 (張數 > 0)
    all_buys = df[df['張數'] > 0].sort_values(by='張數', ascending=False)
    
    return all_buys

def send_line_message(buy_df):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    # 組合訊息
    msg = "📋 【凱基士林】今日買超清單 (全部)\n"
    msg += "--------------------------\n"
    
    if buy_df.empty:
        msg += "今日無買超標的。"
    else:
        for _, row in buy_df.iterrows():
            msg += f"✅ {row['股票']}: +{row['張數']}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"傳送狀態: {response.status_code}")

if __name__ == "__main__":
    all_buy_data = get_kgi_shilin_all_buys()
    send_line_message(all_buy_data)
