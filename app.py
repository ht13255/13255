import time
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st

# 요청을 재시도하는 함수 (최대 3회)
def make_request_with_retry(session, url, headers, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            st.error(f"Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(2)  # 2초 대기 후 재시도
    return None  # 3회 실패 시 None 반환

# 세션을 사용하여 크롤링하는 함수
def extract_text_from_url(url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': url,
    }

    response = make_request_with_retry(session, url, headers)
    if response is None:
        st.warning(f"Failed to crawl {url} after 3 attempts. Skipping...")
        return ""  # 요청이 실패한 경우 빈 텍스트 반환

    try:
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

    except Exception as e:
        st.error(f"Error in extracting text from {url}: {str(e)}")
        return ""

# 광고, 구독, 결제 링크 등을 필터링하여 크롤링하지 않도록 설정
def is_valid_link(href, base_url):
    # 광고 및 결제 관련 링크 패턴 정의
    ad_keywords = ['utm_source', 'affiliate', 'ad', 'advert', 'click', 'sponsored']
    subscription_keywords = ['subscribe', 'newsletter']
    payment_keywords = ['checkout', 'payment', 'cart', 'pricing']

    # 광고 및 결제 관련 링크 필터링
    if any(keyword in href for keyword in ad_keywords + subscription_keywords + payment_keywords):
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

# 내부 링크를 탐색하고 모든 페이지를 너비 우선 방식으로 크롤링
def crawl_and_collect_all_pages(base_url, session, visited):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    all_text = ""

    to_visit = [base_url]

    while to_visit:
        current_url = to_visit.pop(0)  # 큐에서 링크를 가져와 크롤링
        if current_url in visited:
            continue  # 이미 방문한 페이지는 재방문하지 않음

        st.write(f"Visiting {current_url}...")
        time.sleep(2)  # 서버에 부담을 주지 않도록 대기 시간 추가

        # 페이지에서 텍스트 추출
        text = extract_text_from_url(current_url, session)
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

                # 광고 및 구독, 결제 링크 필터링 후 내부 링크만 크롤링
                if full_url not in visited and is_valid_link(full_url, base_url):
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

    # 세션을 사용하여 모든 페이지를 크롤링
    session = requests.Session()  # 세션을 사용하여 쿠키 유지

    # 방문한 페이지 추적
    visited = set()

    # 모든 페이지 방문 및 크롤링
    all_text = crawl_and_collect_all_pages(base_url, session, visited)

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
    st.title("Comprehensive Website Crawler: Excluding Ads, Subscription, and Payment Links")

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
