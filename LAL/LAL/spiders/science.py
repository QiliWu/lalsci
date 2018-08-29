# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
import json
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5


class ScienceSpider(scrapy.Spider):
    name = 'science'
    #allowed_domains = ['search.sciencemag.org']  域名一直在变，所以取消这一项的限制
    start_urls = ['https://w35slb9cf3.execute-api.us-west-1.amazonaws.com/prod/search']

    def start_requests(self):
        #通过post请求start_url获取json格式数据
        for i in range(14):
            post_data = {"page":i,
                    "pagesize":10,
                    "orderby":"tfidf",
                    "rules":[{"field":"q","value":"laser ablation in liquid"},
                             {"field":"source",
                              "value":"\"sciencemag\" \"Science\" \"Science Advances\" \"Science Signaling\" \"Science Translational Medicine\" \"Science Immunology\" \"Science Robotics\" \"In the Pipeline\" \"Sciencehound\" \"Science Careers Blog\" \"Books, Et Al.\""}]}
            #这里其实formdata的key是字符串格式的post_data, value是'', 无法直接用formdata参数来传递，只能用body参数。
            yield Request(url=self.start_urls[0], body=json.dumps(post_data), method='POST', callback=self.parse)

    def parse(self, response):
        result = json.loads(response.body)
        datas = result['hitlist']
        for data in datas:
            url = data['canonical_url'][0]
            # Missing scheme in request url, 有些url没有http
            if not url.startswith('http:'):
                url = 'http:'+url
            yield Request(url=url, callback=self.parse_article, meta={'data':data})

    def parse_article(self, response):
        scienceitem = LalItem()
        scienceitem['url'] = response.url
        data = response.meta['data']
        scienceitem['title'] = data['title'][0]
        scienceitem['journal'] = data['source'][0]
        scienceitem['doi'] = data['doi'][0]
        scienceitem['authors'] = data['authors']
        scienceitem['year'] = int(data['pubyear'][0])

        abstract_text = response.css('.section.abstract p').extract()
        if abstract_text:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text[0], re.S)
            scienceitem['abstract'] = abstract_match.group(1)
        else:
            scienceitem['abstract'] = ''

        scienceitem['citing_num'] = 0
        scienceitem['abs_img_url'] = response.url+'/F1.large.jpg'
        scienceitem['keywords'] = []
        scienceitem['_id'] = get_md5(scienceitem['url'])
        scienceitem['company'] = self.name
        yield scienceitem

