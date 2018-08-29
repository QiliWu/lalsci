#通过CrawlerProcess同时运行几个spider
from scrapy.crawler import CrawlerProcess
#导入获取项目配置的模块
from scrapy.utils.project import get_project_settings

#导入自己创建的spiders
from LALredis.spiders.acs import AcsSpider
from LALredis.spiders.aip import AipSpider
from LALredis.spiders.aps import ApsSpider
from LALredis.spiders.iop import IopSpider
from LALredis.spiders.nature import NatureSpider
from LALredis.spiders.osa import OsaSpider
from LALredis.spiders.rsc import RscSpider
from LALredis.spiders.scidir import ScidirSpider
from LALredis.spiders.science import ScienceSpider
from LALredis.spiders.springer import SpringerSpider
from LALredis.spiders.wiley import WileySpider


process = CrawlerProcess(get_project_settings())

process.crawl(AcsSpider)
process.crawl(AipSpider)
process.crawl(ApsSpider)
process.crawl(IopSpider)
process.crawl(NatureSpider)
process.crawl(OsaSpider)
process.crawl(RscSpider)
process.crawl(ScidirSpider)
process.crawl(ScienceSpider)
process.crawl(SpringerSpider)
process.crawl(WileySpider)

process.start()