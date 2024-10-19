import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 세션을 사용하여 크롤링하는 함수
def extract_text_from_url(url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 첫 번째 시도: <p> 태그에서 텍스트 추출
        response = session.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()  # 404, 403 등의 HTTP 오류가 발생할 경우 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        if paragraphs:
            return "\n\n".join([p.get_text() for p in paragraphs])

        # 두 번째 시도: <div>, <span> 태그에서 텍스트 추출
        divs = soup.find_all('div')
        spans = soup.find_all('span')
        if divs or spans:
            return "\n\n".join([d.get_text() for d in divs] + [s.get_text() for s in spans])

    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred while extracting from {url}: {str(http_err)}")
        return ""
    except Exception as e:
        st.error(f"Error in standard extraction for {url}: {str(e)}")
        return ""

    # 세 번째 시도: Selenium을 사용하여 동적 페이지에서 텍스트 추출
    try:
        return extract_text_with_selenium(url)
    except Exception as e:
        st.error(f"Failed to extract content from {url} using all methods.")
        return ""

# Selenium을 사용한 동적 콘텐츠 크롤링 함수
def extract_text_with_selenium(url):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        driver.get(url)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # 다시 <p> 태그, <div> 태그, <span> 태그에서 텍스트 추출
        paragraphs = soup.find_all('p')
        divs = soup.find_all('div')
        spans = soup.find_all('span')

        text_content = "\n\n".join([p.get_text() for p in paragraphs] +
                                   [d.get_text() for d in divs] +
                                   [s.get_text() for s in spans])

        driver.quit()
        return text_content
    except Exception as e:
        st.error(f"Selenium extraction failed for {url}: {str(e)}")
        return ""

# 내부 링크를 재귀적으로 탐색하고 모든 페이지의 텍스트를 크롤링하는 함수
def crawl_all_links(base_url, current_url, visited, session):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = session.get(current_url, headers=headers, allow_redirects=True)
        response.raise_for_status()  # 404, 403 등의 HTTP 오류가 발생할 경우 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')

        # 현재 페이지에서 내부 링크를 추출
        internal_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)

            # 내부 링크만 추가, 외부 링크나 중복 링크는 제외
            if urlparse(full_url).netloc == urlparse(base_url).netloc and full_url not in visited:
                internal_links.append(full_url)

        # 방문한 링크 목록에 현재 링크 추가
        visited.add(current_url)

        # 현재 페이지의 텍스트 추출
        text = extract_text_from_url(current_url, session)

        # 재귀적으로 모든 내부 링크를 탐색하고 텍스트를 수집
        for link in internal_links:
            if link not in visited:
                text += "\n\n" + ("-" * 50) + "\n\n"
                text += crawl_all_links(base_url, link, visited, session)

        return text
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred while crawling {current_url}: {str(http_err)}")
        return ""
    except Exception as e:
        st.error(f"Error occurred while crawling {current_url}: {str(e)}")
        return ""

# PDF로 텍스트 저장 함수 (유니코드 지원)
def save_text_to_pdf(text, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 유니코드 지원 폰트 추가 (GitHub에서 폰트 파일을 찾을 수 있도록 상대 경로로 설정)
    font_path = os.path.join(os.getcwd(), 'fonts', 'NotoSans-Regular.ttf')
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font('NotoSans', size=12)

    # 텍스트를 PDF로 작성
    pdf.multi_cell(0, 10, text)

    # PDF 저장
    pdf.output(pdf_filename)

# 주 함수: 사이트 내 모든 링크를 재귀적으로 크롤링하고, 모든 데이터를 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename):
    st.write(f"Starting full site crawl from {base_url}...")

    # 방문한 URL을 저장하는 집합(set)
    visited = set()

    # 세션을 사용하여 모든 페이지를 크롤링
    session = requests.Session()

    # 메인 URL부터 시작하여 모든 내부 페이지를 크롤링
    all_text = crawl_all_links(base_url, base_url, visited, session)

    # 텍스트를 PDF로 저장
    save_text_to_pdf(all_text, pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Full Website to PDF Converter (with Error Handling)")

    # URL 입력
    url_input = st.text_input("Enter the base URL:")

    if st.button("Create PDF"):
        if url_input:
            pdf_filename = "site_output.pdf"
            create_pdf_from_site(url_input, pdf_filename)
            # PDF 다운로드 링크 제공
            with open(pdf_filename, "rb") as pdf_file:
                st.download_button(
                    label="Download PDF",
                    data=pdf_file,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
        else:
            st.error("Please enter a valid URL")

if __name__ == "__main__":
    main()

