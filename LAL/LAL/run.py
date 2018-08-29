#通过CrawlerProcess同时运行几个spider
from scrapy.crawler import CrawlerProcess
#导入获取项目配置的模块
from scrapy.utils.project import get_project_settings

#导入自己创建的spiders
from LAL.spiders.acs import AcsSpider
from LAL.spiders.aip import AipSpider
from LAL.spiders.aps import ApsSpider
from LAL.spiders.iop import IopSpider
from LAL.spiders.nature import NatureSpider
from LAL.spiders.osa import OsaSpider
from LAL.spiders.rsc import RscSpider
from LAL.spiders.scidir import ScidirSpider
from LAL.spiders.science import ScienceSpider
from LAL.spiders.springer import SpringerSpider
from LAL.spiders.wiley import WileySpider


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