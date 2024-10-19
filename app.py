import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import streamlit as st
import time
import pdfkit

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

# Streamlit 웹 인터페이스에서 사용할 크롤링 함수 및 PDF 생성 기능
def crawl_all_pages(main_page_url):
    base_url = main_page_url.rsplit('/', 1)[0]  # 기본 사이트 URL 추출 (상대 링크 처리용)
    current_page_url = main_page_url
    
    news_articles = []  # 뉴스 기사를 저장할 리스트
    html_content = "<html><head><meta charset='UTF-8'></head><body>"  # PDF를 위한 HTML 시작

    while current_page_url:
        # 현재 페이지에서 뉴스 링크 추출
        response = requests.get(current_page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        news_links = get_news_links(current_page_url)
        
        # 각 뉴스 페이지 크롤링
        for news_link in news_links:
            full_url = f"{base_url}{news_link}"  # 상대 경로일 경우 절대 경로로 변환
            news_data = crawl_news_page(full_url)
            
            # Streamlit으로 출력
            st.write(f"### {news_data['title']}")
            st.write(news_data['content'])
            st.write("\n" + "="*50 + "\n")
            
            # PDF용 HTML 내용 추가
            html_content += f"<h2>{news_data['title']}</h2><p>{news_data['content']}</p><hr>"

            # 뉴스 기사를 리스트에 저장
            news_articles.append(news_data)
        
        # 다음 페이지 링크 추출
        next_page_link = get_next_page_link(soup)
        if next_page_link:
            current_page_url = f"{base_url}{next_page_link}"
        else:
            # 더 이상 페이지가 없으면 종료
            current_page_url = None

    html_content += "</body></html>"  # PDF를 위한 HTML 종료
    return html_content

# PDF 저장 함수
def save_as_pdf(html_content, output_filename):
    pdfkit.from_string(html_content, output_filename)

# Streamlit 앱 실행 부분
def main():
    st.title("뉴스 크롤러 및 PDF 생성기")
    st.write("뉴스 사이트의 URL을 입력하고, '크롤링 시작' 버튼을 누르세요.")
    
    # 사용자가 입력할 수 있는 텍스트 입력 필드
    url = st.text_input('뉴스 목록 페이지 URL을 입력하세요', 'https://example.com/news')
    
    if st.button('크롤링 시작'):
        st.write(f"크롤링을 시작합니다: {url}")
        html_content = crawl_all_pages(url)
        
        # 크롤링 완료 후 PDF 생성
        pdf_filename = 'news_report.pdf'
        save_as_pdf(html_content, pdf_filename)
        st.success(f"PDF 파일이 생성되었습니다: {pdf_filename}")
        
        # Streamlit에서 PDF 다운로드 링크 제공
        with open(pdf_filename, "rb") as file:
            btn = st.download_button(
                label="PDF 다운로드",
                data=file,
                file_name=pdf_filename,
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
