import os
import time
import hmac
import hashlib
import base64
from urllib.parse import quote
import requests
from flask import Flask
from xml.etree import ElementTree as ET
import random

app = Flask(__name__)

# ===== SAFE HELPER =====
def safe_str(value):
    if value is None:
        return ""
    return str(value)

# ===== SIGNATURE GENERATOR =====
def sign(params, secret_key):
    clean_params = {
        safe_str(k): safe_str(v)
        for k, v in params.items()
        if k is not None and v is not None
    }
    sorted_params = "&".join([
        f"{quote(safe_str(k), safe='')}"
        f"={quote(safe_str(v), safe='')}"
        for k, v in sorted(clean_params.items())
    ])
    string_to_sign = f"GET\nwebservices.amazon.in\n/onca/xml\n{sorted_params}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

# ===== DEAL CATEGORIES =====
CATEGORIES = [
    {"name": "Mobile", "search_index": "Electronics", "keywords": "mobile"},
    {"name": "Electronics", "search_index": "Electronics", "keywords": "headphones"},
    {"name": "Women's Clothing", "search_index": "Fashion", "keywords": "women kurti"},
    {"name": "Men's Clothing", "search_index": "Fashion", "keywords": "men tshirt"},
    {"name": "Personal Care", "search_index": "HealthPersonalCare", "keywords": "trimmer"},
]

# ===== FETCH DEAL FROM AMAZON =====
def get_deal():
    # Validate environment variables
    required = ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_ASSOCIATE_TAG", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    for key in required:
        if not os.getenv(key):
            print(f"❌ Missing env var: {key}")
            return None

    # Pick random category
    category = random.choice(CATEGORIES)
    print(f"🔍 Searching in: {category['name']}")

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    params = {
        "Service": "AWSECommerceService",
        "Operation": "ItemSearch",
        "AWSAccessKeyId": os.getenv("AKPAOBWAZJ1765178442"),
        "AssociateTag": os.getenv("shopydilse-21"),
        "SearchIndex": category["search_index"],
        "Keywords": category["keywords"],
        "ResponseGroup": "Images,ItemAttributes,Offers",
        "Timestamp": timestamp
    }

    try:
        secret_key = os.getenv("tKezT6Z+ifzkGzE2scF19bfszVRb2CsVDll6K/nd")
        params["Signature"] = sign(params, secret_key)
    except Exception as e:
        print("❌ Signature error:", e)
        return None

    try:
        response = requests.get("https://webservices.amazon.in/onca/xml", params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return None

        root = ET.fromstring(response.content)
        error = root.find(".//Error")
        if error is not None:
            code = error.find("Code")
            msg = error.find("Message")
            code_text = code.text if code is not None else "Unknown"
            msg_text = msg.text if msg is not None else ""
            print(f"❌ Amazon API Error: {code_text} – {msg_text}")
            return None

        item = root.find(".//Item")
        if item is None:
            print("❌ No items found")
            return None

        def safe_find(path):
            el = item.find(path)
            return el.text if el is not None else ""

        title = safe_find(".//ItemAttributes/Title") or "Product"
        image = safe_find(".//LargeImage/URL") or safe_find(".//MediumImage/URL")
        if not image:
            print("❌ No image")
            return None

        price = "₹0"
        price_el = item.find(".//OfferSummary/LowestNewPrice/Amount")
        if price_el is not None:
            try:
                price = "₹" + str(int(price_el.text) / 100)
            except:
                pass

        link = safe_find(".//DetailPageURL")
        if link:
            link += f"?tag={os.getenv('AMAZON_ASSOCIATE_TAG')}"

        return {
            "title": title,
            "image": image,
            "price": price,
            "link": link,
            "category": category["name"]
        }

    except Exception as e:
        print("🚨 Exception in get_deal:", str(e))
        return None

# ===== SEND TO TELEGRAM =====
def send_to_telegram(deal):
    try:
        tags_map = {
            "Mobile": "#Mobile #Smartphone #Gadgets",
            "Electronics": "#Electronics #Headphones #Tech",
            "Women's Clothing": "#WomensFashion #Kurti #Clothing",
            "Men's Clothing": "#MensFashion #Tshirt #Clothing",
            "Personal Care": "#PersonalCare #Trimmer #Grooming"
        }
        tags = tags_map.get(deal["category"], "#AmazonDeals")

        caption = (
            f"🔥 <b>{deal['title']}</b>\n\n"
            f"🏷️ Category: {deal['category']}\n"
            f"💰 Price: {deal['price']}\n"
            f"👉 <a href='{deal['link']}'>🛒 Buy on Amazon</a>\n\n"
            f"{tags} #AmazonDeals #Affiliate #India"
        )
        url = f"https://api.telegram.org/bot{os.getenv('8509017131:AAG5qyXhA0tlUIAodDmjh5ohe1GJ9s9UPvo')}/sendPhoto"
        data = {
            "chat_id": os.getenv("@amazondealindia4u"),
            "photo": deal["image"],
            "caption": caption,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, data=data, timeout=10)
        print("✅ Telegram sent | Category:", deal["category"])
    except Exception as e:
        print("🚨 Telegram error:", str(e))

# ===== FLASK ENDPOINTS =====
@app.route("/run")
def run_bot():
    deal = get_deal()
    if deal:
        send_to_telegram(deal)
        return f"✅ Deal posted! Category: {deal['category']}"
    else:
        return "⚠️ No deal found. Check logs."

@app.route("/")
def home():
    return "Amazon Multi-Category Deal Bot is live! Visit /run to trigger."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
