import os
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import streamlit as st

# Streamlit 설정
st.title("웹사이트 텍스트 및 이미지 취합 PDF 생성기")

# PDF 클래스 정의
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Website Content Compilation', 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(10)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_image(self, image_path):
        try:
            self.image(image_path, w=150)  # 이미지 크기를 적절히 조정
            self.ln()
        except Exception as e:
            st.write(f"Error adding image {image_path}: {e}")

    def add_page_content(self, title, body, images):
        self.add_page()
        self.chapter_title(title)
        self.chapter_body(body)
        for img in images:
            self.add_image(img)

def extract_content_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 텍스트 추출
        paragraphs = soup.find_all('p')
        text = '\n'.join([para.get_text() for para in paragraphs])
        
        # 이미지 URL 추출
        images = []
        img_tags = soup.find_all('img')
        for img in img_tags:
            img_url = img.get('src')
            if not img_url.startswith('http'):
                img_url = requests.compat.urljoin(url, img_url)  # 상대 경로 처리
            images.append(download_image(img_url))

        return text, images
    except Exception as e:
        st.write(f"Error fetching {url}: {e}")
        return "", []

def download_image(img_url):
    try:
        response = requests.get(img_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img_path = os.path.basename(img_url)  # 이미지 파일명만 추출
        img.save(img_path)
        return img_path
    except Exception as e:
        st.write(f"Error downloading image {img_url}: {e}")
        return None

def create_pdf_from_links(urls, output_filename='output.pdf'):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for url in urls:
        text, images = extract_content_from_url(url)
        if text or images:
            pdf.add_page_content(f"Content from {url}", text, images)
        else:
            st.write(f"No content found for {url}")
    
    pdf.output(output_filename)
    st.success(f"PDF saved as {output_filename}")

    # 다운로드한 이미지 파일들 삭제
    for url in urls:
        _, images = extract_content_from_url(url)
        for img in images:
            if img and os.path.exists(img):
                os.remove(img)

# Streamlit UI 요소
st.write("웹사이트 링크를 입력하세요:")
urls = st.text_area("웹사이트 링크들 (한 줄에 하나씩 입력)", height=200)

if st.button("PDF 생성"):
    # 링크 리스트로 변환
    url_list = urls.splitlines()
    
    if url_list:
        output_filename = "output.pdf"
        create_pdf_from_links(url_list, output_filename)

        # PDF 다운로드 링크 제공
        with open(output_filename, "rb") as f:
            st.download_button(label="PDF 다운로드", data=f, file_name=output_filename, mime='application/pdf')
