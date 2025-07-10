from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

BASE_URL = "https://docs.snowflake.com"
MAIN_PAGE = "/en/sql-reference/operators"

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "footer", "nav", "header", "noscript"]):
        tag.decompose()
    return soup

def strip_unicode(text):
    return re.sub(r"[^\x00-\x7F]+", "", text)

def extract_operator_categories(soup):
    categories = []
    table = soup.find("table")
    if not table:
        return categories
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) != 2:
            continue
        a_tag = cols[0].find("a")
        category_name = a_tag.get_text().strip()
        category_href = urljoin(BASE_URL + MAIN_PAGE, a_tag["href"])
        operators_raw = cols[1].get_text(separator=",").strip()
        operators_list = [op.strip() for op in re.split(r",|\s{2,}", operators_raw) if op.strip()]
        categories.append({
            "category": category_name,
            "url": category_href,
            "operators": operators_list
        })
    return categories

def parse_table(table_tag):
    headers = []
    rows = []
    thead = table_tag.find("thead")
    if thead:
        headers = [th.get_text().strip() for th in thead.find_all("th")]
    tbody = table_tag.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            row = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
            if row:
                rows.append(row)
    if headers and rows:
        return {"headers": headers, "rows": rows}
    return None

def extract_examples(soup):
    examples = []
    example_blocks = soup.select("div.highlight-sqlexample pre, div.highlight-output pre")
    for block in example_blocks:
        code = block.get_text().strip()
        if code:
            examples.append(code)
    return examples

def extract_sections(soup):
    content = []
    current_section = None
    tables_present = False

    for tag in soup.find_all(["h1", "h2", "h3", "p", "pre", "ul", "ol", "table", "dl"]):
        tag_text = tag.get_text().strip()

        if tag.name in ["h1", "h2", "h3"]:
            if current_section:
                if tables_present:
                    current_section.pop("description", None)
                    current_section.pop("syntax", None)
                    current_section.pop("definitions", None)
                content.append(filter_non_empty_fields(current_section))
            current_section = {
                "heading": strip_unicode(tag_text),
                "description": "",
                "syntax": [],
                "examples": [],
                "tables": [],
                "definitions": []
            }
            tables_present = False

        elif current_section:
            if tag.name == "table":
                parsed_table = parse_table(tag)
                if parsed_table:
                    current_section["tables"].append(parsed_table)
                    tables_present = True

            elif tag.name == "pre":
                if not tables_present:
                    current_section["syntax"].append(tag.get_text().strip())

            elif tag.name in ["ul", "ol"]:
                if not tables_present:
                    current_section["description"] += "\n" + " ".join(li.get_text().strip() for li in tag.find_all("li"))

            elif tag.name == "p":
                if not tables_present:
                    current_section["description"] += "\n" + strip_unicode(tag_text)

            elif tag.name == "dl":
                if not tables_present:
                    for dt_tag, dd_tag in zip(tag.find_all("dt"), tag.find_all("dd")):
                        term = dt_tag.get_text().strip()
                        definition = [p.get_text().strip() for p in dd_tag.find_all("p")]
                        if not definition:
                            definition = [dd_tag.get_text().strip()]
                        definition = " ".join(definition)
                        if term and definition:
                            current_section["definitions"].append({
                                "term": strip_unicode(term),
                                "definition": strip_unicode(definition)
                            })

    if current_section:
        if tables_present:
            current_section.pop("description", None)
            current_section.pop("syntax", None)
            current_section.pop("definitions", None)
        # Add examples from whole soup section (outside heading tags)
        examples = extract_examples(soup)
        if examples:
            current_section["examples"].extend(examples)
        content.append(filter_non_empty_fields(current_section))

    return content

def filter_non_empty_fields(section):
    return {k: v for k, v in section.items() if v and (v if isinstance(v, list) else v.strip())}

def scrape_page(playwright, url):
    print(f"Scraping: {url}")
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url)
    page.wait_for_load_state("networkidle")
    html = page.content()
    browser.close()

    soup = clean_html(html)
    sections = extract_sections(soup)

    return {
        "title": soup.title.string.strip() if soup.title else "No Title",
        "url": url,
        "sections": sections
    }

def scrape_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(urljoin(BASE_URL, MAIN_PAGE))
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()

        soup = clean_html(html)
        categories = extract_operator_categories(soup)

        all_data = []
        for category in categories:
            result = {
                "category": category["category"],
                "url": category["url"],
                "operators": category["operators"]
            }
            try:
                subpage = scrape_page(p, category["url"])
                result["details"] = subpage["sections"]
            except Exception as e:
                print(f"Failed to scrape {category['url']}: {e}")
                result["details"] = []

            all_data.append(result)

        with open("snowflake_operator_categories.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    scrape_all()
