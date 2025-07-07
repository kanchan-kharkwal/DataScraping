import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin

def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value

class SnowflakeQuerySyntaxSpider(scrapy.Spider):
    name = 'snowflake_query_syntax'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/constructs']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/commands/Query/query_syntax_constructs.json': {
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
        self.logger.info("Parsing Query Syntax index page...")
        links = response.css('section#query-syntax ul a::attr(href)').getall()
        for link in links:
            full_url = urljoin(response.url, link)
            yield response.follow(full_url, callback=self.parse_construct_detail, meta={'url': full_url})

    def parse_construct_detail(self, response):
        title = response.css('main h1::text').get(default='').strip()
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

        result = {
            'url': response.meta['url']
        }

        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'example', example)
        add_if_not_empty(result, 'arguments', argument_pairs)
        add_if_not_empty(result, 'returns', returns)

        yield result

if __name__ == '__main__':
    print("Starting scraper for Snowflake Query Syntax constructs...")
    process = CrawlerProcess(settings=SnowflakeQuerySyntaxSpider.custom_settings)
    process.crawl(SnowflakeQuerySyntaxSpider)
    process.start()
    print("Scraping completed. Data saved.")
