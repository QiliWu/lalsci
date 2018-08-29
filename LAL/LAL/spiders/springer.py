# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5


class SpringerSpider(scrapy.Spider):
    name = 'springer'
    allowed_domains = ['link.springer.com']
    start_urls = ['https://link.springer.com/search/page/{0}?facet-content-type=%22Article%22&query=laser+ablation+in+liquid'
                  .format(i for i in range(1, 101))]

    def parse(self, response):
        #获取文章链接，请求并将response交个parse_article处理
        article_links = response.css('#results-list .title::attr(href)').extract()
        for link in article_links:
            full_link = 'https://link.springer.com' + link
            yield Request(url=full_link, callback=self.parse_article)

        # 获取下一页链接,只爬取前100页
        # count=1
        # while count<100:
        #     next_link = response.css('.functions-bar-top .next::attr(href)').extract()
        #     if next_link:
        #         full_next_link = 'https://link.springer.com' + next_link[0]
        #         yield Request(url=full_next_link, callback=self.parse)
        #         count += 1
        #     else:
        #         print('No next page!')

    def parse_article(self, response):
        # 解析文章主页
        springeritem = LalItem()
        springeritem['url'] = response.url
        #部分title中会有子标签
        title =  response.css('.ArticleTitle').extract()[0]
        title_match =  re.match(r'<.+?>(.+)</.+>', title, re.S)
        springeritem['title'] = title_match.group(1)
        springeritem['journal'] = response.css('.JournalTitle::text').extract()[0]
        doi_link = response.css('#doi-url::text').extract()[0]
        springeritem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)
        springeritem['year'] = int(response.css('.ArticleCitation_Year time::text').extract()[0][-4:])

        abstract_text = response.css('p.Para').extract_first(default='')
        try:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            springeritem['abstract'] = abstract_match.group(1)
        except:
            springeritem['abstract'] = ''

        img_url = response.css('div.Para img::attr(src)').extract_first(default='')
        if img_url:
            springeritem['abs_img_url'] = img_url
        else:
            journalid = re.match(r".*\'Journal Id\':\'(.+?)\'.*", response.text, re.S).group(1)
            part_1 = springeritem['doi'].split('/')[0]
            part_2 = springeritem['doi'].split('/')[1]
            part_3 = part_2.split('-')[2].replace('0', '')
            img_url = 'https://media.springernature.com/original/springer-static/image/art%3A{0}%2F{1}/MediaObjects/{2}_{3}_{4}_Fig1_HTML.jpg'
            springeritem['abs_img_url'] = img_url.format(part_1, part_2, journalid, springeritem['year'], part_3)
        #有些是gif文件
        citing_num = response.css('#citations-count-number::text').extract_first(default='')
        if citing_num.endswith('k'):
            springeritem['citing_num'] = float(citing_num.split('k')[0])*1000
        else:
            springeritem['citing_num'] = int(citing_num) if citing_num else 0

        springeritem['keywords'] = response.css('.KeywordGroup .Keyword::text').extract()

        author_group = response.css('.authors__list li').extract()
        commun_author = [author for author in author_group if 'authors__contact' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*class="authors__name">(.+?)<.*', author)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        springeritem['authors'] = authors

        springeritem['_id'] = get_md5(springeritem['url'])
        springeritem['company'] = self.name
        yield springeritem


