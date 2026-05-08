import os
import requests
import pandas as pd
import io
import subprocess

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_data():
    # 您指定的群益連結
    url = "https://stock.capital.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9238&c=E&d=1"
    
    # 使用底層 curl 指令來模擬瀏覽器，這比 requests 更難被偵測
    curl_cmd = [
        'curl', 
        '-L', url,
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        '-H', 'Referer: https://stock.capital.com.tw/',
        '-H', 'Accept-Language: zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        '--compressed'
    ]
    
    try:
        # 執行指令並取得結果
        result = subprocess.run(curl_cmd, capture_output=True, text=False, timeout=30)
        # 用 big5 解碼內容
        html_content = result.stdout.decode('big5', errors='ignore')
        
        if "股票名稱" not in html_content:
            return None, None, "數據源連線成功但內容被攔截 (空網頁)。"

        # 解析所有表格
        dfs = pd.read_html(io.StringIO(html_content))
        target_df = None
        for df in dfs:
            if df.astype(str).apply(lambda x: x.str.contains('買賣超')).any().any():
                target_df = df
                break
        
        if target_df is None:
            return None, None, "無法從網頁內容中提取表格數據。"

        # 整理與清洗
        target_df.columns = target_df.iloc[0]
        target_df = target_df.drop(target_df.index[0]).reset_index(drop=True)
        target_df.columns = [str(c).strip() for c in target_df.columns]
        target_df['買賣超'] = pd.to_numeric(target_df['買賣超'], errors='coerce')
        
        clean_df = target_df.dropna(subset=['股票名稱'])
        clean_df = clean_df[~clean_df['股票名稱'].str.contains("合計|股票名稱|期貨")]

        buy_df = clean_df[clean_df['買賣超'] > 0].copy()
        sell_df = clean_df[clean_df['買賣超'] < 0].copy()
        sell_df['買賣超'] = sell_df['買賣超'].abs()
        
        return buy_df, sell_df, None

    except Exception as e:
        return None, None, f"運行異常: {str(e)}"

def send_line_message(buy_df, sell_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    
    if error_msg:
        content = f"⚠️ 監控回報: {error_msg}"
    else:
        content = "📊 【凱基士林】今日進出彙整\n"
        content += "--------------------------\n🔥 買超：\n"
        if not buy_df.empty:
            for _, r in buy_df.head(15).iterrows():
                content += f"✅ {r['股票名稱']}: +{int(r['買賣超'])}張\n"
        else: content += "（今日無買超）\n"
        
        content += "\n📉 賣超：\n"
        if not sell_df.empty:
            for _, r in sell_df.head(15).iterrows():
                content += f"❌ {r['股票名稱']}: -{int(r['買賣超'])}張\n"
        else: content += "（今日無賣超）\n"

    requests.post(url, headers=headers, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": content}]})

if __name__ == "__main__":
    b, s, err = get_kgi_shilin_data()
    send_line_message(b, s, err)
