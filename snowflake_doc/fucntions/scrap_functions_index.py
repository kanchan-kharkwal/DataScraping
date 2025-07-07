import scrapy
from scrapy.crawler import CrawlerProcess

class SnowflakeFunctionsSpider(scrapy.Spider):
    name = 'snowflake_functions'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/functions-all']
    
    custom_settings = {
        'FEEDS': {
            'D:\Ridgeant\POC\'s\DataScraping\snowflake_doc\fucntions\snowflake_functions.json': {
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
            if len(cells) == 3 and cells[0].css('a'):
                function_name_raw = cells[0].xpath('string(.)').get()
                summary_raw = cells[1].xpath('string(.)').get()
                category_raw = cells[2].xpath('string(.)').get()

                yield {
                    'function_name': function_name_raw.strip() if function_name_raw else '',
                    'summary': summary_raw.strip() if summary_raw else '',
                    'category': category_raw.strip() if category_raw else '',
                }


if __name__ == '__main__':
    # To run this spider, you need to have Scrapy installed.
    
    print("Starting scraper to get Snowflake functions...")
    
    process = CrawlerProcess(settings=SnowflakeFunctionsSpider.custom_settings)
    process.crawl(SnowflakeFunctionsSpider)
    process.start()
    
    print("Scraping finished. Data saved to 'snowflake_functions.json'") 