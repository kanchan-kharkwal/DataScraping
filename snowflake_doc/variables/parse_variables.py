from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

BASE_URL = "https://docs.snowflake.com"
MAIN_PAGE = "/en/sql-reference/session-variables"
LINKED_TOPICS = ["set", "unset", "show-variables"]

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "footer", "nav", "header", "noscript"]):
        tag.decompose()
    return soup

def strip_unicode(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def is_ascii_table(text):
    return bool(re.search(r"\+\-+\+", text) or re.search(r"^\|\s?.+\s?\|", text, re.MULTILINE))

def extract_sections(soup):
    content = []
    current_section = None

    for tag in soup.find_all(["h1", "h2", "h3", "p", "pre", "ul", "ol"]):
        tag_text = tag.get_text(strip=True)

        if tag.name in ["h2", "h3"]:
            if current_section:
                content.append(filter_non_empty_fields(current_section))
            current_section = {
                "heading": strip_unicode(tag_text),
                "description": "",
                "syntax": [],
                "examples": []
            }

        elif current_section:
            if tag.name == "pre":
                raw_text = tag.get_text()
                if is_ascii_table(raw_text):
                    current_section["syntax"].append(strip_unicode(raw_text.strip()))
                elif "example" in current_section["heading"].lower():
                    current_section["examples"].append(strip_unicode(raw_text.strip()))
                else:
                    current_section["syntax"].append(strip_unicode(raw_text.strip()))
            elif tag.name in ["ul", "ol"]:
                current_section["description"] += "\n" + " ".join(
                    strip_unicode(li.get_text(strip=True)) for li in tag.find_all("li"))
            elif tag.name == "p":
                current_section["description"] += "\n" + strip_unicode(tag_text)

    if current_section:
        content.append(filter_non_empty_fields(current_section))

    return content

def filter_non_empty_fields(section):
    cleaned = {}
    for k, v in section.items():
        if isinstance(v, list):
            filtered_list = [item for item in v if item.strip()]
            if filtered_list:
                cleaned[k] = filtered_list
        else:
            if v.strip():
                cleaned[k] = v.strip()
    return cleaned

def scrape_page(playwright, relative_url):
    full_url = urljoin(BASE_URL, relative_url)
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(full_url)
    page.wait_for_load_state("networkidle")
    html = page.content()
    browser.close()

    soup = clean_html(html)
    sections = extract_sections(soup)

    return {
        "title": soup.title.string.strip(),
        "url": full_url,
        "sections": sections
    }

def scrape_all():
    with sync_playwright() as p:
        # Main page
        all_data = []
        all_data.append(scrape_page(p, MAIN_PAGE))

        # Linked pages
        for topic in LINKED_TOPICS:
            rel_path = f"/en/sql-reference/sql/{topic}"
            try :
                print(f"Scraping: {rel_path}")
                all_data.append(scrape_page(p, rel_path))
            except Exception as e:
                print(f"Error scraping {rel_path}: {e}")

        # Save as JSON
        with open("snowflake_session_variables.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    scrape_all()
    print("Scraping completed. Data saved ")
