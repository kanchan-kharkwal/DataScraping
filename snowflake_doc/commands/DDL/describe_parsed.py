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

def parse_dt_dd_with_floating_tables(selector):
    result = []
    children = selector.xpath('./*')  # get all direct children of section or block

    current_name = None
    description = ''
    i = 0
    while i < len(children):
        elem = children[i]
        tag = elem.root.tag.lower()

        if tag == 'dt':
            # Start of a new field
            current_name = ' '.join(elem.xpath('.//text()').getall()).strip()
            description = ''
            i += 1

            # Try to get the <dd> directly after <dt>
            if i < len(children) and children[i].root.tag.lower() == 'dd':
                dd_elem = children[i]
                desc_parts = dd_elem.xpath('.//p//text()').getall() or dd_elem.xpath('.//text()').getall()
                description = ' '.join(p.strip() for p in desc_parts if p.strip())
                i += 1

            # Check if a <table> immediately follows
            if i < len(children) and children[i].root.tag.lower() == 'table':
                table = children[i]
                headers = table.xpath('.//thead/tr/th/text()').getall()
                headers = [h.strip() for h in headers if h.strip()]
                rows = []
                for row in table.xpath('.//tbody/tr'):
                    cells = row.xpath('.//td')
                    row_data = [cell.xpath('string(.)').get(default='').strip() for cell in cells]
                    if any(row_data):
                        rows.append(row_data)
                if headers:
                    table_strs = []
                    table_strs.append(' | '.join(headers))
                    table_strs.append('-|-'.join(['---'] * len(headers)))
                    for r in rows:
                        table_strs.append(' | '.join(r))
                    description += '\n\n' + '\n'.join(table_strs)
                i += 1

            if current_name:
                result.append({
                    'name': current_name.strip(),
                    'description': description.strip()
                })
                current_name = None

        else:
            i += 1

    return result


def parse_all_parameter_sections(response):
    all_args = []
    sections = response.xpath('//section[contains(translate(@id, "PARAMETER", "parameter"), "parameter")]')

    for section in sections:
        for dl in section.xpath('.//dl'):
            all_args.extend(parse_dt_dd_with_floating_tables(dl))

    for block in response.xpath('//blockquote'):
        all_args.extend(parse_dt_dd_with_floating_tables(block))

    return all_args



def parse_examples_with_titles(response):
    examples = []
    all_example_blocks = response.xpath('//section[@id="examples"]//pre') or response.xpath('//pre')

    for block in all_example_blocks:
        title = block.xpath('./preceding-sibling::h2[1]/text()').get() or \
                block.xpath('./preceding-sibling::h3[1]/text()').get() or \
                ''
        code = block.xpath('string(.)').get()
        if code:
            example = {'code': code.strip()}
            if title.strip():
                example['title'] = title.strip()
            examples.append(example)
    return examples


def parse_tables(response):
    """
    Extracts all tables on the page with headers and rows.
    """
    tables = []
    for table in response.xpath('//table'):
        headers = table.xpath('.//thead/tr/th/text()').getall()
        headers = [h.strip() for h in headers if h.strip()]

        rows = []
        for row in table.xpath('.//tbody/tr'):
            cells = row.xpath('.//td')
            row_data = [cell.xpath('string(.)').get(default='').strip() for cell in cells]
            if any(row_data):
                rows.append(row_data)

        if headers and rows:
            tables.append({'headers': headers, 'rows': rows})
    return tables


class SnowflakeDDLSpider(scrapy.Spider):
    name = 'snowflake_ddl'
    start_urls = ['https://docs.snowflake.com/en/sql-reference/sql/desc']

    custom_settings = {
        'FEEDS': {
            'D:/Ridgeant/POC\'s/DataScraping/snowflake_doc/commands/DDL/describe_scraped.json': {
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
        self.logger.info("Collecting sub-links under ALTER...")

        sub_links = response.xpath('//main//ul/li//a/@href').getall()
        extra_links = response.xpath('//main//dl//a/@href').getall()
        all_links = list(set(sub_links + extra_links))

        for link in all_links:
            full_url = urljoin(response.url, link)
            self.logger.info(f"Following sublink: {full_url}")
            yield response.follow(full_url, callback=self.parse_construct_detail, meta={'url': full_url})

    def parse_construct_detail(self, response):
        title = response.css('main h1::text').get(default='').strip()
        description = response.xpath('//main//h1/following-sibling::p[1]').xpath('string(.)').get(default='').strip()
        syntax = parse_pre_blocks(response, 'syntax')
        examples = parse_examples_with_titles(response)
        parameters = parse_all_parameter_sections(response)
        tables = parse_tables(response)

        usage_notes_raw = response.xpath('//section[@id="usage-notes"]//p').xpath('string(.)').getall()
        usage_notes = '\n'.join(p.strip() for p in usage_notes_raw if p.strip())

        if not any([title, description, syntax, examples, parameters, tables, usage_notes]):
            self.logger.warning(f"No content found for: {response.url}")
            return

        result = {
            'url': response.meta['url']
        }
        add_if_not_empty(result, 'title', title)
        add_if_not_empty(result, 'description', description)
        add_if_not_empty(result, 'syntax', syntax)
        add_if_not_empty(result, 'examples', examples)
        add_if_not_empty(result, 'parameters', parameters)
        add_if_not_empty(result, 'tables', tables)
        add_if_not_empty(result, 'usage_notes', usage_notes)

        self.logger.info(f"Scraped: {title}")
        yield result


if __name__ == '__main__':
    print("Starting scraper for Snowflake DDL constructs (DESCRIBE)...")
    process = CrawlerProcess(settings=SnowflakeDDLSpider.custom_settings)
    process.crawl(SnowflakeDDLSpider)
    process.start()
    print("Scraping completed. Data saved.")
