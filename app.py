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

# 내부 링크 추출 함수 (재귀적으로 페이지를 탐색)
def extract_internal_links(url, base_url, depth=1):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        internal_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)
            
            # 내부 링크만 처리 (도메인이 같은 링크) 및 중복 제거
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                if full_url not in internal_links:
                    internal_links.append(full_url)
        
        # 깊이 설정에 따른 재귀 탐색
        if depth > 1:
            for link in internal_links:
                internal_links.extend(extract_internal_links(link, base_url, depth - 1))

        return list(set(internal_links))  # 중복 제거
    except Exception as e:
        st.error(f"Error occurred while extracting links from {url}: {str(e)}")
        return []

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

# 주 함수: 사이트 내 링크를 크롤링하고, 모든 데이터를 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename, depth=1):
    st.write(f"Starting extraction from {base_url} with depth {depth}...")

    # 1. 메인 페이지에서 모든 내부 링크 추출 (깊이 설정 추가)
    all_links = extract_internal_links(base_url, base_url, depth)

    all_text = ""
    
    # 2. 각 링크에서 텍스트 추출
    for link in all_links:
        st.write(f"Extracting from {link}...")
        text = extract_text_from_url(link)
        if text:
            all_text += text + "\n\n" + ("-" * 50) + "\n\n"

    # 3. 텍스트를 PDF로 저장
    save_text_to_pdf(all_text, pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Website to PDF Converter with Depth")

    # URL 입력
    url_input = st.text_input("Enter the base URL:")
    depth = st.slider("Select the depth for crawling:", min_value=1, max_value=5, value=1)

    if st.button("Create PDF"):
        if url_input:
            pdf_filename = "site_output.pdf"
            create_pdf_from_site(url_input, pdf_filename, depth)
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