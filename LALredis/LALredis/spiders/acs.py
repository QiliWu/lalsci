# -*- coding: utf-8 -*-

import os
import scrapy
from scrapy_redis.spiders import RedisSpider
from selenium import webdriver
from scrapy import Request
import re
from urllib.parse import urljoin, urlencode
from scrapy.selector import Selector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from w3lib.html import remove_tags

class AcsSpider(RedisSpider):
    name = 'acs'
    redis_key = "acs:start_urls"
    start_urls = [
        'https://pubs.acs.org/action/doSearch?AllField=laser+ablation+in+liquid&pageSize=50&startPage={0}'
        .format(i) for i in range(0,30)]

    def start_requests(self):
        #通过selenium+phantomjs来请求网页
        # # 伪装User Agent
        path = os.path.dirname(__file__).split('LALredis')[0]
        phantmjs_path = path + 'Scripts/phantomjs/bin/phantomjs.exe'
        #phantmjs_path = '/root/.pyenv/versions/lalproject/bin/phantomjs/bin/phantomjs'
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap['phantomjs.page.settings.userAgent'] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36")
        driver = webdriver.PhantomJS(desired_capabilities=dcap,executable_path=phantmjs_path)
        for url in self.start_urls:
            driver.get(url)
            try:
                element = WebDriverWait(driver, 300).until(
                    EC.presence_of_element_located((By.ID, 'pb-page-content'))
                )
            finally:
                text = driver.page_source
                response = Selector(text=text)
                article_links = response.css(
                    '.art_title.linkable a::attr(href)').extract()
                for i in range(len(article_links)):
                    full_link = urljoin('https://pubs.acs.org', article_links[i])
                    yield Request(url=full_link, callback=self.parse)
        driver.close()

    def parse(self, response):
        # 解析文章主页
        lalitem = LalItem()
        lalitem['url'] = response.url
        # 保留sub_tag
        title = response.css('.hlFld-Title').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        lalitem['title'] = title_match.group(1)

        lalitem['journal'] = response.css('#citation cite::text').extract_first(default='')
        lalitem['doi'] = response.css('#doi::text').extract()[0]
        #保留sub_tag
        abstract_text = response.css('.articleBody_abstractText').extract_first(default='')
        if abstract_text:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            lalitem['abstract'] = abstract_match.group(1)
        else:
            lalitem['abstract'] = ''

        abs_img_url = response.css('#absImg img::attr(src)').extract_first(default='')
        if abs_img_url:
            abs_img_url = urljoin('https://pubs.acs.org', abs_img_url)
        lalitem['abs_img_url'] = abs_img_url
        # lalitem['citing_num'] = len(response.css('#citedBy li'))
        lalitem['keywords'] = ''
        try:
            lalitem['year'] = int(response.css('.citation_year::text').extract()[0])
        except:
            lalitem['year'] = int(response.css('#pubDate::text').extract()[0][-4:])

        author_group = response.css('#authors > span').extract()
        commun_author = [author for author in author_group if '#cor1' in author]
        authors = []
        for author in author_group:
            match = re.match(r'.*<a id="authors".*?>(.+?)</a.*', author, re.S)
            if match:
                name = match.group(1)
                if author in commun_author:
                    name = name + '*'
                authors.append(name)
        lalitem['authors'] = ', '.join(authors)
        lalitem['_id'] = get_md5(lalitem['url'])
        lalitem['company'] = self.name
        #请求glgoo来获取citation
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