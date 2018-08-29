# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
import re
from scrapy import Request
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class ScidirSpider(RedisSpider):
    name = 'scidir'
    redis_key = "scidir:start_urls"
    start_urls = ['https://www.sciencedirect.com/search?qs=laser%20ablation%20in%20liquid&offset={0}'
                      .format(i * 25) for i in range(200)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        #获取每篇文章的链接，并发送请求，然后response交给parse_article函数处理
        article_links = response.css('.result-list-title-link.u-font-serif.text-s::attr(href)').extract()
        for link in article_links:
            full_link = 'https://www.sciencedirect.com'+link
            yield Request(url=full_link, callback=self.parse_article)


    def parse_article(self, response):
        lalitem = LalItem()
        lalitem['url'] = response.url
        #title中可能有子标签
        title = response.css('.title-text').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        lalitem['title'] = title_match.group(1)

        lalitem['journal'] = response.css('.publication-title-link::text').extract()[0]

        doi_link = response.css('.DoiLink .doi::text').extract()[0]
        lalitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        abstract_text = response.css('.abstract.author p').extract()
        abstract_text = '\n'.join(abstract_text)
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        lalitem['abstract'] = abstract_match.group(1)

        img_url = response.css('.abstract.graphical img::attr(src)').extract_first(default='')
        if img_url:
            lalitem['abs_img_url'] = response.css('.abstract.graphical img::attr(src)').extract_first(default='')
        else:
            lalitem['abs_img_url'] = 'https://ars.els-cdn.com/content/image/1-s2.0-'+response.url.split('/')[-1]+'-gr1.jpg'

        lalitem['keywords'] = ', '.join(response.css('.keywords-section .keyword span::text').extract())

        year = response.css('.publication-volume .size-m::text, .publication-volume .text-xs::text').extract()
        year = ''.join(year)
        year_match = re.match(r'.*\s(\d{4}),.*', year)
        lalitem['year'] = int(year_match.group(1))

        author_group = response.css('.AuthorGroups .author').extract()
        commun_author = [author for author in author_group if '<svg' in author]
        authors = []

        for author in author_group:
            match = re.match(r'.*"text given-name">(.+?)<.*"text surname">(.+?)<.*', author)
            name = match.group(1)+ ' ' + match.group(2)
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






