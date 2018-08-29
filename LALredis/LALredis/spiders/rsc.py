# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import FormRequest, Request
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class RscSpider(RedisSpider):
    name = 'rsc'
    redis_key = "rsc:start_urls"
    start_urls = ['http://pubs.rsc.org/en/results?searchtext=laser%20ablation%20in%20liquid']

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        #通过post请求start_url获取包含数据的js文件
        searchterm = response.css('input#SearchTerm::attr(value)').extract()[0]
        m = re.match(r'.*?{"Type":"all","Count":.*?},{"Type":"(.*?)","Count":(.*?)}.*', response.text, re.S)
        category = m.group(1)
        resultcount = m.group(2)

        for i in range(1, 70):
            post_url = 'http://pubs.rsc.org/en/search/journalresult'
            #dict的值只能是字符串或者bytes
            post_data = {
                'searchterm':searchterm,
                'resultcount':resultcount,
                'category':category,
                'pageno':str(i)
            }
            yield FormRequest(url=post_url,
                              method='POST',
                              formdata=post_data,
                              callback=self.parse_jsresult,
                              meta={'post_data':post_data})


    def parse_jsresult(self, response):
        article_urls = response.css('a.capsule__action::attr(href)').extract()
        if article_urls:
            for url in article_urls:
                full_url = 'http://pubs.rsc.org' + url
                yield Request(url=full_url, callback=self.parse_article)
        else:
            #说明获取的是No Record Found页面, 重新发送请求
            yield FormRequest(url=response.url,
                              method='POST',
                              formdata=response.meta['post_data'],
                              callback=self.parse_jsresult)


    def parse_article(self, response):
        # 解析文章主页
        lalitem = LalItem()
        lalitem['url'] = response.url
        # 部分title中会有子标签

        title = response.css('.article__title h2 p, .article__title p, .article__title h2, .article-control h2').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.*?>', title, re.S)
        lalitem['title'] = title_match.group(1).strip()

        lalitem['journal'] = response.css('.h--heading3.no-heading::text').extract_first(default='')
        lalitem['doi'] = response.css('.list__item-data::text')[1].extract()

        abstract_text = response.css('.capsule__text p').extract_first(default='')
        if abstract_text:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            lalitem['abstract'] = abstract_match.group(1)
        else:
            lalitem['abstract'] = ''

        img_url = response.css('.capsule__article-image img::attr(src)').extract_first(default='')
        if img_url:
            lalitem['abs_img_url'] = 'https://pubs.rsc.org' + img_url
        else:
            lalitem['abs_img_url'] = ''

        lalitem['keywords'] = ''
        year_info = response.css('.article-nav__issue.autopad--h a::text').extract_first(default='')
        if year_info:
            year_match = re.match(r'.*Issue \d+, (\d{4}).*', year_info)
            lalitem['year'] = int(year_match.group(1))
        else:
            lalitem['year'] = None

        author_group = response.css('.article__author-link').extract()
        commun_author = [author for author in author_group if '>*</' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<a href=.*?>(.+?)</a.*', author, re.S)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        lalitem['authors'] = ', '.join(authors)
        lalitem['_id'] = get_md5(lalitem['url'])
        lalitem['company'] = self.name

        ##请求glgoo来获取citation
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

