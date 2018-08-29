# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class LalItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    journal = scrapy.Field()
    doi = scrapy.Field()
    year = scrapy.Field()
    citing_num = scrapy.Field()

    abstract = scrapy.Field()
    abs_img_url = scrapy.Field()
    keywords = scrapy.Field()
    authors = scrapy.Field()
    _id = scrapy.Field()
    company = scrapy.Field()

