from typing import List
import os.path
import time

import cloudscraper
from requests_html import HTML
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from socks import method
from webdriver_manager.chrome import ChromeDriverManager
from lxml import etree

test_url=('https://missav.com/fsdss-952-uncensored-leak')
ob_vaults_path = r"C:\Users\Scott\OB\卡片庫\AV Collections"

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
            if "番號" in tag.text:
                info.serial = tag.getparent().findall(".//span")[1].text
                info.serial = info.serial.replace("-UNCENSORED-LEAK", "")
            elif "女優" in tag.text:
                actress = [a.text for a in tag.getparent().findall(".//a")]
                info.artists = ', '.join(actress)
            elif "發行商" in tag.text:
                info.company = tag.getparent().find(".//a").text
            elif "導演" in tag.text:
                info.director = tag.getparent().find(".//a").text
    return info


if __name__ == "__main__":
    # use parser to get url option from CLI

    time_start = time.time()
    if test_url.startswith('https://missav.com'):
        raw_html = get_page_source(test_url, 'selenium')
        print(f"{len(raw_html)=} delta {time.time() - time_start}")
        info = parse_missav_info(raw_html)
    elif test_url.startswith('https://njav.tv'):
        raw_html = get_page_source(test_url, 'requests')
        print(f"{len(raw_html)=} delta {time.time() - time_start}")
        info = parse_njav_info( raw_html)
    info.source_link = test_url

    # replace  '/' with '-' in title
    filepath = info.title.replace('/', '-')
    info.write_to_file(os.path.join(ob_vaults_path, filepath + '.md'))






