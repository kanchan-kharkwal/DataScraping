from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json

BASE_URL = "https://docs.snowflake.com"
MAIN_PAGE = "/en/sql-reference/commands-function"


def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "footer", "nav", "header", "noscript"]):
        tag.decompose()
    return soup


def strip_unicode(text):
    return re.sub(r"[^\x00-\x7F]+", "", text)


def extract_function_links(soup):
    links = []
    for a in soup.select("main ul li a[href]"):
        href = a["href"]
        full_url = urljoin(BASE_URL + MAIN_PAGE, href)
        title = a.get_text(strip=True)
        links.append({
            "name": title,
            "url": full_url
        })
    return links


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
                else:
                    current_section.pop("_definitions_text", None)
                content.append(filter_non_empty_fields(current_section))
            current_section = {
                "heading": strip_unicode(tag_text),
                "description": "",
                "syntax": [],
                "examples": [],
                "tables": [],
                "definitions": [],
                "_definitions_text": set()
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
                    for li in tag.find_all("li"):
                        text = strip_unicode(li.get_text().strip())
                        if not overlaps_definition(text, current_section["_definitions_text"]):
                            current_section["description"] += "\n" + text

            elif tag.name == "p":
                if not tables_present:
                    para = strip_unicode(tag.get_text().strip())
                    if not overlaps_definition(para, current_section["_definitions_text"]):
                        current_section["description"] += "\n" + para

            elif tag.name == "dl":
                if not tables_present:
                    for dt_tag, dd_tag in zip(tag.find_all("dt"), tag.find_all("dd")):
                        term = strip_unicode(dt_tag.get_text().strip())
                        dd_texts = [p.get_text().strip() for p in dd_tag.find_all("p")] or [dd_tag.get_text().strip()]
                        definition = strip_unicode(" ".join(dd_texts).strip())
                        if term and definition:
                            current_section["definitions"].append({
                                "term": term,
                                "definition": definition
                            })
                            current_section["_definitions_text"].add(definition)

    if current_section:
        if tables_present:
            current_section.pop("description", None)
            current_section.pop("syntax", None)
            current_section.pop("definitions", None)
        else:
            current_section.pop("_definitions_text", None)
        content.append(filter_non_empty_fields(current_section))

    return content


def filter_non_empty_fields(section):
    return {k: v for k, v in section.items() if k != "_definitions_text" and v and (v if isinstance(v, list) else v.strip())}


def overlaps_definition(text, definition_set):
    text = re.sub(r"\s+", " ", text.strip())
    for defn in definition_set:
        defn_clean = re.sub(r"\s+", " ", defn.strip())
        if defn_clean in text or text in defn_clean:
            return True
    return False


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


def scrape_function_command_docs():
    with sync_playwright() as p:
        print(f"Loading main page: {BASE_URL + MAIN_PAGE}")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        main_url = urljoin(BASE_URL, MAIN_PAGE)
        page.goto(main_url)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()

        soup = clean_html(html)
        function_links = extract_function_links(soup)
        print(f"Found {len(function_links)} function links.\n")

        results = []
        for i, item in enumerate(function_links, start=1):
            print(f"[{i}/{len(function_links)}] {item['name']}")
            try:
                page_data = scrape_page(p, item["url"])
                results.append({
                    "function": item["name"],
                    "url": item["url"],
                    "details": page_data["sections"]
                })
            except Exception as e:
                print(f"Error scraping {item['url']}: {e}")
                results.append({
                    "function": item["name"],
                    "url": item["url"],
                    "error": str(e),
                    "details": []
                })

        with open("snowflake_command_functions.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("\nScraping completed. Data saved to snowflake_command_functions.json")


if __name__ == "__main__":
    scrape_function_command_docs()
