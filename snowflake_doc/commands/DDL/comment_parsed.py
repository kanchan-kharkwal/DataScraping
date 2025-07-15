import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin


def add_if_not_empty(target, key, value):
    if value:
        target[key] = value


def parse_pre_blocks(response, section_id):
    blocks = response.xpath(f'//section[@id="{section_id}"]//pre')
    return '\n\n'.join(
        b.xpath('string(.)').get().strip()
        for b in blocks if b.xpath('string(.)').get()
    )


def parse_parameters(response):
    params = []
    sections = response.xpath('//section[contains(translate(@id, "PARAMETER", "parameter"), "parameter")]')
    for section in sections:
        for dl in section.xpath('.//dl'):
            dts = dl.xpath('./dt')
            dds = dl.xpath('./dd')
            for dt, dd in zip(dts, dds):
                name = ' '.join(dt.xpath('.//text()').getall()).strip()
                desc_parts = dd.xpath('.//p//text()').getall() or dd.xpath('.//text()').getall()
                desc = ' '.join(d.strip() for d in desc_parts if d.strip())
                if name:
                    params.append({'name': name, 'description': desc})
    return params


def parse_examples(response):
    examples = []
    example_blocks = response.xpath('//section[@id="examples"]//pre') or response.xpath('//pre')
    for block in example_blocks:
        title = block.xpath('./preceding-sibling::h2[1]/text()').get() or \
                block.xpath('./preceding-sibling::h3[1]/text()').get() or ''
        code = block.xpath('string(.)').get()
        if code:
            example = {'code': code.strip()}
            if title.strip():
                example['title'] = title.strip()
            examples.append(example)
    return examples


def parse_tables_in_examples(response):
    tables = []
    for table in response.xpath('//section[@id="examples"]//table'):
        headers = table.xpath('.//thead/tr/th//text()').getall()
        headers = [h.strip() for h in headers if h.strip()]
        rows = []
        for row in table.xpath('.//tbody/tr'):
            cells = row.xpath('./td')
            row_data = [cell.xpath('string(.)').get(default='').strip() for cell in cells]
            if any(row_data):
                rows.append(row_data)
        if headers and rows:
            tables.append({'headers': headers, 'rows': rows})
    return tables


class CommentCommandSpider(scrapy.Spider):
    name = 'snowflake_comment'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/sql/comment']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/commands/DDL/comment_scraped.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
                'indent': 4,
            },
        },
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0',
        'ROBOTSTXT_OBEY': True,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def parse(self, response):
        title = response.css('main h1::text').get(default='').strip()
        description = response.xpath('//main//h1/following-sibling::p[1]').xpath('string(.)').get(default='').strip()
        syntax = parse_pre_blocks(response, 'syntax')
        parameters = parse_parameters(response)
        usage_notes_raw = response.xpath('//section[@id="usage-notes"]//p').xpath('string(.)').getall()
        usage_notes = '\n'.join(p.strip() for p in usage_notes_raw if p.strip())
        examples = parse_examples(response)
        tables = parse_tables_in_examples(response)

        result = {'url': response.url}
        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'parameters', parameters)
        add_if_not_empty(result, 'usage_notes', usage_notes)
        add_if_not_empty(result, 'examples', examples)
        add_if_not_empty(result, 'tables', tables)

        self.logger.info(f"Scraped: {title}")
        yield result


if __name__ == '__main__':
    print("Starting scraper for Snowflake SQL COMMENT page...")
    process = CrawlerProcess(settings=CommentCommandSpider.custom_settings)
    process.crawl(CommentCommandSpider)
    process.start()
    print("Scraping completed. Data saved.")
