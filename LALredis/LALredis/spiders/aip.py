# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import Request
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class AipSpider(RedisSpider):
    name = 'aip'
    redis_key = "aip:start_urls"
    start_urls = [
        'https://aip.scitation.org/action/doSearch?appendWebsiteFilter=false&AllField=laser+ablation+in+liquid&pageSize=20&startPage={0}'
            .format(i) for i in range(100)]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        #获取文章链接
        articles = response.css('.searchResultItem')
        for article in articles:
            url = article.css('.art_title a::attr(href)').extract()[0]
            full_url = 'https://aip.scitation.org'+url
            yield Request(url=full_url, callback=self.parse_article)

    def parse_article(self, response):
        # 解析文章主页
        lalitem = LalItem()
        lalitem['url'] = response.url
        # 保留sub_tag
        title = response.css('.publicationContentTitle h3').extract()[0]
        title_match = re.match(r'<h3>(.*?)<span.*', title, re.S)
        lalitem['title'] = title_match.group(1).strip()

        lalitem['journal'] = response.css('.publicationContentCitation::text').extract()[0].strip()
        doi_link = response.css('.publicationContentCitation a::text').extract()[0]
        lalitem['doi'] = re.sub(r'https://doi\.org/', '', doi_link)

        year_info = response.css('.publicationContentCitation::text').extract()[1].strip()
        year_match = re.match(r'.*\((\d{4})\).*', year_info)
        lalitem['year'] = int(year_match.group(1))

        abstract_text =  response.css('div.NLM_paragraph').extract()[0]
        lalitem['abstract'] = re.sub(r'(<|</)(div|named).*?>', '', abstract_text, re.S)

        img_url = response.css('.figure-no-f1 img::attr(src)').extract_first(default='')
        if img_url:
            lalitem['abs_img_url'] = 'https://aip.scitation.org' + img_url
        else:
            info_match = re.match(r".*journal=(.+?)&volume=(\d+?)&issue=(\d+?)&doi=10.1063/(.+?)\';.*", response.text, re.S)
            if info_match:
                jname, vol, issue, doiend = info_match.groups()
                img_url = 'https://aip.scitation.org/na101/home/literatum/publisher/aip/journals/content/{0}/{4}/{0}.{4}.{1}.issue-{2}/{3}/production/images/small/{3}.figures.f1.gif'
                lalitem['abs_img_url'] = img_url.format(jname, vol, issue, doiend, lalitem['year'])
                #此法对于2017-2018(即近两年)的文章是没有效果的
            else:
                lalitem['abs_img_url'] = ''

        lalitem['keywords'] = ', '.join(response.css('.topicTags a::text').extract())
        author_group = response.css('.contrib-author').extract()
        authors = ''.join([remove_tags(author) for author in author_group])
        lalitem['authors'] = authors.replace('a)', '*').strip()

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

