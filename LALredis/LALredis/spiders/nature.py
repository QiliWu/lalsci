# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import Request
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags


class NatureSpider(RedisSpider):
    name = 'nature'
    redis_key = "nature:start_urls"
    start_urls = ['https://www.nature.com/search?q=laser%20ablation%20in%20liquid&page={0}'
                  .format(i) for i in range(1, 40)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        # 获取文章链接
        article_urls = response.css('.h3.extra-tight-line-height a::attr(href)').extract()
        for url in article_urls:
            yield Request(url=url, callback=self.parse_article)

    def parse_article(self, response):
        lalitem = LalItem()

        lalitem['url'] = response.url
        title = response.css('header .tighten-line-height.small-space-below').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        lalitem['title'] = title_match.group(1)
        lalitem['journal'] = response.css('meta[name="citation_journal_title"]::attr(content)').extract()[0]
        lalitem['doi'] = response.css('meta[name="citation_doi"]::attr(content)').extract()[0]
        lalitem['year'] = response.css('meta[name="citation_online_date"]::attr(content)').extract()[0].split('/')[0]
        abstract_text = response.css('.pl20.mq875-pl0.js-collapsible-section p').extract()[0]
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        lalitem['abstract'] = abstract_match.group(1)
        img_match = re.match(r'.*?"index" : 1.*?"imagePaths" : \[ "(.*?jpg)" \].*', response.text, re.S)
        if img_match:
            lalitem['abs_img_url'] = ('https:'+img_match.group(1)) if not img_match.group(1).startswith('http') else img_match.group(1)
        else:
            lalitem['abs_img_url'] = ''

        lalitem['keywords'] = ', '.join(response.css('.subject-tag-link::text').extract())
        author_group = response.css('li[itemprop="author"]').extract()
        commun_author = [author for author in author_group if 'data-corresp-id' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<span itemprop="name".*?>(?:<a data-test="author-name".*?>)?(.+?)(?:</a>)?</span.*', author, re.S)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        lalitem['authors'] = ', '.join(authors)

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


