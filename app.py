import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os

# URL에서 데이터를 가져와 텍스트를 추출하는 함수
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # 요청 오류가 있으면 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')

        # 기본적으로 <p> 태그의 텍스트를 모두 가져온다.
        paragraphs = soup.find_all('p')
        text_content = "\n\n".join([p.get_text() for p in paragraphs])

        return text_content
    except Exception as e:
        st.error(f"Error occurred while extracting from {url}: {str(e)}")
        return ""

# 내부 링크를 재귀적으로 탐색하고 모든 페이지의 텍스트를 크롤링하는 함수
def crawl_all_links(base_url, current_url, visited):
    try:
        response = requests.get(current_url)
        response.raise_for_status()
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
        text = extract_text_from_url(current_url)

        # 재귀적으로 모든 내부 링크를 탐색하고 텍스트를 수집
        for link in internal_links:
            if link not in visited:
                text += "\n\n" + ("-" * 50) + "\n\n"
                text += crawl_all_links(base_url, link, visited)

        return text
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

    # 메인 URL부터 시작하여 모든 내부 페이지를 크롤링
    all_text = crawl_all_links(base_url, base_url, visited)

    # 텍스트를 PDF로 저장
    save_text_to_pdf(all_text, pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Full Website to PDF Converter")

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
