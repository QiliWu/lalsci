
import hashlib
import requests
import json

def get_md5(value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    m = hashlib.md5()
    m.update(value)
    return m.hexdigest()


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


