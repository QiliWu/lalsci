# -*- coding: utf-8 -*-
import scrapy
import json
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5
from scrapy import Request

class ApsSpider(scrapy.Spider):
    name = 'aps'
    allowed_domains = ['journals.aps.org']
    start_urls = ['https://journals.aps.org/search/results/json?sort=relevance&page={0}&clauses=%5B%7B%22field%22%3A%22all'
                  '%22%2C%22value%22%3A%22laser%20ablation%20in%20liquid%22%2C%22operator%22%3A%22AND%22%7D%5D'
                  .format(i) for i in range(20)]

    def parse(self, response):
        result = json.loads(response.body)
        datas = result['hits']
        for data in datas:
            url = 'https://journals.aps.org' + data['link']
            yield Request(url=url, callback=self.parse_article, meta={'data':data})

    def parse_article(self, response):
            apsitem = LalItem()
            data = response.meta['data']
            apsitem['url'] = response.url
            apsitem['title'] = data['title']
            apsitem['journal'] = data['citation'].split(' <')[0]
            apsitem['doi'] = data['doi']

            year_match = re.match(r'.*\((\d{4})\).*', data['citation'])
            apsitem['year'] = int(year_match.group(1))
            citing_info = data.get('citation_count_text', '')
            apsitem['citing_num'] = int(citing_info.split(' ')[0]) if citing_info else 0

            abstract_text = data['summary']
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            apsitem['abstract'] = abstract_match.group(1)

            img_url = response.css('.clear-wrap li img::attr(src)').extract()
            apsitem['abs_img_url'] = ('https://journals.aps.org'+ img_url[0]) if img_url else ''

            subject_areas = data.get('subject_areas', [])
            apsitem['keywords'] = [subject['label'] for subject in subject_areas] if subject_areas else []

            authors = data['authors'].split(', ')
            authors[-1] = re.sub(r'and ', '', authors[-1])
            apsitem['authors'] = authors

            apsitem['_id'] = get_md5(apsitem['url'])
            apsitem['company'] = self.name

            yield apsitem



