# lalsci
spider code for www.lalsci.com

1. www.lalsci.com

LALSCI是两个单词的缩写，分别是LAL(Laser Ablation in Liquids) 和SCI(Science Citation Index)的缩写。旨在为LAL领域的科研工作者提供一个专业领域的论文索引和国际课题组介绍的平台。

2. 项目具体内容

使用scrapy-redis实现的一个分布式网络爬虫，爬取了主流杂志社期刊上关于laser ablation in liquid（液相激光烧蚀法）研究的论文信息（包括：题目，链接，作者，发表年份，DOI，摘要等），爬取结果存入elasticsearch。

再基于数据库中的结果使用django构建出一个该领域文献搜索平台www.lalsci.com。

2.1 数据爬取逻辑

ACS：selenium + phantomjs浏览器爬虫获取js加载的目录页，从目录页html中提取文章链接，再请求论文链接以获得论文信息。

RSC、 Science、osapublishing ：文章目录页信息是ajax异步加载json文件获取，抓包获取相应json文件的url, 以POST或GET方式请求后，得到json数据，从json中提取出每篇文章对应的链接，请求该链接，分析返回的html并提取出文章信息。

Wiley：首先请求目录页获取每篇文章对应连接，请求该链接，分析返回的html并提取出文章信息，再请求文章所在期卷目录获取对象的toc图片链接。

Nature、 Springer、 sciencedirect、 iopscience、APS, AIP： 首先请求目录页获取每篇文章对应连接，请求该链接，分析返回的html并提取出文章信息。

每个爬虫最后在根据文章的title，请求google镜像网站glgoo获取文章引用次数信息。

2.2 存储方式

利用elasticsearch的映射功能创建具有自定义字段属性和类型的索引，将爬取到的文章信息都存储到该索引中，以供后续lalsci搜索平台使用。

2.3 避免爬虫被禁的策略
允许请求带上cookie
增加retry次数
实现了一个RandomUserAgentMiddleware， 可以不停的改变user-agent
实现了一个ProxyMiddleware，可以不停地改变ip代理

2.4 爬虫信息收集
将系统log信息写到文件中
重写了download middleware中的MyRetryMiddleware，收集请求失败的url

2.5 爬虫状态监测
修改了scrapy-redis包中schedule.py里的next_request函数。通过监测request=None(即队列为空）的次数来判断是否全部url爬取完毕了，连续一定次数请求的request都是None时，说明队列已经彻底爬取完毕了，触发爬虫关闭信息号，关闭爬虫。解决了redis中request队列为空时，scrapy爬虫一直空跑的问题。

3. 需要使用的库
scrapy, requests, scrapy-redis, selenium, redis, fake-useragent, pillow, pytesseract(用于付费ip网站验证码破解), elasticsearch-dsl(5.1.1版)

![lalsci](https://github.com/QiliWu/lalsci/blob/master/lalsci.png)
