# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5

class AipSpider(scrapy.Spider):
    name = 'aip'
    allowed_domains = ['aip.scitation.org']
    start_urls = ['https://aip.scitation.org/action/doSearch?appendWebsiteFilter=false&AllField=laser+ablation+in+liquid&pageSize=20&startPage={0}'
                  .format(i for i in range(100))]

    def parse(self, response):
        #获取文章链接
        articles = response.css('.searchResultItem')
        for article in articles:
            url = article.css('.art_title a::attr(href)').extract()[0]
            full_url = 'https://aip.scitation.org'+url
            citation = article.css('.citation::text').extract_first(default='')
            citation = int(citation.split(' ')[0]) if citation else 0
            yield Request(url=full_url, callback=self.parse_article, meta={'citation':citation})
        #
        # #获取下一页链接
        # count = 1
        # while count < 101:
        #     next_url = response.css('.pageLink-with-arrow-next a::attr(href)').extract()
        #     if next_url:
        #        yield Request(url=next_url[0], callback=self.parse)
        #        count += 1
        #     else:
        #         print('No next page!')

    def parse_article(self, response):
        # 解析文章主页
        aipitem = LalItem()
        aipitem['url'] = response.url
        # 保留sub_tag
        title = response.css('.publicationContentTitle h3').extract()[0]
        title_match = re.match(r'<h3>(.*?)<span.*', title, re.S)
        aipitem['title'] = title_match.group(1).strip()

        aipitem['journal'] = response.css('.publicationContentCitation::text').extract()[0].strip()
        doi_link = response.css('.publicationContentCitation a::text').extract()[0]
        aipitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        year_info = response.css('.publicationContentCitation::text').extract()[1].strip()
        year_match = re.match(r'.*\((\d{4})\).*', year_info)
        aipitem['year'] = int(year_match.group(1))

        abstract_text =  response.css('div.NLM_paragraph').extract()[0]
        aipitem['abstract'] = re.sub(r'(<|</)(div|named).*?>', '', abstract_text, re.S)

        img_url = response.css('.figure-no-f1 img::attr(src)').extract_first(default='')
        if img_url:
            aipitem['abs_img_url'] = 'https://aip.scitation.org' + img_url
        else:
            info_match = re.match(r".*journal=(.+?)&volume=(\d+?)&issue=(\d+?)&doi=10.1063/(.+?)\';.*", response.text, re.S)
            if info_match:
                jname, vol, issue, doiend = info_match.groups()
                img_url = 'https://aip.scitation.org/na101/home/literatum/publisher/aip/journals/content/{0}/{4}/{0}.{4}.{1}.issue-{2}/{3}/production/images/small/{3}.figures.f1.gif'
                aipitem['abs_img_url'] = img_url.format(jname, vol, issue, doiend, aipitem['year'])
                #此法对于2017-2018(即近两年)的文章是没有效果的
            else:
                aipitem['abs_img_url'] = ''

        aipitem['citing_num'] = response.meta['citation']
        aipitem['keywords'] = response.css('.topicTags a::text').extract()
        author_group = response.css('.contrib-author').extract()
        commun_author = [author for author in author_group if 'a)' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<a href=.*?>(.+?)</a.*', author, re.S)
            name = match.group(1).strip()
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        aipitem['authors'] = authors

        aipitem['_id'] = get_md5(aipitem['url'])
        aipitem['company'] = self.name

        yield aipitem

