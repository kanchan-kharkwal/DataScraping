import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin

def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value
        
class SnowflakeCmdsSpider(scrapy.Spider):
    name = 'snowflake_functions'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/sql-all']
    
    custom_settings = {
        'FEEDS': {
            'D:\Ridgeant\POC\'s\DataScraping\snowflake_doc\commands\snowflake_cmds_all.json': {
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
        Parses the response and extracts function data from the table.
        """
        # look for a table within the <main> element.
        table = response.css('main table')

        if not table:
            self.log("ERROR: No table found on the page with the selector 'main table'. The website structure may have changed.")
            return
            
        # Iterate over each row in the table
        for row in table.css('tr'):
            cells = row.css('td')
            # Ensure it is a data row with 3 columns and a link in the first column
            if len(cells) == 2 and cells[0].css('a'):
                link = cells[0].css('a::attr(href)').get()
                function_url = urljoin(response.url, link)

                yield response.follow(
                    function_url,
                    callback=self.parse_function_details,
                    meta={
                        'function_name': cells[0].xpath('string(.)').get().strip(),
                        'summary': cells[1].xpath('string(.)').get().strip(),
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
        
        parameters = response.xpath('//section[contains(@id="parameters")]//p/text()').get(default='')


        # Syntax - extract full inner text even if nested inside <span>, etc.
        syntax_block = response.xpath('//section[@id="syntax"]//pre').xpath('string(.)').get()
        syntax = syntax_block.strip() if syntax_block else ''

        # Examples - multiple <pre> blocks under #examples section
        example_blocks = response.xpath('//section[@id="examples"]//pre')
        examples = [ex.xpath('string(.)').get().strip() for ex in example_blocks if ex.xpath('string(.)').get()]
        example = '\n\n'.join(examples)
        
        # Arguments
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

        # Return type
        usage_note = response.xpath('//section[@id="usage-notes"]//p').xpath('string(.)').get()
        usage_notes = usage_note.strip() if usage_note else ''
        
        result = {
            'function_name': response.meta['function_name'],
            'summary': response.meta['summary'],
            'url': response.meta['url']
        }
        
        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'example', example)
        add_if_not_empty(result, 'arguments', argument_pairs)
        add_if_not_empty(result, 'usage_notes', usage_notes)

        yield result

if __name__ == '__main__':
    print("Starting scraper to get Snowflake commands...")
    
    process = CrawlerProcess(settings=SnowflakeCmdsSpider.custom_settings)
    process.crawl(SnowflakeCmdsSpider)
    process.start()
    
    print("Scraping finished. DATA SAVED") 