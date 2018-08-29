# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5


class WileySpider(scrapy.Spider):
    name = 'wiley'
    allowed_domains = ['onlinelibrary.wiley.com']
    start_urls = ['https://onlinelibrary.wiley.com/action/doSearch?AllField=laser+ablation+in+liquid&startPage={0}'
                  .format(i for i in range(40))]

    def parse(self, response):
        #获取文章链接
        article_urls = response.css('.hlFld-Title a::attr(href)').extract()
        for url in article_urls:
            full_url = 'https://onlinelibrary.wiley.com'+url
            yield Request(url=full_url, callback=self.parse_article)

        # # 获取下一页链接
        # count = 1
        # while count<40: #只爬取前40页
        #     next_url = response.css('.pagination__btn--next::attr(href)').extract()
        #     if next_url:
        #        yield Request(url=next_url[0], callback=self.parse)
        #        count += 1
        #     else:
        #         print('No next page!')

    def parse_article(self, response):
        # 解析文章主页
        wileyitem = LalItem()
        wileyitem['url'] = response.url
        # 部分title中会有子标签
        try:#有些文章有两个title,第一个是德文的，第二个才是英文的
            title = response.css('.citation__title--second').extract()[0]
        except:
            title = response.css('.citation__title').extract()[0]

        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        title = title_match.group(1)
        wileyitem['title'] = re.sub('\n', ' ', title)

        wileyitem['journal'] = response.css('.article-citation h1 a::text').extract()[0]

        doi_link =  response.css('.epub-doi::text').extract()[0]
        wileyitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        abstract_text = response.css('.article-section__content p').extract()[0]
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        abstract_text = abstract_match.group(1)
        wileyitem['abstract'] = re.sub('\n', ' ', abstract_text)

        wileyitem['citing_num'] = int(response.css('a[href="#citedby-section"]::text').extract_first(default='0'))
        wileyitem['keywords'] = response.css('meta[name="citation_keywords"]::attr(content)').extract()
        wileyitem['year'] = int(response.css('.epub-date::text').extract()[0][-4:])

        author_group = response.css('.accordion-tabbed .accordion-tabbed__tab-mobile').extract()
        commun_author = [author for author in author_group if 'Corresponding Author' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<a href=.*?><span>(.+?)<.*', author, re.S)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        wileyitem['authors'] = authors

        wileyitem['_id'] = get_md5(wileyitem['url'])
        wileyitem['company'] = self.name

        toc_url = 'https://onlinelibrary.wiley.com' + response.css('a.volume-issue::attr(href)').extract()[0]
        yield Request(url=toc_url, callback=self.parse_toc, meta={'item':wileyitem})

    def parse_toc(self, response):
        wileyitem = response.meta['item']
        img_urls = response.css('.abstract-preview__zoom::attr(href)').extract()
        wileyitem['abs_img_url'] = ''
        for img_url in img_urls:
            if wileyitem['doi'].split('.')[-1] in img_url:
                wileyitem['abs_img_url'] = 'https:'+img_url
        yield wileyitem
