import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os

# 이미지 다운로드 함수
def download_image(img_url, folder="images"):
    if not os.path.exists(folder):
        os.makedirs(folder)

    img_name = os.path.join(folder, img_url.split("/")[-1])
    try:
        img_data = requests.get(img_url).content
        with open(img_name, 'wb') as handler:
            handler.write(img_data)
        return img_name
    except Exception as e:
        st.error(f"Error occurred while downloading image {img_url}: {str(e)}")
        return None

# URL에서 데이터를 가져와 텍스트와 이미지를 추출하는 함수
def extract_content_from_url(url, base_url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 텍스트 추출
        paragraphs = soup.find_all('p')
        text_content = "\n\n".join([p.get_text() for p in paragraphs])

        # 2. 이미지 링크 추출 및 다운로드
        images = soup.find_all('img')
        img_paths = []
        for img in images:
            img_src = img.get('src')
            if img_src:
                img_url = urljoin(base_url, img_src)
                img_path = download_image(img_url)
                if img_path:
                    img_paths.append(img_path)

        return text_content, img_paths
    except Exception as e:
        st.error(f"Error occurred while extracting content from {url}: {str(e)}")
        return "", []

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

# PDF로 텍스트와 이미지를 저장하는 함수 (유니코드 지원)
def save_content_to_pdf(text, img_paths, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 유니코드 지원 폰트 추가
    font_path = os.path.join(os.getcwd(), 'fonts', 'NotoSans-Regular.ttf')
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font('NotoSans', size=12)

    # 텍스트 추가
    pdf.multi_cell(0, 10, text)

    # 이미지 추가
    for img_path in img_paths:
        try:
            pdf.add_page()
            pdf.image(img_path, x=10, y=10, w=pdf.w - 20)  # 이미지 추가 (페이지 중앙 배치)
        except Exception as e:
            st.error(f"Error occurred while adding image {img_path} to PDF: {str(e)}")

    # PDF 저장
    pdf.output(pdf_filename)

# 주 함수: 사이트 내 링크를 크롤링하고, 텍스트와 이미지를 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename, depth=1):
    st.write(f"Starting extraction from {base_url} with depth {depth}...")

    # 1. 메인 페이지에서 모든 내부 링크 추출 (깊이 설정 추가)
    all_links = extract_internal_links(base_url, base_url, depth)

    all_text = ""
    all_images = []
    
    # 2. 각 링크에서 텍스트 및 이미지 추출
    for link in all_links:
        st.write(f"Extracting from {link}...")
        text, img_paths = extract_content_from_url(link, base_url)
        all_text += text + "\n\n" + ("-" * 50) + "\n\n"
        all_images.extend(img_paths)

    # 3. 텍스트와 이미지를 PDF로 저장
    save_content_to_pdf(all_text, all_images, pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Website to PDF Converter with Images and Depth")

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