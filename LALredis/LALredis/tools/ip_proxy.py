# -*- coding: utf-8 -*-
# python36
__author__ = 'wuqili'

#自动登录蘑菇ip, 然后获取代理ip的连接
# 1. 验证码识别
# 2.登录蘑菇ip,
# 3. 购买ip
import time
import requests
from io import BytesIO
from PIL import Image
import pytesseract
import json
import re
import redis
from random import choice
from scrapy.selector import Selector


class GetIP():
    def __init__(self):
        self.r = redis.StrictRedis(host='12.34.56.78', port=6379, db=1, password='123456')
        # self.r = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        self.session = requests.Session()

    def login(self):
        #将验证码图片破解，获取验证码

        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'}
        captcha_url = 'http://www.moguproxy.com/proxy/validateCode/createCode?time={} '.format(
            int(time.time() * 1000))
        response = self.session.get(captcha_url) #请求验证码图片链接
        im = Image.open(BytesIO(response.content))   #直接读取bytes数据，生成图片对象
        width, height = im.size
        #获取图片中的颜色，返回列表[(counts, color)...]
        color_info = im.getcolors(width*height)
        sort_color = sorted(color_info, key=lambda x: x[0], reverse=True)
        #将背景全部改为白色, 提取出字，每张图片一个字
        char_dict = {}
        for i in range(1, 6):
            start_x = 0
            im2 = Image.new('RGB', im.size, (255, 255, 255))
            for x in range(im.size[0]):
                for y in range(im.size[1]):
                    if im.getpixel((x, y)) == sort_color[i][1]:
                        im2.putpixel((x, y), (0, 0, 0))
                        if not start_x:
                            start_x = x
                    else:
                        im2.putpixel((x, y), (255, 255, 255))
            char = pytesseract.image_to_string(im2, lang='normal',config='--psm 10')
            char_dict[start_x] = char
        code = ''.join([item[1] for item in sorted(char_dict.items(), key=lambda i:i[0])])
        login_url = 'http://www.moguproxy.com/proxy/user/login?mobile=??????????&password=???????????&code={}'.format(code)
        self.session.get(login_url)

    def crawl_api(self):
        #抓取ip并存入redis数据库
        api_url = 'http://piping.mogumiao.com/proxy/api/get_ip_al?appKey=???????????????????&count=15&expiryDate=0&format=1&newLine=2'
        response = self.session.get(api_url)
        while 'port' not in response.text:
            self.login()
            response = self.session.get(api_url)
        data = json.loads(response.text,encoding='utf8')
        index = 0
        for proxy in data['msg']:
            port = proxy['port']
            ip = proxy['ip']
            http_proxy_ip = 'http://' + ip + ':' + port
            self.r.hset('proxies', index, http_proxy_ip)
            index += 1
        print('成功下载新的ip')

    def check_ip(self, proxy_dict):
        #验证ip是否有效
        http_url = 'http://www.123cha.com/'
        if not proxy_dict:
            return False
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'}
            response = requests.get(
                http_url, headers=headers, proxies=proxy_dict, timeout=2)
            response.raise_for_status()
            code = response.status_code
            if code >= 200 and code < 300:
                response = Selector(response)
                text = response.css('div.location').extract()[0]
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
        # 从数据库提取一个有效的ip
        keys = self.r.hkeys('proxies')
        if keys:
            i = choice(keys)
            proxy = self.r.hget('proxies', i).decode('utf8')
            proxy_dict = {'http': proxy}
            if self.check_ip(proxy_dict):
                return proxy
            else:
                self.r.hdel('proxies', i)
                return self.get_random_valid_ip()
        else:
            print("数据库中没有ip了，重新下载新的ip")
            self.crawl_api()
            return self.get_random_valid_ip()




