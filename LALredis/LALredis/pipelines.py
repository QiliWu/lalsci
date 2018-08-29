# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

from elasticsearch_dsl.connections import connections
from LALredis.tools import tools
from LALredis.models.es_types import ESLAL


class LalPipeline(object):
    def process_item(self, item, spider):
        return item

class ElasticSearchPipeline(object):
    def process_item(self, item, spider):
        article = ESLAL()
        article.title = item['title']
        article.url = item['url']
        article.id = item['_id']
        article.abs_img_url = item['abs_img_url']
        article.year = item['year']
        article.authors = item['authors']
        article.citing_num = item['citing_num']
        article.company = item['company']
        article.abstract = item['abstract']
        article.doi = item['doi']
        article.journal = item['journal']
        article.keywords = item['keywords']

        es = connections.create_connection(ESLAL._doc_type.using, hosts=["12.34.56.78:9200"])
        article.suggest = tools.get_suggests(
            ESLAL._doc_type.index, ((article.title, 10), (article.keywords, 7), (article.abstract, 5)), es)
        article.save()
        return item

