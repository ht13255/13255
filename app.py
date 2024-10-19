import time
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Selenium으로 페이지 로드 및 동적 콘텐츠 처리
def load_dynamic_page(url):
    options = Options()
    options.add_argument("--headless")  # GUI 없이 실행
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # ChromeDriver 설치 및 사용
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)  # JavaScript가 로드될 시간을 주기 위해 대기 (필요시 조정 가능)

    page_source = driver.page_source
    driver.quit()  # 크롤링 후 드라이버 종료
    return page_source

# 페이지에서 텍스트를 추출하는 함수 (Selenium으로 동적 로드 처리)
def extract_text_from_dynamic_url(url):
    try:
        # 동적 페이지 로딩
        page_source = load_dynamic_page(url)
        soup = BeautifulSoup(page_source, 'html.parser')

        # 기본적으로 <p> 태그의 텍스트를 모두 가져온다.
        paragraphs = soup.find_all('p')
        if paragraphs:
            return "\n\n".join([p.get_text() for p in paragraphs])

        # <div>, <span> 등의 태그에서도 텍스트를 추출
        divs = soup.find_all('div')
        spans = soup.find_all('span')
        if divs or spans:
            return "\n\n".join([d.get_text() for d in divs] + [s.get_text() for s in spans])

    except Exception as e:
        st.error(f"Error in extracting text from {url}: {str(e)}")
        return ""

# 광고 링크 및 외부 링크, 비정상적인 링크 필터링
def is_valid_link(href, base_url):
    # 광고 링크 패턴 정의 (여기에 패턴을 추가할 수 있음)
    ad_keywords = ['utm_source', 'affiliate', 'ad', 'advert', 'click']

    # 광고 링크 패턴에 맞는지 확인
    if any(keyword in href for keyword in ad_keywords):
        return False

    # 특정 스킴을 가진 링크 필터링 (mailto:, tel:, javascript:)
    invalid_schemes = ['mailto:', 'tel:', 'javascript:']
    if any(href.startswith(scheme) for scheme in invalid_schemes):
        return False

    # 외부 사이트 링크인지 확인
    parsed_href = urlparse(href)
    base_domain = urlparse(base_url).netloc

    if parsed_href.netloc and parsed_href.netloc != base_domain:
        return False

    return True

# 내부 링크를 탐색하고 모든 페이지를 제한 없이 순차적으로 크롤링
def crawl_and_collect_all_pages(base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 방문한 페이지를 추적
    visited = set()
    # 크롤링할 페이지 목록
    to_visit = [base_url]
    all_text = ""

    while to_visit:
        current_url = to_visit.pop(0)  # 큐에서 링크를 가져와 크롤링
        if current_url in visited:
            continue  # 이미 방문한 페이지는 재방문하지 않음

        st.write(f"Visiting {current_url}...")
        time.sleep(2)  # 서버에 부담을 주지 않도록 대기 시간 추가

        # 동적 페이지에서 텍스트 추출
        text = extract_text_from_dynamic_url(current_url)
        if not text:
            continue  # 크롤링에 실패한 경우 데이터를 포함하지 않음

        # 크롤링 성공 시 텍스트 추가
        all_text += text + "\n\n" + ("-" * 50) + "\n\n"

        try:
            soup = BeautifulSoup(text, 'html.parser')

            # 내부 링크 추출 및 처리
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                full_url = urljoin(base_url, href)

                # 광고 및 외부 링크 필터링 후 내부 링크만 크롤링
                if full_url not in visited and full_url not in to_visit and is_valid_link(full_url, base_url):
                    to_visit.append(full_url)

            # 방문한 페이지로 추가
            visited.add(current_url)

        except Exception as e:
            st.error(f"Error occurred while crawling {current_url}: {str(e)}")
            continue

    return all_text

# PDF로 텍스트 저장 함수 (유니코드 지원)
def save_text_to_pdf(text, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 유니코드 지원 폰트 추가
    font_path = os.path.join(os.getcwd(), 'fonts', 'NotoSans-Regular.ttf')
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font('NotoSans', size=12)

    # 텍스트를 PDF로 작성
    pdf.multi_cell(0, 10, text)

    # PDF 저장
    pdf.output(pdf_filename)

# 주 함수: 사이트 내 모든 링크를 순차적으로 크롤링하고, 모든 데이터를 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename):
    st.write(f"Starting site crawl from {base_url}...")

    # 모든 페이지 방문 및 크롤링
    all_text = crawl_and_collect_all_pages(base_url)

    # 텍스트를 PDF로 저장
    if all_text:
        save_text_to_pdf(all_text, pdf_filename)

        # PDF 다운로드 링크 제공
        with open(pdf_filename, "rb") as pdf_file:
            pdf_data = pdf_file.read()
            st.download_button(
                label="Download PDF",
                data=pdf_data,
                file_name=pdf_filename,
                mime="application/pdf"
            )
    else:
        st.error("No content to save.")

# Streamlit UI
def main():
    st.title("Advanced Website Crawler with Dynamic Content Support")

    # URL 입력
    url_input = st.text_input("Enter the base URL:")

    if st.button("Create PDF"):
        if url_input:
            pdf_filename = "site_output.pdf"
            create_pdf_from_site(url_input, pdf_filename)
        else:
            st.error("Please enter a valid URL")

if __name__ == "__main__":
    main()
