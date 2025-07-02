import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


class SnowflakeFunctionsSpider(scrapy.Spider):
    name = 'snowflake_functions'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/functions-all']

    custom_settings = {
        'FEEDS': {
            'snowflake_functions_parsed.json': {
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
        """
        Parses the function list page and follows links to function detail pages.
        """
        table = response.css('main table')
        if not table:
            self.log("ERROR: No function table found.")
            return

        for row in table.css('tr'):
            cells = row.css('td')
            if len(cells) == 3 and cells[0].css('a'):
                link = cells[0].css('a::attr(href)').get()
                function_url = urljoin(response.url, link)

                yield response.follow(
                    function_url,
                    callback=self.parse_function_details,
                    meta={
                        'function_name': cells[0].xpath('string(.)').get().strip(),
                        'summary': cells[1].xpath('string(.)').get().strip(),
                        'category': cells[2].xpath('string(.)').get().strip(),
                        'url': function_url
                    }
                )

    def parse_function_details(self, response):
        """
        Parses each function's detail page for title, description, syntax, and examples.
        """

        # Title from <h1>
        title = response.css('main h1::text').get(default='').strip()

        # Description - first paragraph in <main> (right under h1)
        description = response.css('main h1 + p::text').get(default='').strip()

        # Syntax - extract full inner text even if nested inside <span>, etc.
        syntax_block = response.xpath('//section[@id="syntax"]//pre').xpath('string(.)').get()
        syntax = syntax_block.strip() if syntax_block else ''

        # Examples - multiple <pre> blocks under #examples section
        example_blocks = response.xpath('//section[@id="examples"]//pre')
        examples = [ex.xpath('string(.)').get().strip() for ex in example_blocks if ex.xpath('string(.)').get()]
        example = '\n\n'.join(examples)
        
        # Arguments
        arg_blocks = response.xpath('//section[@id="arguments"]//p')
        arguments = [arg.xpath('string(.)').get().strip() for arg in arg_blocks if arg.xpath('string(.)').get()]
        arguments_text = '\n\n'.join(arguments)

        # Return type
        returns_block = response.xpath('//section[@id="returns"]//p').xpath('string(.)').get()
        returns = returns_block.strip() if returns_block else ''

        yield {
        'function_name': response.meta['function_name'],
        'summary': response.meta['summary'],
        'category': response.meta['category'],
        'url': response.meta['url'],
        'title': title,
        'description': description,
        'syntax': syntax,
        'example': example,
        'arguments': arguments_text,
        'returns': returns
    }

if __name__ == '__main__':
    print("Starting full scraper for Snowflake function details...")
    process = CrawlerProcess(settings=SnowflakeFunctionsSpider.custom_settings)
    process.crawl(SnowflakeFunctionsSpider)
    process.start()
    print("Scraping completed. Data saved to 'snowflake_functions_detailed.json'")
