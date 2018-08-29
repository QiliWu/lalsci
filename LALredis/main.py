from scrapy.cmdline import execute
import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(path)


execute(['scrapy', 'crawl', 'scidir'])
execute(['scrapy', 'crawl', 'springer'])
execute(['scrapy', 'crawl', 'acs'])
execute(['scrapy', 'crawl', 'rsc'])
execute(['scrapy', 'crawl', 'wiley'])
execute(['scrapy', 'crawl', 'aip'])
execute(['scrapy', 'crawl', 'iop'])
execute(['scrapy', 'crawl', 'osa'])
execute(['scrapy', 'crawl', 'aps'])
execute(['scrapy', 'crawl', 'nature'])
execute(['scrapy', 'crawl', 'science'])