import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_data():
    # 使用你指定的群益連結，d=1 代表當日
    url = "https://stock.capital.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9238&c=E&d=1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://stock.capital.com.tw/'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = 'big5' # 群益必須使用 big5
        
        if res.status_code != 200:
            return None, None, f"網頁連線失敗 (HTTP {res.status_code})"

        # 使用 pandas 讀取所有表格
        dfs = pd.read_html(io.StringIO(res.text))
        
        target_df = None
        for df in dfs:
            # 尋找包含關鍵字「買賣超」的表格
            if df.astype(str).apply(lambda x: x.str.contains('買賣超')).any().any():
                target_df = df
                break
        
        if target_df is None:
            return None, None, "在網頁中找不到資料表格 (可能是今日尚未更新)"

        # 整理表格：群益表格第一列通常是標題
        target_df.columns = target_df.iloc[0]
        target_df = target_df.drop(target_df.index[0]).reset_index(drop=True)
        
        # 清洗欄位名稱
        target_df.columns = [str(c).strip() for c in target_df.columns]
        
        # 將「買賣超」欄位轉為數值
        target_df['買賣超'] = pd.to_numeric(target_df['買賣超'], errors='coerce')
        
        # 排除掉無效列（如合計、或是重複的標題）
        clean_df = target_df.dropna(subset=['股票名稱'])
        clean_df = clean_df[~clean_df['股票名稱'].str.contains("合計|股票名稱|期貨")]

        # 分離買超與賣超
        buy_df = clean_df[clean_df['買賣超'] > 0].copy()
        sell_df = clean_df[clean_df['買賣超'] < 0].copy()
        
        # 賣超轉為正數方便閱讀
        sell_df['買賣超'] = sell_df['買賣超'].abs()
        
        return buy_df, sell_df, None

    except Exception as e:
        return None, None, f"系統異常: {str(e)}"

def send_line_message(buy_df, sell_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 監控報錯: {error_msg}"
    else:
        content = "📊 【凱基士林】今日進出報告\n"
        content += "--------------------------\n"
        
        # 處理買超
        content += "🔥 買超清單：\n"
        if buy_df is not None and not buy_df.empty:
            for _, row in buy_df.head(20).iterrows():
                content += f"✅ {row['股票名稱']}: +{int(row['買賣超'])}張\n"
        else:
            content += "（無買超標的）\n"
            
        content += "\n📉 賣超清單：\n"
        # 處理賣超
        if sell_df is not None and not sell_df.empty:
            for _, row in sell_df.head(20).iterrows():
                content += f"❌ {row['股票名稱']}: -{int(row['買賣超'])}張\n"
        else:
            content += "（無賣超標的）\n"

    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    b_df, s_df, err = get_kgi_shilin_data()
    send_line_message(b_df, s_df, err)
