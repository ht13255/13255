import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Selenium을 사용해 동적 페이지 처리 (필요시 사용)
def fetch_dynamic_page(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 브라우저 창을 띄우지 않음
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.get(url)
    time.sleep(3)  # 페이지 로딩 대기

    page_source = driver.page_source
    driver.quit()
    
    return page_source

# 정적 페이지에서 뉴스 링크 목록 크롤링
def get_news_links(page_url):
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 페이지에서 뉴스 링크 추출 (예: 'a' 태그에 뉴스 링크가 있을 경우)
    news_links = []
    for a_tag in soup.find_all('a', href=True):
        if 'news' in a_tag['href']:  # 특정 패턴이 포함된 링크만 추출
            news_links.append(a_tag['href'])
    
    return news_links

# 페이지네이션에서 다음 페이지 링크 추출
def get_next_page_link(soup):
    next_page_tag = soup.find('a', text='다음 페이지')  # 페이지네이션의 '다음 페이지' 텍스트 찾기
    if next_page_tag and next_page_tag['href']:
        return next_page_tag['href']
    return None

# 뉴스 페이지 크롤링
def crawl_news_page(news_url):
    page_source = fetch_dynamic_page(news_url)  # 동적 페이지일 경우 사용
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # 뉴스 제목과 내용 추출 (예: 'h1'과 'p' 태그 사용)
    title = soup.find('h1').get_text(strip=True)
    content = "\n".join([p.get_text(strip=True) for p in soup.find_all('p')])
    
    return {'title': title, 'content': content}

# 전체 크롤링 프로세스 (여러 페이지 크롤링)
def main():
    base_url = 'https://example.com'  # 기본 사이트 URL
    main_page_url = f'{base_url}/news'  # 뉴스 목록 첫 페이지 URL
    
    current_page_url = main_page_url
    
    while current_page_url:
        # 현재 페이지에서 뉴스 링크 추출
        response = requests.get(current_page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        news_links = get_news_links(current_page_url)
        
        # 각 뉴스 페이지 크롤링
        for news_link in news_links:
            full_url = f"{base_url}{news_link}"  # 상대 경로일 경우 절대 경로로 변환
            news_data = crawl_news_page(full_url)
            print(news_data['title'])
            print(news_data['content'])
            print("\n" + "="*50 + "\n")
        
        # 다음 페이지 링크 추출
        next_page_link = get_next_page_link(soup)
        if next_page_link:
            current_page_url = f"{base_url}{next_page_link}"
        else:
            # 더 이상 페이지가 없으면 종료
            current_page_url = None

if __name__ == "__main__":
    main()
