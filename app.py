import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 로그 파일 설정
logging.basicConfig(filename='error_log.txt', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# URL에서 데이터를 가져와 텍스트를 추출하는 함수
def extract_text_from_url(url, progress_bar, task_num, total_tasks):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        paragraphs = soup.find_all('p')
        text_content = "\n\n".join([p.get_text() for p in paragraphs])

        # 진행상황 업데이트
        progress_bar.progress((task_num + 1) / total_tasks)

        return text_content
    except Exception as e:
        logging.error(f"Error extracting text from {url}: {str(e)}")
        return ""

# 내부 링크 추출 함수
def extract_internal_links(url, base_url, depth, visited_urls):
    if url in visited_urls:
        return []

    visited_urls.add(url)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        internal_links = []

        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc and full_url not in visited_urls:
                internal_links.append(full_url)

        if depth > 1:
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(extract_internal_links, link, base_url, depth - 1, visited_urls) for link in internal_links]
                for future in as_completed(futures):
                    new_links = future.result()
                    internal_links.extend(new_links)

        return list(set(internal_links))
    except Exception as e:
        logging.error(f"Error extracting links from {url}: {str(e)}")
        return []

# PDF로 텍스트를 저장하는 함수
def save_text_to_pdf(text, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = os.path.join(os.getcwd(), 'fonts', 'NotoSans-Regular.ttf')
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font('NotoSans', size=12)

    pdf.multi_cell(0, 10, text)
    pdf.output(pdf_filename)

# 주 함수: 사이트 내 모든 링크와 글을 크롤링하여 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename, depth=1):
    st.write(f"Starting extraction from {base_url} with depth {depth}...")

    visited_urls = set()

    all_links = extract_internal_links(base_url, base_url, depth, visited_urls)

    all_text = ""

    total_tasks = len(all_links)
    progress_bar = st.progress(0)  # 진행상황 바 생성

    with ThreadPoolExecutor() as executor:
        text_futures = {executor.submit(extract_text_from_url, link, progress_bar, i, total_tasks): link for i, link in enumerate(all_links)}

        for future in as_completed(text_futures):
            link = text_futures[future]
            try:
                text = future.result()
                if text:
                    all_text += text + "\n\n" + ("-" * 50) + "\n\n"
            except Exception as e:
                logging.error(f"Error extracting text from {link}: {str(e)}")

    save_text_to_pdf(all_text, pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Website to PDF Converter (Text Only)")

    url_input = st.text_input("Enter the base URL:")
    depth = st.slider("Select the depth for crawling:", min_value=1, max_value=5, value=1)

    if st.button("Create PDF"):
        if url_input:
            pdf_filename = "site_output.pdf"
            create_pdf_from_site(url_input, pdf_filename, depth)
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
