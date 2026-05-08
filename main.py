import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_from_capital():
    # 你提供的群益證券網址
    url = "https://stock.capital.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9238"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        # 關鍵點：群益使用 Big5 編碼，必須強制指定，否則會亂碼
        res.encoding = 'big5'
        
        if res.status_code != 200:
            return None, f"網頁連線失敗 (HTTP {res.status_code})"

        # 使用 pandas 讀取 HTML 表格
        # 群益的買賣超資料通常在第 3 或第 4 個表格
        dfs = pd.read_html(io.StringIO(res.text))
        
        # 尋找包含「股票名稱」字眼的那個表格
        target_df = None
        for df in dfs:
            if df.shape[1] >= 3 and '股票名稱' in str(df.values):
                target_df = df
                break
        
        if target_df is None:
            return None, "在網頁中找不到符合格式的買賣超表格。"

        # 整理表格欄位
        # 根據該網頁結構：0:股票名稱, 1:買張, 2:賣張, 3:買賣超
        # 我們將第一行設為標題
        target_df.columns = target_df.iloc[0]
        target_df = target_df.drop(target_df.index[0])
        
        # 轉換數值並過濾買超 > 0
        target_df['買賣超'] = pd.to_numeric(target_df['買賣超'], errors='coerce')
        all_buys = target_df[target_df['買賣超'] > 0].copy()
        
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
        content = f"⚠️ 抓取報錯 (群益源):\n{error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】暫無買超標的 (或資料尚未更新)。"
    else:
        content = "📋 【凱基士林】今日買超全清單\n"
        content += "--------------------------\n"
        for _, row in buy_df.iterrows():
            name = str(row['股票名稱']).strip()
            # 排除非股票名稱的列
            if "合計" in name or "股票名稱" in name: continue
            amount = int(row['買賣超'])
            content += f"✅ {name}: +{amount}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    df, err = get_kgi_shilin_from_capital()
    send_line_message(df, err)
