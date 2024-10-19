import os
import pdfkit

def get_pdfkit_config():
    if os.name == 'nt':  # Windows
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        return pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    else:  # macOS, Linux
        return pdfkit.configuration()  # 기본 경로 사용
