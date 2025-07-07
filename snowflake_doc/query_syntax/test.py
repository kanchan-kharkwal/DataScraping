import requests
from bs4 import BeautifulSoup
import json


def clean(text):
    return ' '.join(text.strip().split())


def scrape_snowflake_construct(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    page_title = soup.title.text.strip()

    # Main content area
    main_content = soup.find('main') or soup.find('article')
    if not main_content:
        return {"error": "Main content not found"}

    result = {
        "url": url,
        "title": clean(page_title),
        "description": "",
        "syntax": "",
        "parameters": [],
        "examples": [],
        "notes": [],
    }

    current_section = None
    pending_param = {}

    for el in main_content.find_all(['p', 'pre', 'div', 'code', 'li', 'dt', 'dd', 'strong']):
        text = clean(el.get_text(separator=' ', strip=True))

        lower_text = text.lower()
        if any(keyword in lower_text for keyword in ["syntax", "how to use"]) and len(text) < 40:
            current_section = "syntax"
            continue
        elif "parameter" in lower_text and len(text) < 40:
            current_section = "parameters"
            continue
        elif "example" in lower_text and len(text) < 40:
            current_section = "examples"
            continue
        elif "usage note" in lower_text and len(text) < 40:
            current_section = "notes"
            continue

        if current_section == "syntax" and el.name == "pre":
            result["syntax"] += el.get_text(separator="\n", strip=True) + "\n"

        elif current_section == "parameters":
            if el.name == "strong":
                pending_param["name"] = clean(el.get_text())
            elif el.name in ["p", "dd", "div"] and "name" in pending_param:
                pending_param["description"] = clean(el.get_text())
                result["parameters"].append(pending_param)
                pending_param = {}

        elif current_section == "examples" and el.name == "pre":
            result["examples"].append(el.get_text(separator="\n", strip=True))

        elif current_section == "usage notes" and el.name in ["p", "div"]:
            result["notes"].append(text)

        elif not result["description"] and el.name == "p":
            result["description"] = text

    return result


# Run the scraper
url = "https://docs.snowflake.com/en/sql-reference/constructs/asof-join"
data = scrape_snowflake_construct(url)

# Save to JSON file
output_path = "asof_join_construct.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Data saved to {output_path}")
