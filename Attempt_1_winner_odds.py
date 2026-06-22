import re
import ast
from flask import Flask, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

URL = "https://www.oddschecker.com/football/world-cup/winner"

cached_data = []


# ----------------------------
# SCRAPING CORE
# ----------------------------

def fetch_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)

        try:
            page.locator("button:has-text('Accept')").click(timeout=5000)
        except:
            pass

        page.wait_for_timeout(5000)

        html = page.content()
        browser.close()

        return html


def extract_chart_objects(html):
    pattern = r"oc\.charts\.push\((\{[\s\S]*?\})\)"
    return re.findall(pattern, html)


def js_object_to_python(js_str):
    js_str = re.sub(r",\s*([}\]])", r"\1", js_str)

    js_str = js_str.replace("null", "None")
    js_str = js_str.replace("true", "True")
    js_str = js_str.replace("false", "False")

    return ast.literal_eval(js_str)


def scrape(url):
    html = fetch_html(url)
    blocks = extract_chart_objects(html)

    if not blocks:
        print("No charts found — page structure mismatch")
        return []

    all_data = []

    for block in blocks:
        if '"container": "my_chart"' not in block:
            continue

        try:
            obj = js_object_to_python(block)
        except:
            continue

        if obj.get("type") == "pie":
            all_data.extend(obj.get("data", []))

    return all_data


# ----------------------------
# CACHE LAYER
# ----------------------------

def update_data():
    global cached_data

    data = scrape(URL)

    cached_data = [
        {"team": label, "probability": p}
        for label, p in data
    ]

    print(f"Updated cache: {len(cached_data)} teams")


# ----------------------------
# FLASK SERVER
# ----------------------------

@app.route("/")
def home():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>No index.html found</h1>"


@app.route("/odds.json")
def odds():
    if not cached_data:
        update_data()

    return jsonify(cached_data)


@app.route("/refresh")
def refresh():
    update_data()
    return {"status": "updated", "count": len(cached_data)}


# ----------------------------
# START SERVER
# ----------------------------

if __name__ == "__main__":
    app.run()