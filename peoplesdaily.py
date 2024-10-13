import aiohttp
import asyncio
import time
from pyquery import PyQuery as pq
from urllib.parse import urljoin
import os
import re
import aiofiles  # 用于异步文件操作
from datetime import datetime, timedelta

# 并发数量 建议不要改太高
CONCURRENCY = 4
BASE_URL = 'http://paper.people.com.cn/rmrb/html/'
semaphore = asyncio.Semaphore(CONCURRENCY)


async def scrape_api(url):
    async with semaphore:
        print('scraping', url)
        retries = 2
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
                print(f"Retrying {url} in 10 seconds...")
                await asyncio.sleep(10)  # 等待10秒再重试
        log_failure(url)  # 记录失败的请求
        return None


def log_failure(url):
    with open('../smalltools/log.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"Failed to fetch: {url}\n")


async def get_paper_urls(page_url: str, layout_url: str) -> list[str]:
    html_string = await scrape_api(layout_url)
    if html_string is None:
        print('html_string is none')
        return []
    try:
        doc = pq(html_string)
        # 找到 class 为 'news-list' 的 ul 下的所有 li 元素
        items = list(doc('.news-list').children('li').items())
        # print(items)
        # 提取 li 元素中的 a 标签的 href 属性
        hrefs = [li('a').attr('href') for li in items]
        # print(hrefs)
        # 组合成完整的 URL
        urls = [urljoin(page_url, href) for href in hrefs]
        # print(f'文章{urls}')
        # print(urls)
        return urls
    except Exception as e:
        print(f"Error parsing paper URLs from {layout_url}: {e}")
        return []  # 确保在出错时返回一个空列表


async def get_layout_urls(url: str, date_string: str) -> list[str]:
    html_string = await scrape_api(url)
    if html_string is None:
        return []
    try:
        doc = pq(html_string)
        # 直接查找 class 为 'swiper-slide' 的 div 下的 a 标签
        items = list(doc('.swiper-container a').items())
        # 提取每个 a 标签的 href 属性
        hrefs = [a.attr('href') for a in items]
        # print(hrefs)
        # 组合成完整的 URL
        urls = [urljoin(BASE_URL, f'{date_string}/{href}') for href in hrefs]
        # print(urls)
        return urls
    except Exception as e:
        print(f'{url}爬取错误: {e}')
        return []  # 在出错时返回一个空列表


async def save_paper(date, title, text):
    folder_path = os.path.join("人民日报", date)  # 将文章按日期保存在相应的文件夹里
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
        html_string = re.sub(r'/\*.*?\*/', '', html_string, flags=re.DOTALL)
        doc = pq(html_string)

        title = doc('.article h1').text()
        text = doc('#ozoom').text()

        await save_paper(date, title, text)
    except Exception as e:
        print(f"Error while getting papers from {url}: {e}")


async def main():
    global session
    async with aiohttp.ClientSession() as session:  # 在这里创建session
        start_date = datetime(2023, 4, 11)
        end_date = datetime(2023, 12, 31)
        current_date = start_date

        while current_date <= end_date:
            date_string = current_date.strftime('%Y-%m/%d')
            date_save_format = current_date.strftime('%Y%m%d')
            print(f"------------------page:{current_date.strftime('%Y/%m/%d/')}------------------")
            page_url = urljoin(BASE_URL, f"{date_string}/nbs.D110000renmrb_01.htm")
            layout_urls = await get_layout_urls(page_url, date_string)
            paper_urls = []
            for layout_url in layout_urls:
                paper_urls.extend(await get_paper_urls(page_url, layout_url))

            scrape_index_tasks = [asyncio.create_task(get_papers(paper_url, date_save_format)) for paper_url in
                                  paper_urls]
            await asyncio.gather(*scrape_index_tasks)
            current_date += timedelta(days=3)
            await asyncio.sleep(2)  # 模拟延迟 建议不要删掉


if __name__ == '__main__':
    asyncio.run(main())
