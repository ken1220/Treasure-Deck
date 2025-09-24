import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import os
import math

# 日本語→英語の色変換マップ
color_map = {
    "赤": "Red",
    "緑": "Green",
    "青": "Blue",
    "黄": "Yellow",
    "紫": "Purple",
    "黒": "Black"
}

# シリーズ番号と公式コードの対応
series_map = {
    "550101": "OP-01", "550102": "OP-02", "550103": "OP-03", "550104": "OP-04",
    "550105": "OP-05", "550106": "OP-06", "550107": "OP-07", "550108": "OP-08",
    "550109": "OP-09", "550110": "OP-10", "550111": "OP-11", "550112": "OP-12",
    "550113": "OP-13",
    "550001": "ST-01", "550002": "ST-02", "550003": "ST-03", "550004": "ST-04",
    "550005": "ST-05", "550006": "ST-06", "550007": "ST-07", "550008": "ST-08",
    "550009": "ST-09", "550010": "ST-10", "550011": "ST-11", "550012": "ST-12",
    "550013": "ST-13", "550014": "ST-14", "550015": "ST-15", "550016": "ST-16",
    "550017": "ST-17", "550018": "ST-18", "550019": "ST-19", "550020": "ST-20",
    "550021": "ST-21", "550022": "ST-22", "550023": "ST-23", "550024": "ST-24",
    "550701": "FAMILY", "550901": "PR", "550801": "LIMITED",
    "550302": "PRB-02", "550301": "PRB-01",
    "550202": "EB-02", "550201": "EB-01"
}

# ディレクトリパスを修正
data_dir = os.path.join("Card_Data", "Onepeace_Cards")
os.makedirs(data_dir, exist_ok=True)
output_path = os.path.join(data_dir, "cards.json")

# カードマージ用
merged_cards = {}

def normalize_image_url(url: str) -> str:
    """_r1 は通常版に統合する"""
    if "_r1" in url:
        return url.replace("_r1", "")
    return url

def get_key(card):
    """同一カード判定キー(画像を_r1正規化して比較)"""
    return f"{card['code']}_{normalize_image_url(card['image_url'])}_{card['parallel']}"

# 総シリーズ数
total_series = len(series_map)
processed_series = 0

for series_number, official_code in series_map.items():
    url = f"https://www.onepiece-cardgame.com/cardlist/?series={series_number}"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    base_url = "https://www.onepiece-cardgame.com/"

    for dt in soup.find_all("dt"):
        card_data = {}
        spans = dt.find_all("span")
        if len(spans) >= 3:
            card_data["code"] = spans[0].text.strip()
            rarity_text = spans[1].text.strip()
            card_data["rarity"] = "SP" if rarity_text == "SPカード" else rarity_text
            card_data["role"] = spans[2].text.strip()

        # カード名
        card_name_div = dt.parent.find("div", class_="cardName")
        card_data["name"] = card_name_div.text.strip() if card_name_div else ""

        dd = dt.find_next_sibling("dd")
        if not dd:
            continue

        # cost / life
        cost_div = dd.find("div", class_="cost")
        cost_text = cost_div.text.strip() if cost_div else ""
        if card_data["role"] == "LEADER":
            card_data["life"] = "4"
            card_data["cost"] = "-"
        else:
            if "コスト" in cost_text:
                card_data["life"] = "-"
                card_data["cost"] = cost_text.replace("コスト", "").strip()
            else:
                card_data["life"] = cost_text.replace("ライフ", "").strip()
                card_data["cost"] = "-"

        # 属性
        if card_data["role"] == "EVENT":
            card_data["attribute"] = "-"
        else:
            attr_img = dd.select_one("div.attribute img")
            card_data["attribute"] = attr_img["alt"] if attr_img else ""

        # パワー
        power_div = dd.find("div", class_="power")
        if power_div:
            h3 = power_div.find("h3")
            if h3:
                h3.extract()
            card_data["power"] = power_div.text.strip()
        else:
            card_data["power"] = ""

        # カウンター
        counter_div = dd.find("div", class_="counter")
        card_data["counter"] = counter_div.text.replace("カウンター", "").strip() if counter_div else ""

        # block
        block_div = dd.find("div", class_="block")
        if block_div:
            card_data["block"] = "".join(filter(str.isdigit, block_div.text))
        else:
            card_data["block"] = ""

        # color
        color_div = dd.find("div", class_="color")
        if color_div:
            colors = color_div.text.replace("色", "").strip().split("/")
            card_data["color"] = [color_map.get(c.strip(), c.strip()) for c in colors if c.strip()]
        else:
            card_data["color"] = []

        # feature
        feature_div = dd.find("div", class_="feature")
        if feature_div:
            features = feature_div.text.replace("特徴", "").strip().replace("・", "/").split("/")
            card_data["feature"] = [f.strip() for f in features if f.strip()]
        else:
            card_data["feature"] = []

        # 画像URL
        img_tag = dd.select_one("div.frontCol img.lazy")
        if img_tag and "data-src" in img_tag.attrs:
            image_url = urljoin(base_url, img_tag["data-src"].replace("../", ""))
            card_data["image_url"] = image_url.split("?")[0]
            if "_p" in image_url.lower():
                card_data["parallel"] = "parallel"
            else:
                card_data["parallel"] = "normal"
        else:
            card_data["image_url"] = ""
            card_data["parallel"] = "normal"

        # マージ処理
        key = get_key(card_data)
        if key in merged_cards:
            merged_cards[key]["series"].add(official_code)
        else:
            card_data["series"] = {official_code}
            merged_cards[key] = card_data

    processed_series += 1
    progress = math.floor(processed_series / total_series * 100)
    print(f"[進捗] {processed_series}/{total_series} ({progress}%) 完了")

# JSON保存
output = []
for card in merged_cards.values():
    card["series"] = sorted(list(card["series"]))
    output.append(card)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n=== 完了 ===\n合計 {len(output)} 枚を保存しました → {output_path}")
