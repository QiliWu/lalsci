# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
import json
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from scrapy import Request
from urllib.parse import urlencode
from w3lib.html import remove_tags

class ApsSpider(RedisSpider):
    name = 'aps'
    redis_key = "aps:start_urls"
    start_urls = ['https://journals.aps.org/search/results/json?sort=relevance&page={0}&clauses=%5B%7B%22field%22%3A%22all'
                  '%22%2C%22value%22%3A%22laser%20ablation%20in%20liquid%22%2C%22operator%22%3A%22AND%22%7D%5D'
                  .format(i) for i in range(20)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        result = json.loads(response.body)
        datas = result['hits']
        for data in datas:
            url = 'https://journals.aps.org' + data['link']
            yield Request(url=url, callback=self.parse_article, meta={'data':data})

    def parse_article(self, response):
        lalitem = LalItem()
        data = response.meta['data']
        lalitem['url'] = response.url
        lalitem['title'] = data['title']
        lalitem['journal'] = data['citation'].split(' <')[0]
        lalitem['doi'] = data['doi']

        year_match = re.match(r'.*\((\d{4})\).*', data['citation'])
        lalitem['year'] = int(year_match.group(1))

        abstract_text = data['summary']
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        lalitem['abstract'] = abstract_match.group(1)

        img_url = response.css('.clear-wrap li img::attr(src)').extract()
        lalitem['abs_img_url'] = ('https://journals.aps.org'+ img_url[0]) if img_url else ''

        lalitem['keywords'] = ', '.join(response.css('a.physh-concept::text').extract())
        lalitem['authors'] = data['authors']
        lalitem['_id'] = get_md5(lalitem['url'])
        lalitem['company'] = self.name

        # #请求glgoo来获取citation
        glgoo_url = 'https://xs.glgoo.top/scholar?'
        headers = {'User_Agent': 'Mozilla/5.0', 'Referer': 'https://gf1.jwss.site/'}
        yield Request(
            url=glgoo_url + urlencode({'q': remove_tags(lalitem['title'])}) + '&hl=zh-CN&as_sdt=0&as_vis=1&oi=scholart',
            headers=headers,
            meta={'lalitem': lalitem},
            dont_filter=True,
            callback=self.get_citation)

    def get_citation(self, response):
        lalitem = response.meta['lalitem']
        data = response.css('.gs_ri .gs_fl').extract()[0]
        citing_info = re.findall(r'.*?被引用.*?(\d+?)<.*', data)
        lalitem['citing_num'] = int(citing_info[0]) if citing_info else 0
        yield lalitem


