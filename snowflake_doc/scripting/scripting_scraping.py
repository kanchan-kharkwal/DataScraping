import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


def add_if_not_empty(target_dict, key, value):
    if value:
        target_dict[key] = value


def parse_dt_dd_pairs(response, section_id):
    result = []
    pairs = response.xpath(f'//section[@id="{section_id}"]//dl/*')
    current_name = None

    for elem in pairs:
        tag = elem.root.tag
        if tag == 'dt':
            current_name = elem.xpath('.//span[@class="pre"]/text()').get() or elem.xpath('string(.)').get()
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


def parse_syntax_blocks(response, section_id):
    syntax_blocks = []
    section = response.xpath(f'//section[@id="{section_id}"]')

    if not section:
        return syntax_blocks
    
    pre_blocks = section.xpath('.//pre')

    for pre in pre_blocks:
        # Get the nearest heading above the <pre> (if any)
        heading = pre.xpath('./ancestor::*[self::div or self::section][1]/preceding-sibling::*[self::h2 or self::h3 or self::h4][1]')
        title = heading.xpath('string(.)').get(default='').strip()

        code = pre.xpath('string(.)').get()
        if code:
            block = {'code': code.strip()}
            if title:  # Only add title if non-empty
                block['title'] = title
            syntax_blocks.append(block)
    return syntax_blocks

def parse_usage_notes(response):
    """
    Extracts paragraphs and bullet points from the Usage Notes section.
    """
    section = response.xpath('//section[@id="usage-notes"]')
    if not section:
        return ""

    paragraphs = section.xpath('.//p//text()').getall()
    bullets = section.xpath('.//ul/li//text()').getall()
    combined = paragraphs + bullets

    return '\n'.join(t.strip() for t in combined if t.strip())



class SnowflakeScriptingSpider(scrapy.Spider):
    name = 'snowflake_scripting_all'
    start_urls = ['https://docs.snowflake.com/en/sql-reference-snowflake-scripting']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/scripting/snowflake_scripting.json': {
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
        self.logger.info("Parsing Snowflake Scripting page for Next Topic links...")

        # Parse "Next Topics" links
        next_topic_links = response.xpath('//section[contains(.,"Next Topics")]//a/@href').getall()

        for link in next_topic_links:
            full_url = urljoin(response.url, link)
            yield response.follow(full_url, callback=self.parse_scripting_topic, meta={'url': full_url})

    def parse_scripting_topic(self, response):
        title = response.css('main h1::text').get(default='').strip()
        description = response.xpath('//main//h1/following-sibling::p[1]').xpath('string(.)').get(default='').strip()
        syntax = parse_syntax_blocks(response, 'syntax')
        usage_notes = parse_usage_notes(response)
        examples = parse_examples_with_titles(response)

        returns_block = response.xpath('//section[@id="returns"]//p').xpath('string(.)').get()
        returns = returns_block.strip() if returns_block else ''

        result = {
            'url': response.meta['url']
        }

        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'usage notes', usage_notes)
        add_if_not_empty(result, 'examples', examples)
        add_if_not_empty(result, 'returns', returns)

        self.logger.info(f"Scraped: {title} from {response.meta['url']}")
        yield result


if __name__ == '__main__':
    print("Starting scraper for all Snowflake Scripting topics...")
    process = CrawlerProcess(settings=SnowflakeScriptingSpider.custom_settings)
    process.crawl(SnowflakeScriptingSpider)
    process.start()
    print("Scraping completed. Data saved.")
