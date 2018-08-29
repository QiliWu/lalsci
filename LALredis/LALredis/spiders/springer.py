# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import Request
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class SpringerSpider(RedisSpider):
    name = 'springer'
    redis_key = "springer:start_urls"
    start_urls = ['https://link.springer.com/search/page/{0}?facet-content-type=%22Article%22&query=laser+ablation+in+liquid'
                  .format(i) for i in range(1, 101)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        #获取文章链接，请求并将response交个parse_article处理
        article_links = response.css('#results-list .title::attr(href)').extract()
        for link in article_links:
            full_link = 'https://link.springer.com' + link
            yield Request(url=full_link, callback=self.parse_article)

    def parse_article(self, response):
        # 解析文章主页
        lalitem = LalItem()
        lalitem['url'] = response.url
        #部分title中会有子标签
        title =  response.css('.ArticleTitle').extract()[0]
        title_match =  re.match(r'<.+?>(.+)</.+>', title, re.S)
        lalitem['title'] = title_match.group(1)

        lalitem['journal'] = response.css('.JournalTitle::text').extract()[0]

        doi_link = response.css('#doi-url::text').extract()[0]
        lalitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        lalitem['year'] = int(response.css('.ArticleCitation_Year time::text').extract()[0][-4:])

        abstract_text = response.css('p.Para').extract_first(default='')
        try:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            lalitem['abstract'] = abstract_match.group(1)
        except:
            lalitem['abstract'] = ''

        img_url = response.css('div.Para img::attr(src)').extract_first(default='')
        if img_url:
            lalitem['abs_img_url'] = img_url
        else:
            try:
                journalid = re.match(r".*\'Journal Id\':\'(.+?)\'.*", response.text, re.S).group(1)
                part_1 = lalitem['doi'].split('/')[0]
                part_2 = lalitem['doi'].split('/')[1]
                part_3 = part_2.split('-')[2].replace('0', '')
                img_url = 'https://media.springernature.com/original/springer-static/image/art%3A{0}%2F{1}/MediaObjects/{2}_{3}_{4}_Fig1_HTML.jpg'
                lalitem['abs_img_url'] = img_url.format(part_1, part_2, journalid, lalitem['year'], part_3)
            except:
                lalitem['abs_img_url'] = ''

        lalitem['keywords'] = ', '.join(response.css('.KeywordGroup .Keyword::text').extract())

        author_group = response.css('.authors__list li').extract()
        commun_author = [author for author in author_group if 'authors__contact' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*class="authors__name">(.+?)<.*', author)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        lalitem['authors'] = ', '.join(authors)

        lalitem['_id'] = get_md5(lalitem['url'])
        lalitem['company'] = self.name
        # yield lalitem
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


