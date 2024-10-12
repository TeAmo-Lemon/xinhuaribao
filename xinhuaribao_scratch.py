import aiohttp
import asyncio
import time
from pyquery import PyQuery as pq
from urllib.parse import urljoin
import os
import re
import aiofiles  # 用于异步文件操作
from datetime import datetime, timedelta

CONCURRENCY = 3
BASE_URL = 'https://xh.xhby.net/pc/'
semaphore = asyncio.Semaphore(CONCURRENCY)

async def scrape_api(url):
    async with semaphore:
        print('scraping', url)
        retries = 3
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        print(f"Failed to fetch {url}, status code: {response.status}")
            except Exception as e:
                print(f"Error fetching {url}: {e}")
            if attempt < retries - 1:
                print(f"Retrying {url} in 20 seconds...")
                await asyncio.sleep(20)  # 等待20秒再重试
        log_failure(url)  # 记录失败的请求
        return None

def log_failure(url):
    with open('../smalltools/log.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"Failed to fetch: {url}\n")

async def get_paper_urls(page_url: str, url: str) -> list[str]:
    html_string = await scrape_api(url)
    if html_string is None:
        return []
    try:
        doc = pq(html_string)
        items = list(doc('.newslist ul').children('li').items())
        hrefs = list(li('a').attr('href') for li in items)
        urls = list(urljoin(page_url, href) for href in hrefs)
        return urls
    except Exception as e:
        print(f"Error parsing paper URLs from {url}: {e}")
        return []  # 确保在出错时返回一个空列表

async def get_layout_urls(url: str, date_string: str) -> list[str]:
    html_string = await scrape_api(url)
    if html_string is None:
        return []
    try:
        doc = pq(html_string)
        items = list(doc('.Chunkiconlist').children('p').items())
        hrefs = list(p('a').eq(0).attr('href') for p in items)
        urls = list(urljoin(BASE_URL, f'layout/{date_string}/{href}') for href in hrefs)
        return urls
    except Exception as e:
        print(f'{url}爬取错误: {e}')
        return []  # 在出错时返回一个空列表

async def save_paper(date, title, text):
    folder_path = os.path.join("xinhuaribao_news", date)  # 将文章按日期保存在相应的文件夹里
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    valid_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    if valid_title == '':
        print(f'{date}: 无标题')
        return

    file_path = os.path.join(folder_path, f"{valid_title}.txt")

    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(f"Title: {title}\nDate: {date}\n\n{text}")

async def get_papers(url, date):
    html_string = await scrape_api(url)
    if html_string is None:
        print(f"{url} is None")
        return
    try:
        doc = pq(html_string)

        title = doc('.newsdetatit h3').text()
        text = doc('.newsdetatext').text()

        await save_paper(date, title, text)
    except Exception as e:
        print(f"Error while getting papers from {url}: {e}")

async def main():
    global session
    async with aiohttp.ClientSession() as session:  # 在这里创建session
        start_date = datetime(2024, 10, 27)
        end_date = datetime(2024, 10, 11)
        current_date = start_date

        while current_date <= end_date:
            date_string = current_date.strftime('%Y%m/%d')
            date_save_format = current_date.strftime('%Y%m%d')
            print(f"------------------page:{current_date.strftime('%Y/%m/%d/')}------------------")
            page_url = urljoin(BASE_URL, f"layout/{date_string}/node_1.html")
            layout_urls = await get_layout_urls(page_url, date_string)
            paper_urls = []
            for layout_url in layout_urls:
                paper_urls.extend(await get_paper_urls(page_url, layout_url))

            scrape_index_tasks = [asyncio.create_task(get_papers(paper_url, date_save_format)) for paper_url in paper_urls]
            await asyncio.gather(*scrape_index_tasks)
            current_date += timedelta(days=1)
            await asyncio.sleep(2)  # 模拟延迟

if __name__ == '__main__':
    asyncio.run(main())
