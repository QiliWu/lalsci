# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import Request
import json
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class ScienceSpider(RedisSpider):
    name = 'science'
    redis_key = "science:start_urls"
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
        lalitem = LalItem()
        lalitem['url'] = response.url
        data = response.meta['data']
        lalitem['title'] = data['title'][0]
        lalitem['journal'] = data['source'][0]
        lalitem['doi'] = data['doi'][0]
        lalitem['authors'] = ', '.join(data['authors'])
        lalitem['year'] = int(data['pubyear'][0])

        abstract_text = response.css('.section.abstract p').extract()
        if abstract_text:
            abstract_match = re.match(r'<.+?>(.+)</.+>', abstract_text[0], re.S)
            lalitem['abstract'] = abstract_match.group(1)
        else:
            lalitem['abstract'] = ''

        lalitem['abs_img_url'] = response.url+'/F1.large.jpg'
        lalitem['keywords'] = ''
        lalitem['_id'] = get_md5(lalitem['url'])
        lalitem['company'] = self.name
        # #请求glgoo来获取citation
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

