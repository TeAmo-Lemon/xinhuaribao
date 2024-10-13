import requests
import bs4
import os
import datetime
import time


def fetchUrl(url, retries=3):
    '''
    功能：访问 url 的网页，获取网页内容并返回，失败时重试
    参数：目标网页的 url，重试次数
    返回：目标网页的 html 内容
    '''
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    }
    for i in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if i < retries - 1:
                print("Retrying...")
                time.sleep(10)  # 请求失败，延时10秒再重试
            else:
                print(f"Failed after {retries} attempts.")
                return None


def getPageList(year, month, day):
    '''
    功能：获取当天报纸的各版面的链接列表
    参数：年，月，日
    '''
    url = f'http://paper.people.com.cn/rmrb/html/{year}-{month}/{day}/nbs.D110000renmrb_01.htm'
    html = fetchUrl(url)
    if not html:
        return []

    bsobj = bs4.BeautifulSoup(html, 'html.parser')
    temp = bsobj.find('div', attrs={'id': 'pageList'})
    if temp:
        pageList = temp.ul.find_all('div', attrs={'class': 'right_title-name'})
    else:
        pageList = bsobj.find('div', attrs={'class': 'swiper-container'}).find_all('div',
                                                                                   attrs={'class': 'swiper-slide'})

    linkList = []
    for page in pageList:
        link = page.a["href"]
        url = f'http://paper.people.com.cn/rmrb/html/{year}-{month}/{day}/{link}'
        linkList.append(url)

    return linkList


def getTitleList(year, month, day, pageUrl):
    '''
    功能：获取报纸某一版面的文章链接列表
    参数：年，月，日，该版面的链接
    '''
    html = fetchUrl(pageUrl)
    if not html:
        return []

    bsobj = bs4.BeautifulSoup(html, 'html.parser')
    temp = bsobj.find('div', attrs={'id': 'titleList'})
    if temp:
        titleList = temp.ul.find_all('li')
    else:
        titleList = bsobj.find('ul', attrs={'class': 'news-list'}).find_all('li')

    linkList = []
    for title in titleList:
        tempList = title.find_all('a')
        for temp in tempList:
            link = temp["href"]
            if 'nw.D110000renmrb' in link:
                url = f'http://paper.people.com.cn/rmrb/html/{year}-{month}/{day}/{link}'
                linkList.append(url)

    return linkList


def getContent(html):
    '''
    功能：解析 HTML 网页，获取新闻的文章内容
    参数：html 网页内容
    '''
    bsobj = bs4.BeautifulSoup(html, 'html.parser')

    # 获取文章 标题
    title = f'{bsobj.h3.text}\n{bsobj.h1.text}\n{bsobj.h2.text}\n'

    # 获取文章 内容
    pList = bsobj.find('div', attrs={'id': 'ozoom'}).find_all('p')
    content = '\n'.join([p.text for p in pList])

    # 返回结果 标题+内容
    return title + content


def saveFile(content, path, filename):
    '''
    功能：将文章内容 content 保存到本地文件中
    参数：要保存的内容，路径，文件名
    '''
    # 如果没有该文件夹，则自动生成
    if not os.path.exists(path):
        os.makedirs(path)

    # 保存文件
    with open(os.path.join(path, filename), 'w', encoding='utf-8') as f:
        f.write(content)


def download_rmrb(year, month, day, destdir=''):
    '''
    功能：爬取《人民日报》网站 某年 某月 某日 的新闻内容，并保存在 指定目录下
    参数：年，月，日，文件保存的根目录
    '''
    pageList = getPageList(year, month, day)
    for page in pageList:
        titleList = getTitleList(year, month, day, page)
        for url in titleList:
            # 获取新闻文章内容
            html = fetchUrl(url)
            if not html:
                continue
            content = getContent(html)

            # 生成保存的文件路径及文件名
            temp = url.split('_')[2].split('.')[0].split('-')
            pageNo = temp[1]
            titleNo = temp[0] if int(temp[0]) >= 10 else '0' + temp[0]
            path = os.path.join(destdir, f'{year}{month}{day}')
            fileName = f'{year}{month}{day}_{pageNo}_{titleNo}.txt'

            # 保存文件
            saveFile(content, path, fileName)


def gen_dates(b_date, days):
    day = datetime.timedelta(days=1)
    for i in range(days):
        yield b_date + day * i


def get_date_list(beginDate, endDate):
    """
    获取日期列表
    :param start: 开始日期
    :param end: 结束日期
    :return: 开始日期和结束日期之间的日期列表
    """
    start = datetime.datetime.strptime(beginDate, "%Y%m%d")
    end = datetime.datetime.strptime(endDate, "%Y%m%d")

    data = []
    for d in gen_dates(start, (end - start).days + 1):
        data.append(d)

    return data

if __name__ == '__main__':
    '''
    主函数：程序入口
    '''
    # 输入起止日期，爬取之间的新闻
    beginDate = input('请输入开始日期 (格式: YYYYMMDD): ')
    endDate = input('请输入结束日期 (格式: YYYYMMDD): ')
    data = get_date_list(beginDate, endDate)

    for d in data:
        year = str(d.year)
        month = str(d.month).zfill(2)
        day = str(d.day).zfill(2)
        download_rmrb(year, month, day)
        print(f"爬取完成：{year}{month}{day}")
        # time.sleep(2)
