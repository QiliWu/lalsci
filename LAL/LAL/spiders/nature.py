# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5
import ssl


class NatureSpider(scrapy.Spider):
    name = 'nature'
    allowed_domains = ['www.nature.com']
    start_urls = ['https://www.nature.com/search?q=laser%20ablation%20in%20liquid&page={0}'
                  .format(i for i in range(1, 40))]

    def parse(self, response):
        # 获取文章链接
        article_urls = response.css('.h3.extra-tight-line-height a::attr(href)').extract()
        for url in article_urls:
            yield Request(url=url, callback=self.parse_article)

        # # 获取下一页链接
        # next_url = response.css('li[data-page="next"] a::attr(href)').extract()
        # if next_url:
        #    full_next_url = 'https://www.nature.com' + next_url[0]
        #    yield Request(url=full_next_url, callback=self.parse)
        # else:
        #     print('No next page!')

    def parse_article(self, response):
        natureitem = LalItem()

        natureitem['url'] = response.url
        title = response.css('header .tighten-line-height.small-space-below').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        natureitem['title'] = title_match.group(1)
        #journal, doi新旧版本位置不一样
        try:
            natureitem['journal'] = response.css('.flex-box-item.none.border-gray-medium i::text').extract()[0]
            doi_tag = response.css('.flex-box-item.none.border-gray-medium li')[1].extract()
            doi_match = re.match(r'.*</abbr>:(.+?)</li>', doi_tag, re.S)
            natureitem['doi'] = doi_match.group(1)
            year_info = response.css('.flex-box-item.none.border-gray-medium li').extract()[0]
            year_match = re.match(r'.*\(.*(\d{4}).*\).*', year_info, re.S)
        except:
            natureitem['journal'] = response.css('.scroll-wrapper dd i::text').extract_first(default='')
            doi_tag = response.css('.scroll-wrapper dd').extract()[1]
            doi_match = re.match(r'.*>doi<.*?"(.+?)".*', doi_tag, re.S)
            natureitem['doi'] = doi_match.group(1)
            year_info = response.css('.scroll-wrapper dd').extract()[0]
            year_match = re.match(r'.*\(.*(\d{4}).*\).*', year_info, re.S)

        abstract_text = response.css('.pl20.mq875-pl0.js-collapsible-section p').extract()[0]
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        natureitem['abstract'] = abstract_match.group(1)
        img_match = re.match(r'.*?"index" : 1.*?"imagePaths" : \[ "(.*?jpg)" \].*', response.text, re.S)
        if img_match:
            natureitem['abs_img_url'] = ('https:'+img_match.group(1)) if not img_match.group(1).startswith('http') else img_match.group(1)
        else:
            natureitem['abs_img_url'] = ''

        citing_info = response.css('li[data-test="citation-count"]::text').extract()  # 如果没有引用，则就没有对应标签，结果为0
        natureitem['citing_num'] = int(citing_info[0].split(' ')[-1]) if citing_info else 0

        natureitem['keywords'] = response.css('.subject-tag-link::text').extract()
        natureitem['year'] = int(year_match.group(1))

        author_group = response.css('li[itemprop="author"]').extract()
        commun_author = [author for author in author_group if 'data-corresp-id' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<span itemprop="name".*?>(?:<a data-test="author-name".*?>)?(.+?)(?:</a>)?</span.*', author, re.S)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        natureitem['authors'] = authors

        natureitem['_id'] = get_md5(natureitem['url'])
        natureitem['company'] = self.name
        yield natureitem


