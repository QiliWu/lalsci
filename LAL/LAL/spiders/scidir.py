# -*- coding: utf-8 -*-
import scrapy
import re
from scrapy import Request
from LAL.items import LalItem
from LAL.tools.tools import get_md5


class ScidirSpider(scrapy.Spider):
    name = 'scidir'
    allowed_domains = ['www.sciencedirect.com']
    start_urls = ['https://www.sciencedirect.com/search?qs=laser%20ablation%20in%20liquid&offset={0}'
                  .format(i*25 for i in range(200))]

    def parse(self, response):
        #获取每篇文章的链接，并发送请求，然后response交给parse_article函数处理
        article_links = response.css('.result-list-title-link.u-font-serif.text-s::attr(href)').extract()
        for link in article_links:
            full_link = 'https://www.sciencedirect.com'+link
            yield Request(url=full_link, callback=self.parse_article)

        #查看是否有下一页，如果有，则获取链接并发送请求，返回的结果交给parse函数处理
        # count = 1
        # while count < 200: #只爬200页（前5000条数据）
        #     next_link = response.css('.next-link a::attr(href)').extract()
        #     if next_link:
        #         full_next_link = 'https://www.sciencedirect.com/search'+next_link[0][1:]
        #         yield Request(url=full_next_link, callback=self.parse)
        #         count += 1
        #     else:
        #         print("No next page!")

    def parse_article(self, response):
        scidiritem = LalItem()
        scidiritem['url'] = response.url
        #title中可能有子标签
        title = response.css('.title-text').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        scidiritem['title'] = title_match.group(1)

        scidiritem['journal'] = response.css('.publication-title-link::text').extract()[0]

        doi_link = response.css('.DoiLink .doi::text').extract()[0]
        scidiritem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        abstract_text = response.css('.abstract.author p').extract()
        abstract_text = '\n'.join(abstract_text)
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        scidiritem['abstract'] = abstract_match.group(1)

        img_url = response.css('.abstract.graphical img::attr(src)').extract_first(default='')
        if img_url:
            scidiritem['abs_img_url'] = response.css('.abstract.graphical img::attr(src)').extract_first(default='')
        else:
            scidiritem['abs_img_url'] = 'https://ars.els-cdn.com/content/image/1-s2.0-'+response.url.split('/')[-1]+'-gr1.jpg'
        #有少量abs_img_url是无效的
        citing_info = response.css('.related-content-links .button-text::text').extract()
        if citing_info:
            citing_num = ''.join(citing_info)
            num_match = re.match(r'.*\((\d+)\)', citing_num)
            scidiritem['citing_num'] = int(num_match.group(1))
        else:
            scidiritem['citing_num'] = 0

        scidiritem['keywords'] = response.css('.keywords-section .keyword span::text').extract()

        year = response.css('.publication-volume .size-m::text').extract()
        year = ''.join(year)
        year_match = re.match(r'.*\s(\d{4}),.*', year)
        scidiritem['year'] = int(year_match.group(1))

        author_group = response.css('.AuthorGroups .author').extract()
        commun_author = [author for author in author_group if '<svg' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*"text given-name">(.+?)<.*"text surname">(.+?)<.*', author)
            name = match.group(1)+ ' ' + match.group(2)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        scidiritem['authors'] = authors

        scidiritem['_id'] = get_md5(scidiritem['url'])
        scidiritem['company'] = self.name
        yield scidiritem





