import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_from_capital():
    # 這是該網頁實際內容的來源網址 (繞過外層框架)
    url = "https://stock.capital.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9238"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://stock.capital.com.tw/'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = 'big5'
        
        if res.status_code != 200:
            return None, f"連線失敗 (HTTP {res.status_code})"

        # 核心修正：使用 BeautifulSoup 先過濾掉雜質，再交給 pandas
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尋找網頁中所有的表格
        tables = soup.find_all('table')
        
        # 尋找含有「股票名稱」文字的表格字串
        target_html = ""
        for t in tables:
            if "股票名稱" in t.text:
                target_html = str(t)
                break
        
        if not target_html:
            return None, "網頁內容已讀取，但未偵測到買賣超數據表格。"

        # 讀取目標表格
        df = pd.read_html(io.StringIO(target_html))[0]
        
        # 清洗：群益表格通常第一列是標題，我們重新設定
        df.columns = df.iloc[0]
        df = df.drop(df.index[0]).reset_index(drop=True)
        
        # 強制將買賣超欄位轉為數字
        df['買賣超'] = pd.to_numeric(df['買賣超'], errors='coerce')
        
        # 篩選買超 > 0 且排除非股票名稱的列
        all_buys = df[df['買賣超'] > 0].dropna(subset=['股票名稱'])
        all_buys = all_buys[~all_buys['股票名稱'].str.contains("股票名稱|合計|期貨")]
        
        return all_buys, None

    except Exception as e:
        return None, f"程式執行異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 監控回報:\n{error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無買超標的 (或資料尚未產出)。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        # 避免訊息過長，取前 50 筆
        for _, row in buy_df.head(50).iterrows():
            name = str(row['股票名稱']).strip()
            val = int(row['買賣超'])
            content += f"✅ {name}: +{val}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    df, err = get_kgi_shilin_from_capital()
    send_line_message(df, err)
