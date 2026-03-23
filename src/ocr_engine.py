import pytesseract
from pdf2image import convert_from_path
import os
# src
current_dir = os.path.dirname(os.path.abspath(__file__))

# root
project_root = os.path.dirname(current_dir)

# ocr
tesseract_folder_name = "Tesseract-OCR" 
tesseract_exe_path = os.path.join(project_root, tesseract_folder_name, "tesseract.exe")

# import local folder
pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path


def extract_text_from_pdf(pdf_path, poppler_path=None):
    try:
        # 1. Chuyển PDF thành danh sách các ảnh (PIL images)
        # Nếu dùng Windows, cần truyền poppler_path
        images = convert_from_path(pdf_path, poppler_path=poppler_path)
        
        full_text = ""
        
        print(f"--- Đang xử lý file: {os.path.basename(pdf_path)} ---")
        
        for i, image in enumerate(images):
            # eng support
            text = pytesseract.image_to_string(image, lang='eng')
            full_text += text + "\n"
            print(f"Hoàn thành trang {i+1}/{len(images)}")
            
        return full_text
    
    except Exception as e:
        print(f"Lỗi khi OCR: {e}")
        return ""

if __name__ == "__main__":
    # Test thử module
    # Tạo một file pdf test trong data/raw/ trước khi chạy
    test_pdf = "data/raw/test_page.pdf"
    # Đường dẫn thư mục bin của poppler (ví dụ: r'C:\poppler-24.02.0\Library\bin')
    POPPLER_PATH = os.path.join(base_path, 'poppler', 'Library', 'bin')
    
    if os.path.exists(test_pdf):
        result = extract_text_from_pdf(test_pdf, poppler_path=POPPLER_PATH)
        print("\n--- Kết quả OCR ---")
        print(result[:500] + "...") # In 500 ký tự đầu tiên
    else:
        print("Vui lòng bỏ file PDF vào data/raw/ để test!")