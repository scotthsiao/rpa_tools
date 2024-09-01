import os.path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from lxml import etree

test_url='https://missav.com/abp-611-uncensored-leak'
ob_vaults_path = r"C:\Users\Scott\OB\卡片庫\AV Collections"

class MissavInfo:
    def __init__(self):
        self.title: str = None
        self.thumbnail: str = None
        self.artists: str = None
        self.serial: str = None
        self.company: str = None
        self.director: str = None
        self.release_date: str = None
        self.source_link: str = None
        self.tags = []

    def __str__(self):
        uncensored = True if 'uncensored-leak' in self.source_link else False
        artist_list = self.artists.split(', ')  # Assuming artists are separated by commas
        artist_serialized = '\n  - '.join([f'[[{artist}]]' for artist in artist_list])
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

    def write_to_file(self, filepath) -> bool:
        print(self.__str__())
        with open(filepath, 'w+', encoding='utf-8') as fd:
            fd.write(self.__str__())

def get_page_source(url: str) -> str:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")
    # dr = webdriver.Chrome(options=options)
    dr = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    dr.get(url)
    return dr.page_source


def parse_missav_info(raw: str) -> MissavInfo:
    info = MissavInfo()

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
            elif "女優" in tag.text:
                info.artists = tag.getparent().find(".//a").text
            elif "發行商" in tag.text:
                info.company = tag.getparent().find(".//a").text
            elif "導演" in tag.text:
                info.director = tag.getparent().find(".//a").text
    return info


if __name__ == "__main__":
    raw_html = get_page_source(test_url)
    info = parse_missav_info(raw_html)
    info.source_link = test_url
    info.write_to_file(os.path.join(ob_vaults_path, info.title + '.md'))




# posters = tree.findall(".//div[@class='plyr__poster']")
# for poster in posters:
#     print(poster.get("style"))
#
# details = tree.findall(".//div[@x-show]")
# print(details)


# $x(".//H1")
# $x('//time')
# $x("//div[contains(@x-show,'detail')]")
# $x("//span[contains(text(),'番號')]/../span[2]/text()")
# $x("//span[contains(text(),'女優')]/../a/text()")
# $x("//span[contains(text(),'發行商')]/../a/text()")
# $x("//span[contains(text(),'導演')]/../a/text()")


# # title
# print(tree.find('.//h1').text)
# print(tree.find('.//time').text)
# # print(tree.find(".//div[contains(@x-show,'detail')]"))

# if detail_node is not None:
#     for tag in tree.iter():
#         if tag.tag == 'span' and tag.text is not None:
#             if "番號" in tag.text:
#                 el = tag
#                 print(tag.getparent().findall(".//span")[1].text)
#             if "女優" in tag.text:
#                 print(tag.getparent().find(".//a").text)
#             if "發行商" in tag.text:
#                 print(tag.getparent().find(".//a").text)
#             if "導演" in tag.text:
#                 print(tag.getparent().find(".//a").text)

# poster = tree.find(".//div[@class='plyr__poster']")
# print(poster.get("style")[23:-3])
