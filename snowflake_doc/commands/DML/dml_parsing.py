import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value


def parse_pre_blocks(response, section_id):
    blocks = response.xpath(f'//section[@id="{section_id}"]//pre')
    return '\n\n'.join(
        b.xpath('string(.)').get().strip()
        for b in blocks if b.xpath('string(.)').get()
    )


def parse_dt_dd_pairs(response, section_id):
    result = []
    pairs = response.xpath(f'//section[@id="{section_id}"]//dl/*')
    current_name = None

    for elem in pairs:
        tag = elem.root.tag
        if tag == 'dt':
            text_parts = elem.xpath('.//text()').getall()
            current_name = ' '.join(part.strip() for part in text_parts if part.strip())
        elif tag == 'dd' and current_name:
            desc_parts = elem.xpath('.//p//text()').getall() or elem.xpath('.//text()').getall()
            desc = ' '.join(t.strip() for t in desc_parts if t.strip())
            result.append({
                'name': current_name.strip(),
                'description': desc
            })
            current_name = None
    return result


def parse_examples_with_titles(response):
    examples = []
    example_sections = response.xpath('//section[@id="examples"]//section')
    if not example_sections:
        example_sections = response.xpath('//section[@id="examples"]')

    for sec in example_sections:
        title = (
            sec.xpath('.//h2/text()').get() or
            sec.xpath('.//h3/text()').get() or
            sec.xpath('.//p[1]/text()').get() or ''
        ).strip()

        code = sec.xpath('.//pre[1]').xpath('string(.)').get()
        if code:
            examples.append({
                'title': title,
                'code': code.strip()
            })

    return examples


class SnowflakeDMLSpider(scrapy.Spider):
    name = 'snowflake_dml'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/sql-dml']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/commands/DML/dml_constructs.json': {
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
        self.logger.info("Parsing DML page for subtopic links...")

        # All <ul><li><a> links
        subtopic_links = response.xpath('//main//ul/li//a/@href').getall()

        # Also grab validate link from <dl>
        extra_links = response.xpath('//main//dl//a/@href').getall()

        all_links = list(set(subtopic_links + extra_links))  # Deduplicate

        for link in all_links:
            full_url = urljoin(response.url, link)
            self.logger.info(f"Following link: {full_url}")
            yield response.follow(full_url, callback=self.parse_construct_detail, meta={'url': full_url})

    def parse_construct_detail(self, response):
        title = response.css('main h1::text').get(default='').strip()
        description = response.xpath('//main//h1/following-sibling::p[1]').xpath('string(.)').get(default='').strip()
        syntax = parse_pre_blocks(response, 'syntax')
        examples = parse_examples_with_titles(response)
        arguments = parse_dt_dd_pairs(response, 'arguments')
        parameters = parse_dt_dd_pairs(response, 'parameters')

        returns_block = response.xpath('//section[@id="returns"]//p').xpath('string(.)').get()
        returns = returns_block.strip() if returns_block else ''
        
        if not any([title, description, syntax, examples, arguments, parameters, returns]):
            self.logger.warning(f"No content found for: {response.url}")
            return

        result = {
            'url': response.meta['url']
        }

        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'examples', examples)
        add_if_not_empty(result, 'arguments', arguments)
        add_if_not_empty(result, 'parameters', parameters)
        add_if_not_empty(result, 'returns', returns)

        self.logger.info(f"Scraped: {title} from {response.meta['url']}")
        yield result


if __name__ == '__main__':
    print("Starting scraper for Snowflake DML constructs...")
    process = CrawlerProcess(settings=SnowflakeDMLSpider.custom_settings)
    process.crawl(SnowflakeDMLSpider)
    process.start()
    print("Scraping completed. Data saved.")
