import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin
from w3lib.html import remove_tags


class SnowflakeConstraintsSpider(scrapy.Spider):
    name = 'snowflake_constraints'
    allowed_domains = ['docs.snowflake.com']
    start_urls = ['https://docs.snowflake.com/en/sql-reference/constraints']

    custom_settings = {
        'FEEDS': {
            'snowflake_constraints_parsed.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
                'indent': 4,
            },
        },
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def parse(self, response):
        yield from self.parse_structured(response)

        # Extract sub-links within the constraints section
        next_links = response.xpath('//a[contains(@href, "/en/sql-reference/constraints")]/@href').getall()
        for link in set(next_links):
            abs_url = urljoin(response.url, link)
            if abs_url != response.url:
                yield scrapy.Request(abs_url, callback=self.parse_structured)

    def parse_structured(self, response):
        self.logger.info(f"Processing {response.url}")
        sections = []
        current_section = {"heading": "Introduction", "content": []}

        content_blocks = response.css('main > *') or response.xpath('//div[@id="markdown-body"]/*')

        for elem in content_blocks:
            tag = elem.root.tag.lower()

            # Headings
            if tag in ['h1', 'h2', 'h3', 'h4']:
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "heading": remove_tags(elem.get()).strip(),
                    "content": []
                }
                continue

            # Find all nested <pre> blocks inside this element
            code_blocks = elem.xpath('.//pre')
            extracted_codes = set()
            for code_elem in code_blocks:
                code_text = code_elem.xpath('string(.)').get()
                if code_text:
                    code_text = code_text.strip()
                    if code_text and code_text not in extracted_codes:
                        # Determine if it's syntax or code based on ancestor class
                        ancestor = code_elem.xpath('ancestor::*[@class[contains(., "highlight-sqlsyntax")]]')
                        block_type = "syntax" if ancestor else "code"
                        current_section["content"].append({
                            "type": block_type,
                            "value": code_text
                        })
                        extracted_codes.add(code_text)

            # Clone the element, remove <pre> blocks for clean text extraction
            clone = elem.root
            for pre in elem.xpath('.//pre'):
                pre_root = pre.root
                if pre_root.getparent() is not None:
                    pre_root.getparent().remove(pre_root)

            clean_html = scrapy.Selector(text=scrapy.Selector(root=clone).get())
            clean_text = remove_tags(clean_html.get()).strip()
            if clean_text and not any(clean_text in b["value"] for b in current_section["content"]):
                current_section["content"].append({
                    "type": "text",
                    "value": clean_text
                })

        if current_section["content"]:
            sections.append(current_section)

        yield {
            "page_name": response.url.rstrip('/').split("/")[-1] or "constraints",
            "url": response.url,
            "sections": sections
        }


if __name__ == '__main__':
    print("Starting scraper for Snowflake constraints documentation...")
    process = CrawlerProcess(settings=SnowflakeConstraintsSpider.custom_settings)
    process.crawl(SnowflakeConstraintsSpider)
    process.start()
    print("Scraping completed. Data saved.")
