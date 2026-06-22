import re
import requests
import json
import ast 


from playwright.sync_api import sync_playwright

def fetch_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)

        try:
            page.locator("button:has-text('Accept')").click(timeout=5000)
        except:
            pass

        page.wait_for_timeout(8000)

        html = page.content()

        browser.close()

        return html


def extract_chart_objects(html):
    """
    More robust extraction:
    captures oc.charts.push({ ... }) including newlines.
    """
    pattern = r"oc\.charts\.push\((\{[\s\S]*?\})\)"
    return re.findall(pattern, html)


def js_object_to_python(js_str):
    js_str = re.sub(r",\s*([}\]])", r"\1", js_str)

    js_str = js_str.replace("null", "None")
    js_str = js_str.replace("true", "True")
    js_str = js_str.replace("false", "False")

    return ast.literal_eval(js_str)


def extract_pie_data(chart_obj):
    """
    Pull data only from pie charts
    """
    if chart_obj.get("type") != "pie":
        return []
    return chart_obj.get("data", [])


def normalise(data):
    total = sum(v for _, v in data)
    if total == 0:
        return data
    return [(label, v / total) for label, v in data]


def scrape(url):
    html = fetch_html(url)

    blocks = extract_chart_objects(html)

    print("Blocks found:", len(blocks))

    if blocks:
        print("\nSAMPLE BLOCK:\n")
        print(blocks[0][:400])

    if not blocks:
        print("No charts found — page structure mismatch")
        return []

    all_data = []

    for block in blocks:
        if '"container": "my_chart"' not in block:
            continue

        try:
            obj = js_object_to_python(block)
        except Exception:
            continue

        if obj.get("type") == "pie":
            all_data.extend(obj.get("data", []))

    return all_data


def print_table(data):
    print("\nRelative tournament win likelihood\n")
    print(f"{'Team':30} {'Probability':>12}")
    print("-" * 45)

    for label, p in sorted(data, key=lambda x: x[1], reverse=True):
        print(f"{label:30} {p:12.4f}")


if __name__ == "__main__":
    url = "https://www.oddschecker.com/football/world-cup/winner"

    data = scrape(url)

    print_table(data)

    structured = [
        {"team": label, "probability": p}
        for label, p in data
    ]

    with open("odds.json", "w") as f:
        json.dump(structured, f, indent=2)