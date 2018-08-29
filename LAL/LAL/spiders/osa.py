# -*- coding: utf-8 -*-
import scrapy
from scrapy import FormRequest, Request
import json
import re
from LAL.items import LalItem
from LAL.tools.tools import get_md5


class OsaSpider(scrapy.Spider):
    name = 'osa'
    allowed_domains = ['www.osapublishing.org']
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
        osaitem = LalItem()
        data = response.meta['data']
        osaitem['url'] = response.url
        osaitem['title'] = data['title']
        osaitem['authors'] = data['author'].split('; ')
        osaitem['doi'] = data['doi']
        osaitem['journal'] = response.css('.article-journal-name li strong::text').extract_first('')
        if not osaitem['journal']:
            osaitem['journal'] = data['name'].split(',')[0]

        osaitem['year'] = int(data['years'])
        osaitem['keywords'] = []
        osaitem['abs_img_url'] = response.css('img[alt="Fig. 1"]::attr(data-src)').extract_first(default='')

        #citing_num是隐藏字段，display:none，需要使用selenium。有点麻烦。就不取了
        osaitem['citing_num'] = 0

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
        osaitem['abstract'] = ''.join(abstract_list)

        osaitem['_id'] = get_md5(osaitem['url'])
        osaitem['company'] = self.name

        yield osaitem

