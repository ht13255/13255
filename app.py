import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os
import logging
from PIL import Image
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

# 로그 파일 설정
logging.basicConfig(filename='error_log.txt', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 이미지 확장자 확인 함수
def is_valid_image_url(url):
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    return url.lower().endswith(valid_extensions)

# 이미지 다운로드 함수 (캐시 추가 및 차단된 이미지 처리)
def download_image(url, folder, downloaded_images):
    try:
        # 이미지 URL이 유효한지 확인
        if not is_valid_image_url(url):
            st.warning(f"Skipping invalid image URL: {url}")
            return None

        # 이미지가 이미 다운로드되었는지 확인
        if url in downloaded_images:
            st.write(f"Image already downloaded: {url}")
            return downloaded_images[url]

        if not os.path.exists(folder):
            os.makedirs(folder)

        # 기본 헤더로 이미지 다운로드 시도
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            # 기본 요청 실패 시 사용자 에이전트를 추가한 헤더로 재시도
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

        # 이미지 파일 이름 추출
        image_name = os.path.join(folder, url.split("/")[-1])

        # 이미지 저장
        with open(image_name, 'wb') as f:
            f.write(response.content)

        # 캐시에 이미지 경로 저장
        downloaded_images[url] = image_name

        return image_name

    except Exception as e:
        # 이미지 다운로드에 실패할 경우 Selenium으로 스크린샷을 찍어서 저장
        st.error(f"Error downloading image {url}. Attempting screenshot instead.")
        logging.error(f"Error downloading image {url}: {str(e)}")
        return capture_screenshot(url, folder)

# Selenium을 사용해 스크린샷을 캡처하는 함수
def capture_screenshot(url, folder):
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)

        # Selenium WebDriver 설정
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        driver.get(url)

        # 스크린샷 파일 경로 설정
        screenshot_name = os.path.join(folder, f"screenshot_{urlparse(url).netloc}.png")
        driver.save_screenshot(screenshot_name)
        driver.quit()

        return screenshot_name
    except Exception as e:
        error_message = f"Failed to capture screenshot for {url}: {str(e)}"
        st.error(error_message)
        logging.error(error_message)
        return None

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
        error_message = f"Error occurred while extracting text from {url}: {str(e)}"
        st.error(error_message)
        logging.error(error_message)  # 오류를 로그 파일에 기록
        return ""

# 내부 링크 및 이미지 추출 함수 (이미지 캐시 추가)
def extract_internal_links_and_images(url, base_url, depth=1, images_folder="images", downloaded_images=None):
    if downloaded_images is None:
        downloaded_images = {}

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        internal_links = []
        images = []

        # 모든 <a> 태그에서 내부 링크 추출
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                if full_url not in internal_links:
                    internal_links.append(full_url)

        # 모든 <img> 태그에서 이미지 URL 추출
        for img in soup.find_all('img', src=True):
            img_url = urljoin(base_url, img['src'])
            if img_url not in images:
                images.append(img_url)
                download_image(img_url, images_folder, downloaded_images)  # 이미지 다운로드

        return list(set(internal_links)), images  # 중복 제거
    except Exception as e:
        error_message = f"Error occurred while extracting links and images from {url}: {str(e)}"
        st.error(error_message)
        logging.error(error_message)  # 오류를 로그 파일에 기록
        return [], []

# PDF로 텍스트와 이미지를 저장하는 함수
def save_text_and_images_to_pdf(text, image_paths, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 유니코드 지원 폰트 추가
    font_path = os.path.join(os.getcwd(), 'fonts', 'NotoSans-Regular.ttf')
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font('NotoSans', size=12)

    # 텍스트를 PDF로 작성
    pdf.multi_cell(0, 10, text)

    # 이미지를 PDF에 추가
    for image_path in image_paths:
        try:
            pdf.add_page()
            pdf.image(image_path, x=10, y=10, w=pdf.w - 20)  # 이미지 크기 조정
        except Exception as e:
            error_message = f"Failed to add image {image_path} to PDF: {str(e)}"
            st.error(error_message)
            logging.error(error_message)

    # PDF 저장
    pdf.output(pdf_filename)

# 주 함수: 사이트 내 링크를 크롤링하고, 모든 데이터를 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename, depth=1):
    st.write(f"Starting extraction from {base_url} with depth {depth}...")

    # 1. 메인 페이지에서 모든 내부 링크와 이미지 추출 (이미지 캐시 추가)
    downloaded_images = {}
    all_links, all_images = extract_internal_links_and_images(base_url, base_url, depth, downloaded_images=downloaded_images)

    all_text = ""

    # 2. 각 링크에서 텍스트 추출
    for link in all_links:
        st.write(f"Extracting from {link}...")
        text = extract_text_from_url(link)
        if text:
            all_text += text + "\n\n" + ("-" * 50) + "\n\n"

    # 3. 텍스트와 이미지를 PDF로 저장
    save_text_and_images_to_pdf(all_text, list(downloaded_images.values()), pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Website to PDF Converter with Image Support and Screenshot Fallback")

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
