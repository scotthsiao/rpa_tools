from typing import List
import os.path
import time
import re

import cloudscraper
from importlib_metadata import files
from requests_html import HTML
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from socks import method
from webdriver_manager.chrome import ChromeDriverManager
from lxml import etree

test_url=('https://missav123.com/cn/spsb-014')
ob_vaults_path = r"C:\Users\Scott\OB\卡片庫\AV Collections"


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    替換檔名中的特殊字元，適合於 Windows 系統存檔。

    :param filename: 原始檔名
    :param replacement: 用於替換非法字元的字元，預設為下劃線 '_'
    :return: 清理後的檔名
    """
    # Windows 不允許的特殊符號
    invalid_chars = r'[\\/:*?"<>|]'

    # 將特殊字元替換為指定的替代字元
    sanitized = re.sub(invalid_chars, replacement, filename)

    # 確保結果長度不超過 255 個字元（適合單一檔名）
    return sanitized[:255]


class AvTitleInfo:
    def __init__(self):
        self.title: str = None
        self.thumbnail: str = None
        self.artists: str = None
        self.serial: str = None
        self.company: str = None
        self.director: str = None
        self.release_date: str = None
        self.source_link: str = None
        self.tags: List[str] = []

    def __str__(self):
        uncensored = True if 'uncensored-leak' in self.source_link else False
        if self.artists:
            artist_list = self.artists.split(', ')
            artist_serialized = '\n  - '.join([f'"[[{artist}]]"' for artist in artist_list])
        else:
            artist_serialized = None
        tags_serialized = '\n  - '.join(self.tags)

        serialized_data = \
f"""---
番號: {self.serial}
女優:
  - {artist_serialized}
tags:
  - {tags_serialized}
