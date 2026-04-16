import httpx
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse
from fake_useragent import UserAgent
import time
from typing import Any

Article = dict[str, Any]
Comment = dict[str, str]
ArticleDetail = dict[str, Any]


class _RateLimitedClientProxy:
    def __init__(
        self, client: httpx.Client, cooldown: int = 2, random_ua: bool = True
    ) -> None:
        self._client = client
        self.cooldown = cooldown
        self.last_request_time: float = 0.0
        self.ua = UserAgent()
        self.rotate_user_agent = lambda: self.ua.random
        self._random_ua = random_ua
        self.USER_AGENT = self.rotate_user_agent()
        self._client.headers.update({"User-Agent": self.USER_AGENT})

    def _cooldown(self) -> bool:
        if self.cooldown == 0:
            return False
        if self.last_request_time == 0:
            return False
        elapsed = time.time() - self.last_request_time
        if elapsed < self.cooldown:
            time.sleep(self.cooldown - elapsed)
            return True
        return False

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if callable(attr):

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if self._random_ua:
                    self.USER_AGENT = self.rotate_user_agent()
                    self._client.headers.update({"User-Agent": self.USER_AGENT})
                self._cooldown()
                self.last_request_time = time.time()
                return attr(*args, **kwargs)

            return wrapper
        return attr


class HackerNews:
    def __init__(self, cooldown: int = 2, random_ua: bool = True) -> None:
        self.BASE_URL = urlparse("https://news.ycombinator.com")
        self.cooldown = cooldown
        self.random_ua = random_ua
        self._client = httpx.Client(timeout=30)
        self.client = _RateLimitedClientProxy(
            self._client, cooldown=cooldown, random_ua=random_ua
        )

    def __repr__(self) -> str:
        return f"HackerNews(cooldown={self.cooldown}, random_ua={self.random_ua})"

    def __str__(self) -> str:
        return f"HackerNews scraper for {self.BASE_URL.geturl()}"

    def __enter__(self) -> "HackerNews":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def parse_homepage(self, page: int = 1) -> list[Article]:
        url = self.BASE_URL._replace(path="news", query=f"p={page}").geturl()
        soup = BeautifulSoup(self.client.get(url).text, "lxml")
        trs = soup.find_all("tr", class_="athing submission")
        articles: list[Article] = []
        for tr in trs:
            article_id = tr.get("id")
            article_title_td = tr.find("span", class_="titleline")
            if article_title_td is None:
                continue
            article_title = article_title_td.text
            link_elem = article_title_td.find("a")
            article_href_link = link_elem.get("href") if link_elem else None
            article_link = self.BASE_URL._replace(
                path="item", query=f"id={article_id}"
            ).geturl()
            articles.append(
                {
                    "article_id": article_id,
                    "article_title": article_title,
                    "article_href_link": article_href_link,
                    "article_link": article_link,
                }
            )

        return articles

    def _parse_comment(self, data: Tag) -> Comment:
        user_elem = data.find("a", class_="hnuser")
        user = user_elem.text if user_elem else ""
        comment_elem = data.find("div", class_="commtext")
        comment = comment_elem.text if comment_elem else ""
        age_elem = data.find("span", class_="age")
        age = age_elem.get("title") if age_elem else ""

        return {"user": user, "comment": comment, "age": age}

    def parse_articles(self, id: int) -> ArticleDetail:
        url = self.BASE_URL._replace(path="item", query=f"id={id}").geturl()
        try:
            response = self.client.get(url)
            soup = BeautifulSoup(response.text, "lxml")
        except httpx.HTTPError:
            raise

        titleline = soup.find("span", class_="titleline")
        title = titleline.text if titleline else ""
        link = ""
        if titleline:
            link_elem = titleline.find("a")
            if link_elem:
                link = link_elem.get("href") or ""

        post_body_elem = soup.find("div", class_="toptext")
        post_body = post_body_elem.text if post_body_elem else ""

        comment_tree = soup.find("table", class_="comment-tree")
        if comment_tree is None:
            return {
                "title": title,
                "link": link,
                "post_body": post_body,
                "comments": [],
            }
        comment_rows = comment_tree.find_all("tr", class_="athing comtr")
        comments_data: list[Comment] = []

        for comment in comment_rows:
            comment_data = self._parse_comment(comment)
            comments_data.append(comment_data)

        return {
            "title": title,
            "link": link,
            "post_body": post_body,
            "comments": comments_data,
        }
