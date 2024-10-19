import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os
import logging
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

# 로그 파일 설정
logging.basicConfig(filename='error_log.txt', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 이미지 확장자 확인 함수
def is_valid_image_url(url):
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    return url.lower().endswith(valid_extensions)

# webp 이미지를 JPG 또는 PNG로 변환하는 함수
def convert_webp_to_png(image_path):
    try:
        img = Image.open(image_path)
        png_path = image_path.replace('.webp', '.png')
        img.save(png_path, 'PNG')  # PNG 형식으로 변환하여 저장
        return png_path
    except Exception as e:
        logging.error(f"Failed to convert webp to PNG: {str(e)}")
        return None

# 이미지 다운로드 함수 (webp 변환 포함)
def download_image(url, folder, downloaded_images, progress_bar, task_num, total_tasks):
    try:
        if not is_valid_image_url(url):
            return None

        if url in downloaded_images:
            return downloaded_images[url]

        if not os.path.exists(folder):
            os.makedirs(folder)

        # 기본 헤더로 이미지 다운로드 시도
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

        # 이미지 파일 이름 추출
        image_name = os.path.join(folder, url.split("/")[-1])

        # 이미지 저장
        with open(image_name, 'wb') as f:
            f.write(response.content)

        # webp 이미지 처리: webp를 PNG로 변환
        if image_name.lower().endswith('.webp'):
            image_name = convert_webp_to_png(image_name)

        # 캐시에 이미지 경로 저장
        downloaded_images[url] = image_name

        # 진행상황 업데이트
        progress_bar.progress((task_num + 1) / total_tasks)

        return image_name

    except Exception as e:
        logging.error(f"Error downloading image {url}: {str(e)}")
        return None

# Selenium을 사용해 스크린샷을 캡처하는 함수
def capture_screenshot(url, folder):
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        driver.get(url)

        screenshot_name = os.path.join(folder, f"screenshot_{urlparse(url).netloc}.png")
        driver.save_screenshot(screenshot_name)
        driver.quit()

        return screenshot_name
    except Exception as e:
        logging.error(f"Failed to capture screenshot for {url}: {str(e)}")
        return None

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

# 내부 링크 및 이미지 추출 함수
def extract_internal_links_and_images(url, base_url, depth, visited_urls, images_folder="images", downloaded_images=None):
    if downloaded_images is None:
        downloaded_images = {}

    if url in visited_urls:
        return [], []

    visited_urls.add(url)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        internal_links = []
        images = []

        for link in soup.find_all('a', href=True):
            href = link.get('href')
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc and full_url not in visited_urls:
                internal_links.append(full_url)

        for img in soup.find_all('img', src=True):
            img_url = urljoin(base_url, img['src'])
            if img_url not in images:
                images.append(img_url)

        if depth > 1:
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(extract_internal_links_and_images, link, base_url, depth - 1, visited_urls, images_folder, downloaded_images) for link in internal_links]
                for future in as_completed(futures):
                    new_links, new_images = future.result()
                    internal_links.extend(new_links)
                    images.extend(new_images)

        return list(set(internal_links)), images
    except Exception as e:
        logging.error(f"Error extracting links and images from {url}: {str(e)}")
        return [], []

# PDF로 텍스트와 이미지를 저장하는 함수
def save_text_and_images_to_pdf(text, image_paths, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = os.path.join(os.getcwd(), 'fonts', 'NotoSans-Regular.ttf')
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font('NotoSans', size=12)

    pdf.multi_cell(0, 10, text)

    for image_path in image_paths:
        try:
            pdf.add_page()
            pdf.image(image_path, x=10, y=10, w=pdf.w - 20)
        except Exception as e:
            logging.error(f"Failed to add image {image_path} to PDF: {str(e)}")

    pdf.output(pdf_filename)

# 주 함수: 사이트 내 모든 링크와 글을 크롤링하여 PDF로 저장
def create_pdf_from_site(base_url, pdf_filename, depth=1):
    st.write(f"Starting extraction from {base_url} with depth {depth}...")

    visited_urls = set()
    downloaded_images = {}

    all_links, all_images = extract_internal_links_and_images(base_url, base_url, depth, visited_urls, downloaded_images=downloaded_images)

    all_text = ""

    total_tasks = len(all_links) + len(all_images)
    progress_bar = st.progress(0)  # 진행상황 바 생성

    with ThreadPoolExecutor() as executor:
        text_futures = {executor.submit(extract_text_from_url, link, progress_bar, i, total_tasks): link for i, link in enumerate(all_links)}
        image_futures = {executor.submit(download_image, img, "images", downloaded_images, progress_bar, len(all_links) + i, total_tasks): img for i, img in enumerate(all_images)}

        for future in as_completed(text_futures):
            link = text_futures[future]
            try:
                text = future.result()
                if text:
                    all_text += text + "\n\n" + ("-" * 50) + "\n\n"
            except Exception as e:
                logging.error(f"Error extracting text from {link}: {str(e)}")

        image_paths = []
        for future in as_completed(image_futures):
            img = image_futures[future]
            try:
                image_path = future.result()
                if image_path:
                    image_paths.append(image_path)
            except Exception as e:
                logging.error(f"Error downloading image {img}: {str(e)}")

    save_text_and_images_to_pdf(all_text, image_paths, pdf_filename)
    st.success(f"PDF saved as {pdf_filename}")

# Streamlit UI
def main():
    st.title("Website to PDF Converter with Progress Indicator")

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
