# -*- coding: utf-8 -*-
import scrapy
from selenium import webdriver
from scrapy import Request
import re
from urllib.parse import urljoin
from scrapy.selector import Selector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from LAL.items import LalItem
import os
from LAL.tools.tools import get_md5
import time

class AcsSpider(scrapy.Spider):
    name = 'acs'
    allowed_domains = ['pubs.acs.org']
    start_urls = [
        'https://pubs.acs.org/action/doSearch?AllField=laser+ablation+in+liquid&pageSize=50&startPage={0}'
        .format(i) for i in range(0,30)]
    #只爬前1500条

    def start_requests(self):
        #通过selenium+chrome来请求网页
        chrome_path = os.path.abspath(__file__).split('LAL')[0] + 'chromedriver.exe'
        driver = webdriver.Chrome(executable_path= chrome_path)
        for url in self.start_urls:
            driver.get(url)
            try:
                element = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.ID, 'pb-page-content'))
                )
                # for i in range(50):  #原本是想通过鼠标拖动滚动条来保证页面图片全部加载，后发现还是有图片缺失，放弃该方法
                #     driver.execute_script("window.scrollTo({0}*0.02*document.body.scrollHeight, {1}*0.02*document.body.scrollHeight); var lenOfPage=document.body.scrollHeight; return lenOfPage;".format(i, i+1))
                #     time.sleep(2)
            finally:
                text = driver.page_source
                response = Selector(text=text)
                article_links = response.css(
                    '.art_title.linkable a::attr(href)').extract()
                #img_links = response.css('.articleFigure img::attr(src)').extract()
                for i in range(len(article_links)):
                    full_link = urljoin('https://pubs.acs.org', article_links[i])
                    #img_link = img_links[i]
                    yield Request(url=full_link, callback=self.parse)#, meta={'img_link':img_link})

        driver.close()

    def parse(self, response):
        # 解析文章主页
        acsitem = LalItem()
        acsitem['url'] = response.url
        # 保留sub_tag
        title = response.css('.hlFld-Title').extract()[0]
        title_match = re.match(r'<.+?>(.+)</.+>', title, re.S)
        acsitem['title'] = title_match.group(1)

        acsitem['journal'] = response.css('#citation cite::text').extract_first(default='')
        acsitem['doi'] = response.css('#doi::text').extract()[0]
        #保留sub_tag
        abstract_text = response.css('.articleBody_abstractText').extract_first(default='')
        if abstract_text:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text, re.S)
            acsitem['abstract'] = abstract_match.group(1)
        else:
            acsitem['abstract'] = ''

        abs_img_url = response.css('#absImg img::attr(src)').extract_first(default='')
        if abs_img_url:
            abs_img_url = urljoin('https://pubs.acs.org', abs_img_url)
        acsitem['abs_img_url'] = abs_img_url
        # acsitem['abs_img_url'] = ('https://pubs.acs.org'+response.meta['img_link']) if response.meta['img_link'] else ''

        acsitem['citing_num'] = len(response.css('#citedBy li'))
        acsitem['keywords'] = []
        try:
            acsitem['year'] = int(response.css('.citation_year::text').extract()[0])
        except:
            acsitem['year'] = int(response.css('#pubDate::text').extract()[0][-4:])
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
        acsitem['authors'] = authors
        acsitem['_id'] = get_md5(acsitem['url'])
        acsitem['company'] = self.name

        yield acsitem
