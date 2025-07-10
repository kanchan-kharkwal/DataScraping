from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "footer", "nav", "header", "noscript"]):
        tag.decompose()
    return soup

def is_ascii_table(text):
    """
    Detects whether a string is likely to be an ASCII table.
    Looks for +---+ or | key | type | or similar patterns.
    """
    return bool(re.search(r"\+\-+\+", text) or re.search(r"^\|\s?.+\s?\|", text, re.MULTILINE))


def extract_sections(soup):
    content = []
    current_section = None

    for tag in soup.find_all(["h1", "h2", "h3", "p", "pre", "ul", "ol"]):
        tag_text = tag.get_text(strip=True).encode('ascii', 'ignore').decode()

        if tag.name in ["h2", "h3"]:
            if current_section:
                content.append(filter_non_empty_fields(current_section))
            current_section = {
                "heading": tag_text,
                "description": "",
                "syntax": [],
                "examples": []
            }

        elif current_section:
            if tag.name == "pre":
                # Preserve ASCII tables as-is
                raw_text = tag.get_text()
                if is_ascii_table(raw_text):
                    current_section["syntax"].append(raw_text.strip())
                elif "example" in current_section["heading"].lower():
                    current_section["examples"].append(raw_text.strip())
                else:
                    current_section["syntax"].append(raw_text.strip())
            elif tag.name in ["ul", "ol"]:
                current_section["description"] += "\n" + " ".join(li.get_text(strip=True) for li in tag.find_all("li"))
            elif tag.name == "p":
                current_section["description"] += "\n" + tag_text

    if current_section:
        content.append(filter_non_empty_fields(current_section))

    return content


def filter_non_empty_fields(section):
    """Remove empty fields from a section dictionary"""
    return {k: v for k, v in section.items() if (v if isinstance(v, list) else v.strip())}


def scrape_snowflake_transactions():
    url = "https://docs.snowflake.com/en/sql-reference/transactions"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")

        html = page.content()
        soup = clean_html(html)
        sections = extract_sections(soup)

        result = {
            "title": "Transactions",
            "url": url,
            "sections": sections
        }

        with open("snowflake_transactions_structured.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        browser.close()


if __name__ == "__main__":
    scrape_snowflake_transactions()
