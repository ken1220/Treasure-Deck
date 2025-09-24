import requests
import json
import re
import os
import math
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --------------------------
# 全体設定
# --------------------------
PRICE_URL = "https://cardrush.media/onepiece/buying_prices?displayMode=リスト&limit=2000&name=&rarity=&model_number=&amount=&page=1&sort%5Bkey%5D=amount&sort%5Border%5D=desc&associations%5B%5D=ocha_product&to_json_option%5Bexcept%5D%5B%5D=original_image_source&to_json_option%5Bexcept%5D%5B%5D=created_at&to_json_option%5Binclude%5D%5Bocha_product%5D%5Bonly%5D%5B%5D=id&to_json_option%5Binclude%5D%5Bocha_product%5D%5Bmethods%5D%5B%5D=image_source&display_category%5B%5D=最新弾&display_category%5B%5D=通常弾"

# ディレクトリのパスをGitHub Actions実行環境に合わせて修正
DATA_DIR = "./Card_Data/Onepeace_Cards/"
HISTORY_FILE = os.path.join(DATA_DIR, "C.json")
LATEST_PRICE_FILE = os.path.join(DATA_DIR, "latestprice.json")
OFFICIAL_CARD_DATA_FILE = os.path.join(DATA_DIR, "cards.json")

OFFICIAL_SITE_URL = "https://www.onepiece-cardgame.com/"

TODAY = datetime.now().strftime("%Y-%m-%d")

# 公式カードデータ用のマッピング
COLOR_MAP = {
    "赤": "Red", "緑": "Green", "青": "Blue",
    "黄": "Yellow", "紫": "Purple", "黒": "Black"
}
SERIES_MAP = {
    "550101": "OP-01", "550102": "OP-02", "550103": "OP-03", "550104": "OP-04",
    "550105": "OP-05", "550106": "OP-06", "550107": "OP-07", "550108": "OP-08",
    "550109": "OP-09", "550110": "OP-10", "550111": "OP-11", "550112": "OP-12",
    "550113": "OP-13", "550001": "ST-01", "550002": "ST-02", "550003": "ST-03",
    "550004": "ST-04", "550005": "ST-05", "550006": "ST-06", "550007": "ST-07",
    "550008": "ST-08", "550009": "ST-09", "550010": "ST-10", "550011": "ST-11",
    "550012": "ST-12", "550013": "ST-13", "550014": "ST-14", "550015": "ST-15",
    "550016": "ST-16", "550017": "ST-17", "550018": "ST-18", "550019": "ST-19",
    "550020": "ST-20", "550021": "ST-21", "550022": "ST-22", "550023": "ST-23",
    "550024": "ST-24", "550701": "FAMILY", "550901": "PR", "550801": "LIMITED",
    "550302": "PRB-02", "550301": "PRB-01", "550202": "EB-02", "550201": "EB-01"
}

# --------------------------
# 価格スクレイピング関数
# --------------------------
def scrape_cardrush_prices():
    """カードラッシュから買取価格をスクレイピングする。"""
    try:
        res = requests.get(PRICE_URL)
        res.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text, re.S)
        data = json.loads(match.group(1))
        cards = data["props"]["pageProps"]["buyingPrices"]
        
        scraped_data = []
        for c in cards:
            rarity = c.get("rarity", "")
            color = c.get("element", "")
            code = c.get("model_number", "")
            
            extras = []
            if "未開封" in c.get("extra_difference", ""): extras.append("未開封")
            if "CS" in c.get("extra_difference", ""): extras.append("チャンピオンシップ")
            if "illust" in c.get("extra_difference", ""): extras.append("プロモ")
            if "パラレル" in c.get("extra_difference", ""): extras.append("パラレル")
            
            price_id = f"{c['name']} 【{rarity}】"
            for e in extras: price_id += f"【{e}】"
            if color: price_id += f"【{color}】"
            if code: price_id += f"【{code}】"
            
            scraped_data.append({"priceid": price_id, "price": c["amount"]})
        
        return scraped_data
    except (requests.RequestException, json.JSONDecodeError, IndexError) as e:
        print(f"❌ 価格のスクレイピングに失敗しました: {e}")
        return None

def update_price_history(scraped_data):
    """日次の価格履歴ファイル (C.json) を更新する。"""
    if not scraped_data:
        return

    history_data = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history_data = json.load(f)

    merged_history = {}
    for item in history_data:
        pid = item["priceid"]
        prices = item["price"]
        if isinstance(prices, int):
            merged_history[pid] = [{"date": TODAY, "value": prices}]
        elif isinstance(prices, list) and all(isinstance(p, dict) and "date" in p and "value" in p for p in prices):
            merged_history[pid] = prices
        else:
            merged_history[pid] = []

    for item in scraped_data:
        pid = item["priceid"]
        price = item["price"]
        
        if pid not in merged_history:
            merged_history[pid] = [{"date": TODAY, "value": price}]
        else:
            existing_today = next((p for p in merged_history[pid] if p["date"] == TODAY), None)
            if existing_today:
                existing_today["value"] = price
            else:
                merged_history[pid].append({"date": TODAY, "value": price})

    result = [{"priceid": pid, "price": prices} for pid, prices in merged_history.items()]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 日次履歴を更新しました: {HISTORY_FILE}")

