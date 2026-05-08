import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_data():
    # 凱基士林分點代號：9238
    url = "https://hi-stock.com/stock/branch.aspx?no=9238"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://hi-stock.com/'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        # 嗨投資通常使用 UTF-8，不需像群益處理 Big5 亂碼
        res.encoding = 'utf-8'
        
        if res.status_code != 200:
            return None, None, f"網頁連線失敗 (HTTP {res.status_code})"

        # 讀取 HTML 表格
        dfs = pd.read_html(io.StringIO(res.text))
        
        # 嗨投資的結構：買超表格通常在前面，賣超在後面
        # 我們根據表格標題關鍵字來鎖定
        buy_df = None
        sell_df = None
        
        for df in dfs:
            if '買超' in str(df.columns) or '買進' in str(df.columns):
                if buy_df is None: buy_df = df
            elif '賣超' in str(df.columns) or '賣出' in str(df.columns):
                if sell_df is None: sell_df = df

        if buy_df is None:
            return None, None, "無法在網頁中定位買賣超數據。"

        # 數據清洗函數
        def clean_data(temp_df):
            # 移除包含「合計」或重複標題的列
            temp_df = temp_df.dropna()
            temp_df = temp_df[~temp_df.astype(str).apply(lambda x: x.str.contains('合計|名稱|股票')).any(axis=1)]
            return temp_df

        return clean_data(buy_df), clean_data(sell_df), None

    except Exception as e:
        return None, None, f"執行異常: {str(e)}"

def send_line_message(buy_df, sell_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    
    if error_msg:
        content = f"⚠️ 凱基士林監控報錯:\n{error_msg}"
    else:
        content = "📊 【凱基士林】今日進出報告\n"
        content += "--------------------------\n"
        
        # 處理買超 (假設第 0 欄是股票，最後一欄是買超張數)
        content += "🔥 買超清單：\n"
        if buy_df is not None and not buy_df.empty:
            for _, row in buy_df.head(15).iterrows():
                content += f"✅ {row.iloc[0]}: +{row.iloc[-1]}張\n"
        else:
            content += "（無買超標的）\n"
            
        content += "\n📉 賣超清單：\n"
        if sell_df is not None and not sell_df.empty:
            for _, row in sell_df.head(15).iterrows():
                content += f"❌ {row.iloc[0]}: -{abs(int(float(row.iloc[-1])))}張\n"
        else:
            content += "（無賣超標的）\n"

    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": content}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    b, s, err = get_kgi_shilin_data()
    send_line_message(b, s, err)