無碼: {str(uncensored).lower()}
發行商: {self.company}
導演: {self.director}
發行日: {self.release_date}
Thumbnail: {self.thumbnail}
SourceLink: {self.source_link}
Stars: 
---"""
        return serialized_data

    def write_to_file(self, filepath:str) -> bool:
        print(filepath)
        with open(filepath, 'w+', encoding='utf-8') as fd:
            fd.write(self.__str__())

def request_page_source(url:str) -> str:
    scraper = cloudscraper.create_scraper(delay=5, browser='chrome')
    response = scraper.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        raise ValueError(f"Request failed with status code: {response.status_code}")
    # html = HTML(html=response.text)
    return response.text


def get_page_source(url: str, method:str = 'selenium') -> str:
    page_source = None
    if method == 'selenium':
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')

        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")
        dr = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        dr.get(url)
        page_source = dr.page_source
    elif method == 'requests':
         page_source = request_page_source(url)
    return page_source

def parse_njav_info(raw: str) ->AvTitleInfo:
    info = AvTitleInfo()
    html  = HTML(html=raw)

    info.title = html.find('h1', first=True).text
    data_poster_div = html.find('div[data-poster]', first=True)
    if data_poster_div:
        info.thumbnail = data_poster_div.attrs.get('data-poster')


    content_div = html.find('div.content', first=True)
    if content_div:
        # Extract and print the text or HTML from the 'content' div
        # print(content_div.text)  # or use content_div.html for raw HTML
        info.release_date = html.find('span', containing="发布日期:", first=True).element.getnext().text
        info.serial =  html.find('span', containing="代码:", first=True).element.getnext().text
        company_ele = html.find('span', containing="制作者:", first=True).element.getnext()
        info.company = company_ele.find('a').text
        actress_ele = html.find('span', containing="演员:", first=True).element.getnext()
        actress = actress_ele.text_content().strip().split('\n')
        info.artists = ', '.join(actress)
    else:
        print("Content div not found.")
    return info


def parse_missav_info(raw: str) -> AvTitleInfo:
    info = AvTitleInfo()

    parser = etree.HTMLParser()
    tree = etree.fromstring(raw, parser)
    detail_node = None
    for tag in tree.iter():
        if tag.tag == 'div' and 'detail' in tag.attrib.get('x-show', ''):
            detail_node = tag
            break
    if detail_node is None:
        raise ValueError('No detail block is found!')

    info.title = tree.find('.//h1').text
    info.release_date = tree.find('.//time').text
    info.thumbnail = tree.find(".//div[@class='plyr__poster']").get("style")[23:-3]

    for tag in detail_node.iter():
        if tag.tag == 'span' and tag.text is not None:
            if any(keyword in tag.text for keyword in ["番號", "番号"]):
                info.serial = tag.getparent().findall(".//span")[1].text
                info.serial = info.serial.replace("-UNCENSORED-LEAK", "")
            elif any(keyword in tag.text for keyword in ["女優", "女优"]):
                actress = [a.text for a in tag.getparent().findall(".//a")]
                info.artists = ', '.join(actress)
            elif any(keyword in tag.text for keyword in ["發行商", "发行商"]):
                info.company = tag.getparent().find(".//a").text
            elif any(keyword in tag.text for keyword in ["導演", "导演"]):
                info.director = tag.getparent().find(".//a").text
    return info


def lookup_javlib(serial: str) -> str:
    # url =  "https://www.javlibrary.com/tw/vl_searchbyid.php?keyword=" + serial
    url = 'https://www.javlibrary.com/tw/'

    def get_cookies_and_user_agent(url):
        scraper = cloudscraper.create_scraper(delay=5, browser='chrome')
        retries = 0
        max_retries = 3
        delay = 5

        while retries < max_retries:
            response = scraper.get(url)
            redirect_url = scraper.get_redirect_target(response)

            if response.status_code == 200:
                return response.content
            elif response.status_code == 403:
                print("Received 403 response, waiting before retrying...")
                time.sleep(delay)

                retries += 1
            else:
                response.raise_for_status()

        if  retries == max_retries:
            print(f"Failed to retrieve cookies and user agent after {max_retries} retries.")
            raise TimeoutException("Failed to retrieve cookies and user agent after multiple retries.")



        # response = scraper.get(url)
        # if response.status_code != 200:
        #     raise ValueError(f"Request failed with status code: {response.status_code}")

        cookies = response.cookies.get_dict()
        user_agent = scraper.headers['User-Agent']
        return cookies, user_agent

    cookies, user_agent = get_cookies_and_user_agent(url)

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')

    options.add_argument(f"user-agent={user_agent}")

    # options.add_argument(
    #     "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")
    dr = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    dr.get(url)

    # Add cookies to Selenium
    for name, value in cookies.items():
        dr.add_cookie({'name': name, 'value': value})

    # Refresh the page to apply cookies
    # dr.refresh()

    # if 'https://www.javlibrary.com/tw/?v' not in dr.current_url:
    #     current_url = dr.current_url
    #     try:
    #         WebDriverWait(dr, 10).until(lambda d: d.current_url != current_url)
    #     except TimeoutException as e:
    #         print(f"Timeout waiting for URL change: {e} - {dr.current_url} - {current_url}")

    # print(f"Current URL: {dr.current_url}")

    WebDriverWait(dr, 10).until(
        EC.presence_of_element_located((By.ID, "idsearchbox"))
    )

    input = dr.find_element(By.ID, "idsearchbox")
    input.send_keys(serial)

    # idsearchbutton
    submit_button = dr.find_element(By.ID, "idsearchbutton")
    submit_button.click()

    # Wait for the <div id="video_info"> element to be present
    WebDriverWait(dr, 10).until(
        EC.presence_of_element_located((By.ID, "video_info"))
    )

    # Once the element is present, you can proceed with further actions
    video_info = dr.find_element(By.ID, "video_info").text
    print(f"Video Info: {video_info}")


if __name__ == "__main__":
    # use parser to get url option from CLI

    time_start = time.time()
    if test_url.startswith(('https://missav.com', 'https://missav123.com', 'https://missav.ws')):
        raw_html = get_page_source(test_url, 'selenium')
        print(f"{len(raw_html)=} delta {time.time() - time_start}")
        info = parse_missav_info(raw_html)
    elif test_url.startswith('https://njav.tv'):
        raw_html = get_page_source(test_url, 'requests')
        print(f"{len(raw_html)=} delta {time.time() - time_start}")
        info = parse_njav_info( raw_html)
    info.source_link = test_url

    # lookup_javlib(info.serial)

    # replace  '/' with '-' in title
    # filepath = info.title.replace('/', '-')
    filepath = sanitize_filename(info.title[:100])
    info.write_to_file(os.path.join(ob_vaults_path, filepath + '.md'))