def generate_latest_price_file(merged_data):
    """最新価格ファイル (latestprice.json) を生成する。"""
    if not merged_data:
        print("最新価格を生成するデータがありません。")
        return

    latest_result = []
    for item in merged_data:
        pid = item["priceid"]
        prices = item["price"]
        if not prices:
            continue
        
        sorted_prices = sorted(prices, key=lambda x: x["date"])
        oldest = sorted_prices[0]["value"]
        newest = sorted_prices[-1]["value"]
        diff = newest - oldest
        stats_str = f"{diff:+d}"
        
        latest_result.append({
            "priceid": pid,
            "price": newest,
            "stats": stats_str
        })
    
    with open(LATEST_PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(latest_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 最新価格を出力しました: {LATEST_PRICE_FILE}")

# --------------------------
# 公式カードデータスクレイピング関数
# --------------------------
def normalize_image_url(url: str) -> str:
    """画像のURLを正規化する (_r1 を除去)。"""
    return url.replace("_r1", "")

def get_card_key(card):
    """重複を防ぐためのカードキーを生成する。"""
    return f"{card['code']}_{normalize_image_url(card['image_url'])}_{card['parallel']}"

def scrape_official_card_data():
    """ワンピースカードゲーム公式サイトからカードデータをスクレイピングする。"""
    merged_cards = {}
    total_series = len(SERIES_MAP)
    processed_series = 0
    
    for series_number, official_code in SERIES_MAP.items():
        try:
            url = f"{OFFICIAL_SITE_URL}cardlist/?series={series_number}"
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for dt in soup.find_all("dt"):
                card_data = {}
                spans = dt.find_all("span")
                if len(spans) >= 3:
                    card_data["code"] = spans[0].text.strip()
                    card_data["rarity"] = spans[1].text.strip()
                    card_data["role"] = spans[2].text.strip()
                
                card_name_div = dt.parent.find("div", class_="cardName")
                card_data["name"] = card_name_div.text.strip() if card_name_div else ""
                
                dd = dt.find_next_sibling("dd")
                if not dd: continue

                # 詳細情報の抽出
                cost_text = dd.find("div", class_="cost").text.strip() if dd.find("div", class_="cost") else ""
                card_data["life"] = "4" if card_data["role"] == "LEADER" else "-"
                card_data["cost"] = "-" if card_data["role"] == "LEADER" else cost_text.replace("コスト", "").strip()
                card_data["attribute"] = dd.select_one("div.attribute img")["alt"] if dd.select_one("div.attribute img") else "-"
                card_data["power"] = dd.find("div", class_="power").text.strip() if dd.find("div", class_="power") else ""
                card_data["counter"] = dd.find("div", class_="counter").text.replace("カウンター", "").strip() if dd.find("div", class_="counter") else ""
                card_data["block"] = "".join(filter(str.isdigit, dd.find("div", class_="block").text)) if dd.find("div", class_="block") else ""
                
                color_div = dd.find("div", class_="color")
                colors = color_div.text.replace("色", "").strip().split("/") if color_div else []
                card_data["color"] = [COLOR_MAP.get(c.strip(), c.strip()) for c in colors if c.strip()]
                
                feature_div = dd.find("div", class_="feature")
                features = feature_div.text.replace("特徴", "").strip().replace("・", "/").split("/") if feature_div else []
                card_data["feature"] = [f.strip() for f in features if f.strip()]
                
                img_tag = dd.select_one("div.frontCol img.lazy")
                if img_tag and "data-src" in img_tag.attrs:
                    image_url = urljoin(OFFICIAL_SITE_URL, img_tag["data-src"].replace("../", ""))
                    card_data["image_url"] = image_url.split("?")[0]
                    card_data["parallel"] = "parallel" if "_p" in image_url.lower() else "normal"
                else:
                    card_data["image_url"] = ""
                    card_data["parallel"] = "normal"
                
                key = get_card_key(card_data)
                if key in merged_cards:
                    merged_cards[key]["series"].add(official_code)
                else:
                    card_data["series"] = {official_code}
                    merged_cards[key] = card_data
            
            processed_series += 1
            progress = math.floor(processed_series / total_series * 100)
            print(f"[進捗] {processed_series}/{total_series} ({progress}%) 完了")
        
        except requests.RequestException as e:
            print(f"❌ 公式サイトのスクレイピングに失敗しました (シリーズ {official_code}): {e}")
            continue
            
    output = []
    for card in merged_cards.values():
        card["series"] = sorted(list(card["series"]))
        output.append(card)
        
    with open(OFFICIAL_CARD_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 公式カード情報を保存しました: {OFFICIAL_CARD_DATA_FILE}")
    
    # 最後に id0 を更新する
    update_card_ids(OFFICIAL_CARD_DATA_FILE)

def update_card_ids(file_path):
    """
    指定されたJSONファイルに連番の `id0` を追加または更新する。
    """
    if not os.path.exists(file_path):
        print(f"❌ ファイル '{file_path}' が見つかりませんでした。id0の更新をスキップします。")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        existing_ids = [card.get("id0", 0) for card in data]
        max_id = max(existing_ids) if existing_ids else 0

        for card in data:
            if "id0" not in card:
                max_id += 1
                card["id0"] = max_id

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(data)} 件のカードに id0 を更新しました")
    
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ id0 の更新中にエラーが発生しました: {e}")

# --------------------------
# メインの実行
# --------------------------
def main():
    """両方のスクレイピングタスクを実行するメイン関数。"""
    print("--- 💸 価格情報の更新を開始します ---")
    scraped_prices = scrape_cardrush_prices()
    if scraped_prices:
        update_price_history(scraped_prices)
        
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                updated_history = json.load(f)
            generate_latest_price_file(updated_history)
        
    print("\n--- 📖 公式カード情報の更新を開始します ---")
    scrape_official_card_data()
    
if __name__ == "__main__":
    main()
