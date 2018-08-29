# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5

class IopSpider(scrapy.Spider):
    name = 'iop'
    allowed_domains = ['iopscience.iop.org']
    start_urls = ['http://iopscience.iop.org/nsearch?terms=laser+ablation+in+liquid&currentPage={0}&pageLength=20'
                  .format(i) for i in range(26)]

    def parse(self, response):
        # 获取文章链接
        article_urls = response.css('.art-list-item-title::attr(href)').extract()
        for url in article_urls:
            full_url = 'http://iopscience.iop.org' + url
            yield Request(url=full_url, callback=self.parse_article)

    def parse_article(self, response):
        # 解析文章主页
        iopitem = LalItem()
        iopitem['url'] = response.url
        # 保留sub_tag
        title = response.css('.wd-jnl-art-title').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        iopitem['title'] = title_match.group(1)

        iopitem['journal'] = response.css('.wd-jnl-art-breadcrumb-title a::text').extract()[0]

        doi_link = response.css('.wd-jnl-art-doi a::text').extract()[0]
        iopitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        try:
            abstract_text = response.css('.wd-jnl-art-abstract p').extract()[0]
        except:
            abstract_text = response.css('.wd-jnl-art-abstract').extract()[0]
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        iopitem['abstract'] = abstract_match.group(1)

        img_url = response.css('img[alt="Fig. 1."]::attr(src)').extract_first(default='')
        if img_url:
            iopitem['abs_img_url'] = img_url
        else:
            iopitem['abs_img_url'] = ''

        citing_num = response.css('.wd-jnl-art-cited-by::text').extract_first('')  #0引用时不出现该字段
        iopitem['citing_num'] = int(re.match(r'.*(\d+).*', citing_num).group(1)) if citing_num else 0

        iopitem['keywords'] = []
        year_info = response.css('.wd-jnl-art-article-info-citation p::text').extract()
        if year_info:
            year_match = re.match(r'.*\s(\d{4})\s.*', ' '.join(year_info))
            iopitem['year'] = int(year_match.group(1))
        else:
            iopitem['year'] = None

        iopitem['authors'] = response.css('.mb-0 span[itemprop="name"]::text').extract()
        iopitem['_id'] = get_md5(iopitem['url'])
        iopitem['company'] = self.name

        yield iopitem

