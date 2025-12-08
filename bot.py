def get_deal():
    required = ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_ASSOCIATE_TAG"]
    for key in required:
        if not os.getenv(key):
            print(f"❌ Missing env var: {key}")
            return None

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    params = {
        "Service": "AWSECommerceService",
        "Operation": "ItemSearch",
        "AWSAccessKeyId": os.getenv("AKPAOBWAZJ1765178442"),
        "AssociateTag": os.getenv("shopydilse-21"),
        "SearchIndex": "All",
        "Keywords": "mobile",  # सबसे reliable keyword
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
        print("🔍 Amazon API Status Code:", response.status_code)
        
        # === DEBUG: FULL RESPONSE (first 500 chars) ===
        raw_xml = response.content.decode('utf-8', errors='ignore')
        print("📄 First 500 chars of response:")
        print(raw_xml[:500])

        if response.status_code != 200:
            print("❌ HTTP error")
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

        items = root.findall(".//Item")
        print(f"📦 Total items found: {len(items)}")

        if not items:
            print("❌ No <Item> tags found in XML")
            return None

        item = items[0]
        # ... (rest of the code unchanged)
