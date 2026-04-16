import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class HackerNews:
    def __init__(self):
        self.BASE_URL=urlparse("https://news.ycombinator.com")
        try:
            self.homepage_articles = self._parse_homepage()
        except Exception as e:
            print("Error parsing homepage articles:", e)
            raise e

    def _parse_homepage(self, page:int=1) -> dict:
        url = self.BASE_URL._replace(path="news", query=f"p={page}").geturl()
        soup = BeautifulSoup(httpx.get(url), "lxml")
        trs = soup.find_all("tr", class_="athing submission")
        articles = []
        for tr in trs:
            article_id = tr.get("id")
            article_title_td = tr.find("span", class_="titleline")
            article_title = article_title_td.text
            article_href_link = article_title_td.find("a").get("href")
            article_link = self.BASE_URL._replace(path="item", query=f"id={article_id}").geturl()
            articles.append({
                "article_id": article_id,
                "article_title": article_title,
                "article_href_link": article_href_link,
                "article_link": article_link
            })

        return articles

    def _parse_commnent(self, data):
        user = data.find("a", class_="hnuser").text
        comment = data.find("div", class_="commtext").text
        age = data.find("span", class_="age").get("title")

        return {
            "user": user,
            "comment": comment,
            "age": age
        }

    def parse_articles(self, id:int):
        url = self.BASE_URL._replace(path="item", query=f"id={id}").geturl()
        print(f"Parsing article with id {id} from url: {url}")
        try:
            response = httpx.get(url)
            soup = BeautifulSoup(response.text, "lxml")
        except httpx.HTTPError as e:
            raise e

        titleline = soup.find("span", class_="titleline")
        title = titleline.text
        link = titleline.find("a").get("href")

        try:
            post_body = soup.find("div", class_="toptext").text
        except Exception as e:
            post_body = ""

        comments = soup.find('table', class_="comment-tree").find_all("tr", class_="athing comtr")
        comments_data = []
        for comment in comments:
            comment_data = self._parse_commnent(comment)
            comments_data.append(comment_data)

        return {
            "title": title,
            "link": link,
            "post_body": post_body,
            "comments": comments_data
        }
