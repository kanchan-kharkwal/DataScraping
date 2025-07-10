from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

BASE_URL = "https://docs.snowflake.com"
MAIN_PAGE = "/en/sql-reference/commands-transaction"

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "footer", "nav", "header", "noscript"]):
        tag.decompose()
    return soup

def strip_unicode(text):
    return re.sub(r"[^\x00-\x7F]+", "", text)

def is_ascii_table(text):
    return bool(re.search(r"\+\-+\+", text) or re.search(r"^\|\s?.+\s?\|", text, re.MULTILINE))

def extract_sections(soup):
    content = []
    current_section = None

    for tag in soup.find_all(["h1", "h2", "h3", "p", "pre", "ul", "ol"]):
        tag_text = tag.get_text(strip=True)

        if tag.name in ["h1", "h2", "h3"]:  
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
    print(f"Scraping: {full_url}")
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(full_url)
    page.wait_for_load_state("networkidle")
    html = page.content()
    browser.close()

    soup = clean_html(html)
    sections = extract_sections(soup)

    return {
        "title": soup.title.string.strip() if soup.title else "No Title",
        "url": full_url,
        "sections": sections
    }

def extract_transaction_links(soup):
    """Extract internal links from the main transaction commands page"""
    links = []
    section = soup.find("section", id="transaction-commands")
    if section:
        for a in section.find_all("a", href=True):
            href = a["href"]
            if href.startswith("sql/"):
                full = urljoin("/en/sql-reference/", href)
                links.append(full)
    return sorted(set(links))

def scrape_all():
    with sync_playwright() as p:
        all_data = []

        # Step 1: Scrape main transaction page
        main_data = scrape_page(p, MAIN_PAGE)
        all_data.append(main_data)

        # Step 2: Extract sub-command links
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(urljoin(BASE_URL, MAIN_PAGE))
        page.wait_for_load_state("networkidle")
        soup = clean_html(page.content())
        browser.close()

        sublinks = extract_transaction_links(soup)

        # Step 3: Scrape each sublink
        for link in sublinks:
            try:
                subpage_data = scrape_page(p, link)
                all_data.append(subpage_data)
            except Exception as e:
                print(f"Failed to scrape {link}: {e}")

        # Step 4: Save result
        with open("snowflake_transaction_commands.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    scrape_all()
