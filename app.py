import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
import streamlit as st
import os
import time

# 세션을 사용하여 크롤링하는 함수 (타임아웃과 리트라이 횟수 포함)
def extract_text_from_url(url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # 타임아웃 설정을 제거하거나 넉넉히 설정
        response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
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

    except requests.exceptions.RequestException as req_err:
        st.error(f"Request error occurred while extracting from {url}: {str(req_err)}")
        return ""
    except Exception as e:
        st.error(f"Error in standard extraction for {url}: {str(e)}")
        return ""

# 광고 링크 및 외부 링크 필터링
def is_valid_link(href, base_url):
    # 광고 링크 패턴 정의 (여기에 패턴을 추가할 수 있음)
    ad_keywords = ['utm_source', 'affiliate', 'ad', 'advert', 'click']
    
    # 광고 링크 패턴에 맞는지 확인
    if any(keyword in href for keyword in ad_keywords):
        return False

    # 외부 사이트 링크인지 확인
    parsed_href = urlparse(href)
    base_domain = urlparse(base_url).netloc
    
    # 내부 링크만 허용 (기본 도메인과 동일한 링크만 허용)
    if parsed_href.netloc and parsed_href.netloc != base_domain:
        return False

    return True

# 내부 링크를 탐색하고 모든 페이지를 제한 없이 순차적으로 크롤링
def crawl_and_collect_all_pages(base_url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 방문한 페이지를 추적
    visited = set()
    # 크롤링할 페이지 목록
    to_visit = [base_url]
    all_text = ""

    while to_visit:
        current_url = to_visit.pop(0)  # 큐에서 링크를 가져와 크롤링
        if current_url in visited:
            continue  # 이미 방문한 페이지는 재방문하지 않음

        st.write(f"Visiting {current_url}...")
        time.sleep(1)  # 서버에 부담을 주지 않도록 1초 대기, 필요시 조정 가능

        try:
            # 페이지에서 텍스트 크롤링
            response = session.get(current_url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 텍스트 추출
            text = extract_text_from_url(current_url, session)
            if text:
                all_text += text + "\n\n" + ("-" * 50) + "\n\n"

            # 내부 링크 추출 및 필터링
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                full_url = urljoin(base_url, href)

                # 광고 및 외부 링크 필터링
                if full_url not in visited and full_url not in to_visit and is_valid_link(full_url, base_url):
                    to_visit.append(full_url)

            # 방문한 페이지로 추가
            visited.add(current_url)

        except requests.exceptions.RequestException as req_err:
            st.error(f"Request error occurred while accessing {current_url}: {str(req_err)}")
            continue
        except Exception as e:
            st.error(f"Error occurred while crawling {current_url}: {str(e)}")
            continue

    return all_text

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

    # 모든 페이지 방문 및 크롤링
    all_text = crawl_and_collect_all_pages(base_url, session)

    # 텍스트를 PDF로 저장
    if all_text:
        save_text_to_pdf(all_text, pdf_filename)
        st.success(f"PDF saved as {pdf_filename}")
    else:
        st.error("No content to save.")

# Streamlit UI
def main():
    st.title("Filtered Website Crawler to PDF Converter")

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
