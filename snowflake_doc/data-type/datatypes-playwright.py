import scrapy
from urllib.parse import urljoin


def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value


class SnowflakeDataTypeDetailsSpider(scrapy.Spider):
    name = 'snowflake_data_type_details'
    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/data-type/data_types.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
                'indent': 4,
            },
        },
        'LOG_LEVEL': 'INFO',
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            "headless": True
        }
    }

    start_urls = ['https://docs.snowflake.com/en/sql-reference/intro-summary-data-types']

    async def parse(self, response):
        rows = response.css('table tbody tr')
        visited = set()

        for row in rows:
            link = row.css('td:first-child a.reference.internal::attr(href)').get()
            category_name = row.css('td:first-child a.reference.internal span.doc::text').get()

            if link and category_name:
                full_url = urljoin(response.url, link)
                if full_url not in visited:
                    visited.add(full_url)
                    yield scrapy.Request(
                        url=full_url,
                        callback=self.parse_data_type_page,
                        meta={
                            'playwright': True,
                            'playwright_include_page': True,
                            'category_name': category_name.strip(),
                            'url': full_url
                        }
                    )

    async def parse_data_type_page(self, response):
        result = {
            'category': response.meta['category_name'],
            'url': response.meta['url'],
        }

        # Title and first paragraph
        title = response.css('h1::text').get(default='').strip()
        description = response.css('main h1 + p::text').get(default='').strip()
        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)

        # Syntax
        syntax_block = response.xpath('//section[@id="syntax"]//pre')
        syntax = '\n\n'.join([s.xpath('string(.)').get().strip() for s in syntax_block if s.xpath('string(.)').get()])
        add_if_not_empty(result, 'syntax', syntax)

        # Examples
        example_blocks = response.xpath('//section[@id="examples"]//pre')
        examples = [ex.xpath('string(.)').get().strip() for ex in example_blocks if ex.xpath('string(.)').get()]
        add_if_not_empty(result, 'examples', examples)

        # Returns
        returns_block = response.xpath('//section[@id="returns"]//p')
        returns = ' '.join(p.xpath('string(.)').get().strip() for p in returns_block if p.xpath('string(.)').get())
        add_if_not_empty(result, 'returns', returns)

        yield result

if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess
    process = CrawlerProcess()
    process.crawl(SnowflakeDataTypeDetailsSpider)
    process.start() 
    print("Scraping completed. Data saved.")