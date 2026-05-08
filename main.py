import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_data():
    # 兆豐證券提供的相同格式資料源 (凱基 9200, 士林 9238)
    url = "https://jsjustweb.jihsun.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9238&c=E&d=1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://jsjustweb.jihsun.com.tw/'
    }
    
    try:
        # 使用 Session 維持連線模擬
        session = requests.Session()
        res = session.get(url, headers=headers, timeout=20)
        res.encoding = 'big5'
        
        if res.status_code != 200 or "股票名稱" not in res.text:
            return None, None, "資料源連線成功但無有效內容 (可能是今日尚未更新)"

        # 讀取所有表格
        dfs = pd.read_html(io.StringIO(res.text))
        
        target_df = None
        for df in dfs:
            # 尋找含有「買賣超」字眼的表格
            if df.astype(str).apply(lambda x: x.str.contains('買賣超')).any().any():
                target_df = df
                break
        
        if target_df is None:
            return None, None, "無法定位數據表格"

        # 整理表格：群益/兆豐系統的標題通常在第一列
        target_df.columns = target_df.iloc[0]
        target_df = target_df.drop(target_df.index[0]).reset_index(drop=True)
        
        # 清洗欄位並轉為數值
        target_df.columns = [str(c).strip() for c in target_df.columns]
        target_df['買賣超'] = pd.to_numeric(target_df['買賣超'], errors='coerce')
        
        # 過濾雜質
        clean_df = target_df.dropna(subset=['股票名稱'])
        clean_df = clean_df[~clean_df['股票名稱'].str.contains("合計|股票名稱|期貨")]

        # 分離買超與賣超
        buy_df = clean_df[clean_df['買賣超'] > 0].copy()
        sell_df = clean_df[clean_df['買賣超'] < 0].copy()
        sell_df['買賣超'] = sell_df['買賣超'].abs() # 賣超轉正數顯示
        
        return buy_df, sell_df, None

    except Exception as e:
        return None, None, f"抓取異常: {str(e)}"

def send_line_message(buy_df, sell_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 凱基士林監控報錯: {error_msg}"
    else:
        content = "📊 【凱基士林】今日進出彙整\n"
        content += "--------------------------\n"
        
        content += "🔥 買超前15：\n"
        if buy_df is not None and not buy_df.empty:
            for _, row in buy_df.head(15).iterrows():
                content += f"✅ {row['股票名稱']}: +{int(row['買賣超'])}張\n"
        else:
            content += "（無買超資料）\n"
            
        content += "\n📉 賣超前15：\n"
        if sell_df is not None and not sell_df.empty:
            for _, row in sell_df.head(15).iterrows():
                content += f"❌ {row['股票名稱']}: -{int(row['買賣超'])}張\n"
        else:
            content += "（無賣超資料）\n"

    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    b_df, s_df, err = get_kgi_shilin_data()
    send_line_message(b_df, s_df, err)
