import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_real_data():
    # 凱基士林代碼：9238
    # 直接抓取證交所的「各券商每日進出」CSV 下載連結
    # 這個連結比 JSON API 更不容易擋 GitHub IP
    url = "https://www.twse.com.tw/exchangeReport/TWT43U?response=csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        
        # 檢查是否真的抓到 CSV 內容
        if "證券代號" not in res.text:
            return None, "證交所尚未更新今日資料或連線被阻擋。"

        # CSV 處理：略過前兩行標題，並用 pandas 讀取
        df = pd.read_csv(io.StringIO(res.text), skiprows=2)
        
        # 證交所 CSV 的欄位名稱可能包含空格，需清洗
        df.columns = [c.replace(' ', '').replace('"', '') for c in df.columns]
        
        # 篩選「買進分點」為 9238 的資料
        # 注意：CSV 內的代號可能是 '"9238"' 或 '9238'，所以用 str.contains 比較穩
        kgi_data = df[df['買進分點'].astype(str).str.contains('9238')].copy()
        
        if kgi_data.empty:
            return pd.DataFrame(), None
            
        # 整理欄位
        output = kgi_data[['證券代號', '證券名稱', '買進張數']].copy()
        return output, None

    except Exception as e:
        return None, f"CSV 下載異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 監控回報: {error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無買超標的 (或證交所尚未結算)。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        for _, row in buy_df.iterrows():
            code = str(row['證券代號']).replace('"', '').strip()
            name = str(row['證券名稱']).replace('"', '').strip()
            amount = str(row['買進張數']).replace('"', '').strip()
            content += f"✅ {code} {name}: +{amount}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    df, err = get_kgi_shilin_real_data()
    send_line_message(df, err)
