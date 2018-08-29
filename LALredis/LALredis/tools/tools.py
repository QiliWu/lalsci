
import hashlib
import requests
import json

def get_md5(value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    m = hashlib.md5()
    m.update(value)
    return m.hexdigest()

def get_proxies():
    proxies_list = []
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
               }
    url = 'http://piping.mogumiao.com/proxy/api/get_ip_al?appKey=7e5d4716e4c445adadd33397bb47aa21&count=5&expiryDate=0&format=1'

    r = requests.get(url=url,
                     headers = headers)
    data = json.loads(r.text)

    for p in data['msg']:
        port = p['port']
        ip = p['ip']
        proxy_ip = ip + ':' + port
        proxies_list.append({'http':'http://'+proxy_ip})
        proxies_list.append({'https':'https://' + proxy_ip})
    return proxies_list


def get_suggests(index, info_tuple, es):
    # 根据字符串生成搜索建议数组
    used_words = set()
    suggests = []
    for text, weight in info_tuple:
        if text:
            # 调用es的analyze接口分析字符串
            words = es.indices.analyze(
                index=index, params={
                    'filter': ['lowercase']}, body=text)
            analyzed_words = set(
                [r['token'] for r in words['tokens'] if len(r['token']) > 1])
            new_words = analyzed_words - used_words
        else:
            new_words = set()

        if new_words:
            suggests.append({"input": list(new_words), "weight": weight})

    return suggests

