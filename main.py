import os
import requests
import pandas as pd

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林券商代號: 9238
    # 我們改用證交所/官方公開資料的高速介面 (模擬資料流)
    # 這裡選擇一個較少阻擋的數據接口
    url = "https://fubon-ebroker.com.tw/z/zg/zgb/zgb0.aspx?a=9230&b=9238&c=E&d=1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = 'big5' # 台灣財經站點多為 big5 編碼
        
        # 這裡改用比較彈性的解析方式
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尋找所有表格
        tables = soup.find_all('table')
        if len(tables) < 4:
            return None, "券商暫無進出資料 (可能今日未交易或尚未更新)"

        # 鎖定進出明細表格 (通常是 id 為 'oMainTable' 或第 4 個 table)
        target_table = tables[3] 
        df = pd.read_html(str(target_table))[0]
        
        # 清洗資料：過濾買超
        # 欄位 0: 股票名稱, 欄位 1: 買進, 欄位 2: 賣出
        df.columns = ['股票', '買進', '賣出', '買賣超', '佔比']
        df['買超張數'] = pd.to_numeric(df['買進'], errors='coerce') - pd.to_numeric(df['賣出'], errors='coerce')
        
        all_buys = df[df['買超張數'] > 0].copy()
        return all_buys, None

    except Exception as e:
        return None, f"數據處理異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 凱基士林監控回報\n{error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無進出標的。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        for _, row in buy_df.iterrows():
            name = str(row['股票']).strip()
            # 排除非股票名稱的列
            if "股票" in name or "合計" in name: continue
            amount = int(row['買超張數'])
            content += f"✅ {name}: +{amount}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    df, err = get_kgi_shilin_real_data()
    send_line_message(df, err)
