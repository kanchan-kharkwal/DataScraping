import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value


class SnowflakeDDLSpider(scrapy.Spider):
    name = 'snowflake_ddl'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/sql-ddl-summary']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/commands/DDL/snowflake_ddl.json': {
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
        ddl_links = response.css('main ul.simple > li > a::attr(href)').getall()
        base_url = response.url

        for href in ddl_links:
            full_url = urljoin(base_url, href)
            yield response.follow(
                full_url,
                callback=self.parse_command_details,
                meta={'url': full_url}
            )

    def parse_command_details(self, response):
        title = response.css('main h1::text, main h1 span::text').get(default='').strip()
        description = response.css('main h1 + p::text').get(default='').strip()

        syntax_block = response.xpath('//section[@id="syntax"]//pre').xpath('string(.)').get()
        syntax = syntax_block.strip() if syntax_block else ''

        example_blocks = response.xpath('//section[@id="examples"]//pre')
        examples = [ex.xpath('string(.)').get().strip() for ex in example_blocks if ex.xpath('string(.)').get()]
        example = '\n\n'.join(examples)

        argument_pairs = []
        dt_dd_pairs = response.xpath('//section[@id="arguments"]//dl/*')
        arg_name = None
        for elem in dt_dd_pairs:
            tag = elem.root.tag
            if tag == 'dt':
                arg_name = elem.xpath('.//span[@class="pre"]/text()').get()
            elif tag == 'dd' and arg_name:
                arg_desc = elem.xpath('.//p//text()').getall()
                arg_desc = ' '.join([t.strip() for t in arg_desc if t.strip()])
                argument_pairs.append({
                    'name': arg_name.strip(),
                    'description': arg_desc
                })
                arg_name = None

        returns_block = response.xpath('//section[@id="returns"]//p').xpath('string(.)').get()
        returns = returns_block.strip() if returns_block else ''

        command_name = response.url.rstrip('/').split('/')[-1].upper()

        result = {
            'command_name': command_name,
            'url': response.meta['url'],
        }

        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'example', example)
        add_if_not_empty(result, 'arguments', argument_pairs)
        add_if_not_empty(result, 'returns', returns)

        yield result

if __name__ == '__main__':
    print("Starting full scraper for Snowflake DDL command documentation...")
    process = CrawlerProcess(settings=SnowflakeDDLSpider.custom_settings)
    process.crawl(SnowflakeDDLSpider)
    process.start()
    print("Scraping completed. Data saved.")
