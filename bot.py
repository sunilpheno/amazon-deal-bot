import os
import time
import hmac
import hashlib
import base64
from urllib.parse import quote
import requests
from flask import Flask
from xml.etree import ElementTree as ET

app = Flask(__name__)

def safe_str(value):
    """Convert any value to safe string for URL encoding"""
    if value is None:
        return ""
    return str(value)

def sign(params):
    # Convert all values to string and remove None
    clean_params = {safe_str(k): safe_str(v) for k, v in params.items() if k is not None and v is not None}
    # Sort and URL-encode
    sorted_params = "&".join([f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted(clean_params.items())])
    # Create string to sign
    string_to_sign = f"GET\nwebservices.amazon.in\n/onca/xml\n{sorted_params}"
    # Sign with secret key
    signature = hmac.new(
        os.getenv("tKezT6Z+ifzkGzE2scF19bfszVRb2CsVDll6K/nd").encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def get_deal():
    # Validate all required environment variables
    required_vars = ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_ASSOCIATE_TAG", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing environment variable: {var}")
            return None

    # Prepare timestamp in ISO 8601 UTC format
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    params = {
        "Service": "AWSECommerceService",
        "Operation": "ItemSearch",
        "AWSAccessKeyId": os.getenv("AKPAOBWAZJ1765178442"),
        "AssociateTag": os.getenv("shopydilse-21"),
        "SearchIndex": "All",
        "Keywords": "diabetes supplements",
        "ResponseGroup": "Images,ItemAttributes,Offers",
        "Timestamp": timestamp  # Now guaranteed to be a string
    }

    try:
        params["Signature"] = sign(params)
    except Exception as e:
        print("❌ Signature generation failed:", str(e))
        return None

    try:
        response = requests.get("https://webservices.amazon.in/onca/xml", params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
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
            print("❌ No items found in response")
            return None

        def safe_find(path):
            el = item.find(path)
            return el.text if el is not None else ""

        title = safe_find(".//ItemAttributes/Title") or "Unknown Product"
        image = safe_find(".//LargeImage/URL") or safe_find(".//MediumImage/URL")
        if not image:
            print("❌ No product image found")
            return None

        price = "₹0"
        price_el = item.find(".//OfferSummary/LowestNewPrice/Amount")
        if price_el is not None:
            try:
                price = "₹" + str(int(price_el.text) / 100)
            except:
                price = "₹0"

        link = safe_find(".//DetailPageURL")
        if link:
            link += f"?tag={os.getenv('AMAZON_ASSOCIATE_TAG')}"

        return {"title": title, "image": image, "price": price, "link": link}

    except Exception as e:
        print("🚨 Exception in get_deal:", str(e))
        return None

def send_to_telegram(deal):
    try:
        caption = (
            f"🔥 <b>{deal['title']}</b>\n\n"
            f"💰 Price: {deal['price']}\n"
            f"👉 <a href='{deal['link']}'>🛒 Buy on Amazon</a>\n\n"
            f"#AmazonDeals #Diabetes #SugarControl #HealthSupplements #Affiliate #India"
        )
        url = f"https://api.telegram.org/bot{os.getenv('8509017131:AAG5qyXhA0tlUIAodDmjh5ohe1GJ9s9UPvo')}/sendPhoto"
        data = {
            "chat_id": os.getenv("@amazondealindia4u"),
            "photo": deal["image"],
            "caption": caption,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, data=data, timeout=10)
        print("📩 Telegram response:", resp.status_code)
    except Exception as e:
        print("🚨 Telegram send error:", str(e))

@app.route("/run")
def run_bot():
    deal = get_deal()
    if deal:
        send_to_telegram(deal)
        return "✅ Deal posted to Telegram!"
    else:
        return "⚠️ No deal found or error occurred. Check logs."

@app.route("/")
def home():
    return "Amazon Deal Bot is running! Visit /run to trigger."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
