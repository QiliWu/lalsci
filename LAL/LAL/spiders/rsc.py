# -*- coding: utf-8 -*-
import scrapy
from scrapy import FormRequest, Request
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5


class RscSpider(scrapy.Spider):
    name = 'rsc'
    allowed_domains = ['pubs.rsc.org']
    start_urls = ['http://pubs.rsc.org/en/results?searchtext=laser%20ablation%20in%20liquid']

    def parse(self, response):
        #通过post请求start_url获取包含数据的js文件
        searchterm = response.css('input#SearchTerm::attr(value)').extract()[0]
        m = re.match(r'.*?{"Type":"all","Count":.*?},{"Type":"(.*?)","Count":(.*?)}.*', response.text, re.S)
        category = m.group(1)
        resultcount = m.group(2)

        for i in range(70):
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
        rscitem = LalItem()
        rscitem['url'] = response.url
        # 部分title中会有子标签
        title = response.css('.article__title h2 p, .article__title p, .article__title h2, .article-control h2').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.*?>', title, re.S)
        rscitem['title'] = title_match.group(1).strip()

        rscitem['journal'] = response.css('.h--heading3.no-heading::text').extract_first(default='')
        rscitem['doi'] = response.css('.list__item-data::text')[1].extract()

        abstract_text = response.css('.capsule__text p').extract_first(default='')
        if abstract_text:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            rscitem['abstract'] = abstract_match.group(1)
        else:
            rscitem['abstract'] = ''

        img_url = response.css('.capsule__article-image img::attr(src)').extract_first(default='')
        if img_url:
            rscitem['abs_img_url'] = 'https://pubs.rsc.org' + img_url
        else:
            rscitem['abs_img_url'] = ''

        #citing_num需要额外请求js文件，不过rsc提供的值不太准，考虑中
        rscitem['citing_num'] = 0

        rscitem['keywords'] = []
        year_info = response.css('.article-nav__issue.autopad--h a::text').extract_first(default='')
        if year_info:
            year_match = re.match(r'.*Issue \d+, (\d{4}).*', year_info)
            rscitem['year'] = int(year_match.group(1))
        else:
            rscitem['year'] = None

        author_group = response.css('.article__author-link').extract()
        commun_author = [author for author in author_group if '>*</' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<a href=.*?>(.+?)</a.*', author, re.S)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        rscitem['authors'] = authors

        rscitem['_id'] = get_md5(rscitem['url'])
        rscitem['company'] = self.name

        yield rscitem
