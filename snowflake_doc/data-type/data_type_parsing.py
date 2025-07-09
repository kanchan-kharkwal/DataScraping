import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value


class SnowflakeDataTypeDetailsSpider(scrapy.Spider):
    name = 'snowflake_data_type_details'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/intro-summary-data-types']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/data-type/snowflake_data_types.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
                'indent': 4,
            },
        },
        'LOG_LEVEL': 'INFO'
    }

    def parse(self, response):
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
                        meta={'category_name': category_name.strip(), 'url': full_url}
                    )

    def parse_data_type_page(self, response):
        result = {
            'category': response.meta['category_name'],
            'url': response.meta['url'],
        }

        # Title and first paragraph
        title = response.css('h1::text').get(default='').strip()
        description = response.css('main h1 + p::text').get(default='').strip()
        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)

        # Syntax block
        syntax_block = response.xpath('//section[@id="syntax"]//pre')
        syntax = '\n\n'.join([s.xpath('string(.)').get().strip() for s in syntax_block if s.xpath('string(.)').get()])
        add_if_not_empty(result, 'syntax', syntax)

        # Example block
        example_blocks = response.xpath('//section[@id="examples"]//pre')
        examples = [ex.xpath('string(.)').get().strip() for ex in example_blocks if ex.xpath('string(.)').get()]
        add_if_not_empty(result, 'examples', examples)

        # Return section
        returns_block = response.xpath('//section[@id="returns"]//p')
        returns = ' '.join(p.xpath('string(.)').get().strip() for p in returns_block if p.xpath('string(.)').get())
        add_if_not_empty(result, 'returns', returns)

        yield result


# Run the spider directly
if __name__ == '__main__':
    process = CrawlerProcess()
    process.crawl(SnowflakeDataTypeDetailsSpider)
    process.start()
