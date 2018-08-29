import requests
from scrapy.selector import Selector
import json
import pymongo



# class StoreIP(object):
#     def __init__(self):
#         self.client = pymongo.MongoClient(host='localhost', port=27017)
#         self.db = self.client['LAL']
#         self.collection = self.db['ippool']
#
#     def get_ip_from_api(self, api_url):
#         if not self.collection.find_one():
#             r = requests.get(api_url)
#             data = json.loads(r.text)
#             for proxy in data['msg']:
#                 self.collection.insert_one(proxy)

class GetIP(object):
    def __init__(self):
        self.client = pymongo.MongoClient(host='localhost', port=27017)
        self.db = self.client['LAL']
        self.collection = self.db['ippool']

    def get_ip_from_api(self):
        if not self.collection.find_one():
            url = 'http://piping.mogumiao.com/proxy/api/get_ip_al?appKey=??????aa21&count=5&expiryDate=0&format=1'

            r = requests.get(url)
            data = json.loads(r.text)
            for proxy in data['msg']:
                port = proxy['port']
                ip = proxy['ip']
                proxy_ip = ip + ':' + port
                self.collection.insert([{'proxy':'http://'+proxy_ip}, {'proxy':'https://'+proxy_ip}])

    def check_ip(self, proxy_dict):
        # 判断ip是否可用
        http_url = 'http://ip.chinaz.com/getip.aspx'
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'}
            response = requests.get(
                http_url, headers=headers, proxies=proxy_dict, timeout=2)
            response.raise_for_status()
            code = response.status_code
            # print(proxy_dict)
            if code >= 200 and code < 300:
                text = response.text
                for key, value in proxy_dict.items():
                    ip = re.match(r'.*://(.*?):\d+', value).group(1)
                    if ip in text:
                        return True
                    else:
                        return False
            else:
                return False
        except BaseException:
            return False

    def get_random_valid_ip(self):
        # 从数据库随机提取一个有效的ip
        item = list(self.collection.aggregate([{'$sample':{"size":1}}]))
        if item:
            proxy = item[0]['proxy']
            key = proxy.split(':')[0]
            proxy_dict = {key:proxy}
            if self.check_ip(proxy_dict):
                #print("有效ip:%s" % proxy)
                return proxy
            else:
                #print("无效的ip， 删除！")
                self.collection.delete_one({'_id':item[0]['_id']})
                return self.get_random_valid_ip()
        else:
            print("数据库中没有ip了，重新下载新的ip")
            self.get_ip_from_api()
            return self.get_random_valid_ip()



