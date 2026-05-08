import os
import requests
import pandas as pd

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_data():
    # 這裡請替換成實際抓取凱基士林 (9217) 的爬蟲邏輯
    # 目前先用模擬數據示範排序邏輯
    data = {
        '股票': ['台積電', '鴻海', '長榮', '陽明', '中信金', '群創', '聯發科'],
        '張數': [500, 320, 150, -450, -210, -600, 100]
    }
    df = pd.DataFrame(data)
    buy_top3 = df.sort_values(by='張數', ascending=False).head(3)
    sell_top3 = df.sort_values(by='張數', ascending=True).head(3)
    return buy_top3, sell_top3

def send_line_message(buy_df, sell_df):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    # 組合訊息
    msg = "📊 凱基士林 今日進出\n\n🔥 買超前三:\n"
    for _, row in buy_df.iterrows():
        msg += f"- {row['股票']}: +{row['張數']}張\n"
    
    msg += "\n❄️ 賣超前三:\n"
    for _, row in sell_df.iterrows():
        msg += f"- {row['股票']}: {row['張數']}張\n"

    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"傳送狀態: {response.status_code}")

if __name__ == "__main__":
    buy_3, sell_3 = get_kgi_shilin_data()
    send_line_message(buy_3, sell_3)
