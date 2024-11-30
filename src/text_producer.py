import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from typing_extensions import Protocol


class TextSource(Protocol):
    async def get_text(self, place: str) -> str:
        ...


class FromWebScraperSource(TextSource):
    def __init__(self, web_scraper):
        self.web_scraper = web_scraper

    async def get_text(self, url: str) -> str:
        return await self.web_scraper.scrape_page(url)


class FromNLFileSource(TextSource):
    async def get_text(self, file_path) -> str:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            return await f.read()


class WebScraper:
    @staticmethod
    async def fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    @staticmethod
    async def scrape_page(url) -> str:
        async with aiohttp.ClientSession() as session:
            page = await WebScraper.fetch(session, url)
            soup = BeautifulSoup(page, 'html.parser')

            for element in soup(['nav', 'footer', 'aside', 'header']):
                element.decompose()

            text = soup.get_text()
            text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])

            return text
