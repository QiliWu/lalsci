# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import Request
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class WileySpider(RedisSpider):
    name = 'wiley'
    redis_key = "wiley:start_urls"
    allowed_domains = ['onlinelibrary.wiley.com']
    start_urls = ['https://onlinelibrary.wiley.com/action/doSearch?AllField=laser+ablation+in+liquid&startPage={0}'
                  .format(i) for i in range(40)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        #获取文章链接
        article_urls = response.css('.hlFld-Title a::attr(href)').extract()
        for url in article_urls:
            full_url = 'https://onlinelibrary.wiley.com'+url
            yield Request(url=full_url, callback=self.parse_article)

    def parse_article(self, response):
        # 解析文章主页
        lalitem = LalItem()
        lalitem['url'] = response.url
        # 部分title中会有子标签
        try:#有些文章有两个title,第一个是德文的，第二个才是英文的
            title = response.css('.citation__title--second').extract()[0]
        except:
            title = response.css('.citation__title').extract()[0]

        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        title = title_match.group(1)
        lalitem['title'] = re.sub('\n', ' ', title)

        lalitem['journal'] = response.css('.article-citation h1 a::text').extract()[0]

        doi_link =  response.css('.epub-doi::text').extract()[0]
        lalitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        abstract_text = response.css('.article-section__content p').extract()[0]
        abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
        abstract_text = abstract_match.group(1)
        lalitem['abstract'] = re.sub('\n', ' ', abstract_text)

        lalitem['keywords'] = ', '.join(response.css('meta[name="citation_keywords"]::attr(content)').extract())
        lalitem['year'] = int(response.css('.epub-date::text').extract()[0][-4:])

        author_group = response.css('.accordion-tabbed .accordion-tabbed__tab-mobile').extract()
        commun_author = [author for author in author_group if 'Corresponding Author' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<a href=.*?><span>(.+?)<.*', author, re.S)
            name = match.group(1)
            if author in commun_author:
                name = name + '*'
            authors.append(name)
        lalitem['authors'] = ', '.join(authors)

        lalitem['_id'] = get_md5(lalitem['url'])
        lalitem['company'] = self.name

        toc_url = 'https://onlinelibrary.wiley.com' + response.css('a.volume-issue::attr(href)').extract()[0]
        yield Request(url=toc_url, callback=self.parse_toc, meta={'item':lalitem})

    def parse_toc(self, response):
        lalitem = response.meta['item']
        img_urls = response.css('.abstract-preview__zoom::attr(href)').extract()
        lalitem['abs_img_url'] = ''
        for img_url in img_urls:
            if lalitem['doi'].split('.')[-1] in img_url:
                lalitem['abs_img_url'] = 'https:'+img_url

        # #请求glgoo来获取citation
        glgoo_url = 'https://xs.glgoo.top/scholar?'
        headers = {'User_Agent': 'Mozilla/5.0', 'Referer': 'https://gf1.jwss.site/'}
        yield Request(url=glgoo_url + urlencode({'q': remove_tags(lalitem['title'])}) + '&hl=zh-CN&as_sdt=0&as_vis=1&oi=scholart',
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
