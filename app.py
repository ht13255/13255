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
        # 페이지에서 텍스트 추출
        response = session.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 기본적으로 <p> 태그의 텍스트를 모두 가져온다.
        paragraphs = soup.find_all('p')
        if paragraphs:
            return "\n\n".join([p.get_text() for p in paragraphs])

        # <div>, <span> 등의 태그에서도 텍스트를 추출
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

# 내부 링크를 탐색하고 순차적으로 페이지에 방문 후 돌아와서 다음 링크 크롤링
def crawl_and_return(base_url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 메인 페이지에서 모든 링크를 추출
        response = session.get(base_url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 내부 링크만 추출
        internal_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)

            # 내부 링크만 추가
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                internal_links.append(full_url)

        # 중복 제거
        internal_links = list(set(internal_links))

        # 순차적으로 링크를 방문하여 크롤링
        all_text = ""
        for idx, link in enumerate(internal_links):
            st.write(f"Visiting {link} ({idx + 1}/{len(internal_links)})...")
            text = extract_text_from_url(link, session)
            if text:
                all_text += text + "\n\n" + ("-" * 50) + "\n\n"

        return all_text

    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred while accessing {base_url}: {str(http_err)}")
        return ""
    except Exception as e:
        st.error(f"Error occurred while crawling {base_url}: {str(e)}")
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

# 주 함수: 사이트 내 모든 링크를 순차적으로 크롤링하고, 모든 데이터를 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename):
    st.write(f"Starting site crawl from {base_url}...")

    # 세션을 사용하여 모든 페이지를 크롤링
    session = requests.Session()

    # 사이트 내 모든 링크를 방문하고 돌아오면서 텍스트를 수집
    all_text = crawl_and_return(base_url, session)

    # 텍스트를 PDF로 저장
    if all_text:
        save_text_to_pdf(all_text, pdf_filename)
        st.success(f"PDF saved as {pdf_filename}")
    else:
        st.error("No content to save.")

# Streamlit UI
def main():
    st.title("Sequential Website Crawler to PDF Converter")

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
