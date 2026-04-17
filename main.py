from fastapi import FastAPI
from hackernews import HackerNews

app = FastAPI()
hn = HackerNews()

@app.get('/')
def hello_world():
    return {"message": "Hello World"}

@app.get('/hn/homepage')
def get_homepage(page: int = 1):
    data = hn.parse_homepage(page)
    return {"data": data}

@app.get('/hn/article/{id}')
def get_article(id: int):
    data = hn.parse_articles(id)
    return {"data": data}
