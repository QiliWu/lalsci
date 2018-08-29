# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

from elasticsearch_dsl.connections import connections
from LAL.tools import tools
import json
import os
import pymongo
from LAL.tools.elements import elements
from scrapy.exceptions import DropItem
from w3lib.html import remove_tags

#数据存入mongodb， 同时也保存一份json文件
currpath = os.path.dirname(os.path.abspath('__file__'))
class LalPipeline(object):
    def process_item(self, item, spider):
        return item

class MongodbPipeline(object):
    #将数据存入mongodb
    def open_spider(self, spider):
        self.client= pymongo.MongoClient(host='localhost', port=27017)
        self.db = self.client['LAL']

    def process_item(self, item, spider):
        article = dict(item)
        self.db['all_articles'].insert(article)
        return item



class JsonPipeline(object):
    #将数据存入json文件
    def open_spider(self, spider):
        name = spider.name
        file_path = currpath + '\\results\\' + name + '.json'
        self.file = open(file_path, 'wb')

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line.encode('utf-8'))
        return item

    def spider_closed(self, spider):
        self.file.close()


from scrapy import signals
from scrapy.contrib.exporter import JsonLinesItemExporter

class JsonExportPipeline(object):
#JsonLinesItemExporter在处理大量数据时有优势。
    def __init__(self, spider):
        self.files = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        file = open(currpath+'\\results\\'+'%s_products.json' % spider.name, 'w+b')
        self.files[spider] = file
        self.exporter = JsonLinesItemExporter(file)
        self.exporter.start_exporting()

    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        file = self.files.pop(spider)
        file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item
