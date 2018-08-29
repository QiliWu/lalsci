# -*- coding: utf-8 -*-
import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy import FormRequest, Request
import json
import re
from LALredis.items import LalItem
from LALredis.tools.tools import get_md5
from urllib.parse import urlencode
from w3lib.html import remove_tags

class OsaSpider(RedisSpider):
    name = 'osa'
    redis_key = "osa:start_urls"
    start_urls = ['https://www.osapublishing.org/search_wrapper.cfm']

    def start_requests(self):
        #通过post请求start_url获取json格式数据
        payload = {"map":{"_children":{"entry":[{"_children":{"key":"facets-length","value":{"_value":15,"_attributes":{"xsi:type":"xs:int"}}}},{"_children":{"key":"query-text","value":{"_value":"laser ablation in liquid","_attributes":{"xsi:type":"xs:string"}}}},{"_children":{"key":"start-value","value":{"_value":1,"_attributes":{"xsi:type":"xs:int"}}}},{"_children":{"key":"num-results","value":{"_value":20,"_attributes":{"xsi:type":"xs:int"}}}},{"_children":{"key":"any-topics","value":{"_value":True,"_attributes":{"xsi:type":"xs:boolean"}}}},{"_children":{"key":"search-in-journals","value":{"_value":True,"_attributes":{"xsi:type":"xs:boolean"}}}},{"_children":{"key":"search-in-conferences","value":{"_value":True,"_attributes":{"xsi:type":"xs:boolean"}}}},{"_children":{"key":"publi","value":{"_value":"none","_attributes":{"xsi:type":"xs:string"}}}},{"_children":{"key":"only-search-in","value":[{"_value":"title","_attributes":{"xsi:type":"xs:string"}},{"_value":"abstract","_attributes":{"xsi:type":"xs:string"}},{"_value":"author","_attributes":{"xsi:type":"xs:string"}}]}},{"_children":{"key":"sort-by","value":{"_value":"relevance-sort","_attributes":{"xsi:type":"xs:string"}}}},{"_children":{"key":"facet-options-selected","value":[{"_value":"year:item-order:descending","_attributes":{"xsi:type":"xs:string"}},{"_value":"journal:frequency-order:descending","_attributes":{"xsi:type":"xs:string"}},{"_value":"author:frequency-order:descending","_attributes":{"xsi:type":"xs:string"}},{"_value":"proceeding:frequency-order:descending","_attributes":{"xsi:type":"xs:string"}},{"_value":"level2:frequency-order:descending","_attributes":{"xsi:type":"xs:string"}},{"_value":"normalized:item-order:ascending","_attributes":{"xsi:type":"xs:string"}}]}}]}}}
        headers = {'content-type': 'application/json'}

        for i in range(5):
            payload['map']['_children']['entry'][2]['_children']['value']['_value'] = 20*i + 1
            #这里不能使用FormRequest, 因为它传递的是formdata, 后者会经过urlencode处理。
            #而这里我们需要将payload以json.stringfy的形式传递
            yield Request(url=self.start_urls[0],
                              body=json.dumps(payload),
                              headers=headers,
                              callback=self.parse)

    def parse(self, response):
        r = json.loads(response.body)
        results = r['response']['result']
        for result in results:
            data = result['data']
            url = 'https://www.osapublishing.org/abstract.cfm?uri=' + data['imgUri']
            yield Request(url=url, callback=self.parse_article, meta={'data':data})

    def parse_article(self, response):
        lalitem = LalItem()
        data = response.meta['data']
        lalitem['url'] = response.url
        lalitem['title'] = data['title']
        # lalitem['authors'] = data['author'].split('; ')
        lalitem['authors'] = data['author'].replace('; ', ', ')
        lalitem['doi'] = data['doi']
        lalitem['journal'] = response.css('.article-journal-name li strong::text').extract_first('')
        if not lalitem['journal']:
            lalitem['journal'] = data['name'].split(',')[0]

        lalitem['year'] = int(data['years'])
        lalitem['keywords'] = ''
        lalitem['abs_img_url'] = response.css('img[alt="Fig. 1"]::attr(data-src)').extract_first(default='')

        abstract_text = response.css('#articleBody p').extract()
        abstract_list = []
        if abstract_text:
            #有些文章是没有摘要的。如果有摘要，格式也是多变的。
            for element in abstract_text:
                if '©' in element:
                    break
                else:
                    abstract_match = re.match(r'<.+?>(.*)</.+>', element, re.S)
                    abstract_list.append(abstract_match.group(1))
        lalitem['abstract'] = ''.join(abstract_list)

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

