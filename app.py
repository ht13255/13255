import streamlit as st
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

# 웹 페이지 내용 크롤링
def scrape_page(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator='\n')
    except Exception as e:
        return f"Error fetching the page: {e}"

# PDF 생성
def create_pdf(content, filename='output.pdf'):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font('Arial', '', 'path/to/arial.ttf', uni=True)  # TTF 폰트 경로 추가
    pdf.set_font('Arial', '', 12)

    for line in content.split('\n'):
        try:
            pdf.cell(200, 10, txt=line, ln=True)
        except:
            pdf.cell(200, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=True)

    pdf.output(filename)
    return filename

# Streamlit 애플리케이션
def main():
    st.title("웹 페이지 크롤링 및 PDF 생성기")
    
    url = st.text_input("사이트 URL을 입력하세요:", "")
    
    if st.button("크롤링 시작"):
        if url:
            st.write(f"크롤링 중: {url}")
            content = scrape_page(url)
            if "Error" not in content:
                st.write("크롤링 완료!")
                st.text_area("크롤링된 내용:", content[:500])  # 크롤링한 내용을 미리보기로 출력
                pdf_file = create_pdf(content)
                with open(pdf_file, "rb") as file:
                    st.download_button("PDF 다운로드", file, file_name="scraped_content.pdf")
            else:
                st.error(content)
        else:
            st.error("URL을 입력하세요!")

if __name__ == "__main__":
    main()
