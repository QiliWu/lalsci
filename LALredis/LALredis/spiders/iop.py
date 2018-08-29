# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import Request
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class IopSpider(RedisSpider):
    name = 'iop'
    redis_key = "iop:start_urls"
    start_urls = ['http://iopscience.iop.org/nsearch?terms=laser+ablation+in+liquid&currentPage={0}&pageLength=20'
                  .format(i) for i in range(26)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        # 获取文章链接
        article_urls = response.css('.art-list-item-title::attr(href)').extract()
        for url in article_urls:
            full_url = 'http://iopscience.iop.org' + url
            yield Request(url=full_url, callback=self.parse_article)

    def parse_article(self, response):
        # 解析文章主页
        lalitem = LalItem()
        lalitem['url'] = response.url
        # 保留sub_tag
        title = response.css('.wd-jnl-art-title').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        lalitem['title'] = title_match.group(1)

        lalitem['journal'] = response.css('.wd-jnl-art-breadcrumb-title a::text').extract()[0]

        doi_link = response.css('.wd-jnl-art-doi a::text').extract()[0]
        lalitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        try:
            abstract_text = response.css('.wd-jnl-art-abstract p').extract()[0]
        except:
            abstract_text = response.css('.wd-jnl-art-abstract').extract()[0]
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        lalitem['abstract'] = abstract_match.group(1)

        img_url = response.css('img[alt="Fig. 1."]::attr(src)').extract_first(default='')
        if img_url:
            lalitem['abs_img_url'] = img_url
        else:
            lalitem['abs_img_url'] = ''

        lalitem['keywords'] = ''
        year_info = response.css('.wd-jnl-art-article-info-citation p::text').extract()
        if year_info:
            year_match = re.match(r'.*\s(\d{4})\s.*', ' '.join(year_info))
            lalitem['year'] = int(year_match.group(1))
        else:
            lalitem['year'] = None

        lalitem['authors'] = ', '.join(response.css('.mb-0 span[itemprop="name"]::text').extract())
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
