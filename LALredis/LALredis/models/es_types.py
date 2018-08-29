
from elasticsearch_dsl import DocType, Date, Integer, Nested, Boolean, \
    analyzer, Completion, Keyword, Text
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import CustomAnalyzer as _CustomAnalyser

connections.create_connection(hosts=["12.34.56.78:9200"])

class ESLAL(DocType):
    suggest = Completion()
    title = Text()
    url = Keyword()
    journal = Keyword()
    doi = Keyword()
    id = Keyword()
    abs_img_url = Keyword()
    abstract = Text()
    keywords = Text(fields={'keywords': Keyword()})
    authors = Text(fields={'keywords': Keyword()})
    year = Integer()
    citing_num = Integer()
    company = Keyword()

    class Meta:
        index = 'lal'
        doc_type = 'article'

if __name__ == '__main__':
    #在ES数据库中创建对应的index
    ESLAL.init()
