import pytesseract
from pdf2image import convert_from_path
import os

from concurrent.futures import ProcessPoolExecutor


# src
current_dir = os.path.dirname(os.path.abspath(__file__))
# root
project_root = os.path.dirname(current_dir)

# ocr
tesseract_folder_name = "Tesseract-OCR" 
tesseract_exe_path = os.path.join(project_root, tesseract_folder_name, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path

POPPLER_BIN = os.path.join(project_root, 'poppler', 'Library', 'bin')

def ocr_single_page(page_data):
    index, image = page_data

    try:
        text = pytesseract.image_to_string(image, lang='eng')
        image.close() # Giải phóng bộ nhớ ngay sau khi xong
        return {"page": index + 1, "content": text.strip()}
    except Exception as e:
        return {"page": index + 1, "content": f"Lỗi: {str(e)}"}




class OCR_Engine:
    def __init__(self, poppler_path=POPPLER_BIN):
        self.poppler_path = poppler_path


    def extract_raw_text(self, pdf_path):
        """
        Trích xuất văn bản thô từ PDF và giữ nguyên định dạng câu/đoạn.
        Trả về: Danh sách các dictionary chứa số trang và nội dung.
        """
        try:
            print(f"--- Đang xử lý file: {os.path.basename(pdf_path)} ---")
            images = convert_from_path(pdf_path, dpi=300, poppler_path=self.poppler_path)

            pages_to_process = list(enumerate(images))
            
            if len(pages_to_process) < 10:
                for i, image in enumerate(images):
                    # Lấy text thô, không filter để giữ ngữ cảnh câu
                    text = pytesseract.image_to_string(image, lang='eng')
                    
                    extracted_data.append({
                        "page": i + 1,
                        "content": text.strip()
                    })
                    
                    image.close()
                    print(f"Đã xử lý xong trang {i+1}/{len(images)}")


            with ProcessPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(ocr_single_page, pages_to_process))
            
            # Sắp xếp lại kết quả theo đúng thứ tự trang (vì chạy song song có thể trả về xáo trộn)
            extracted_data = sorted(results, key=lambda x: x['page'])
            
            print(f"✅ Đã xử lý xong {len(images)} trang.")
                
            return extracted_data
        
        except Exception as e:
            print(f"Lỗi trong quá trình OCR: {e}")
            return []
        


    # def extract_text_from_pdf(pdf_path,output_file, poppler_path=None):
    #     try:
    #         images = convert_from_path(pdf_path,dpi = 300, poppler_path=poppler_path)
    #         total_pages = len(images)
            
    #         print(f"--- Đang xử lý file: {os.path.basename(pdf_path)} ---")
            
    #         with open(output_file, "w", encoding="utf-8") as f:
    #             for i, image in enumerate(images):
    #                 # OCR trang hiện tại
    #                 text = pytesseract.image_to_string(image, lang='eng')
    #                 text = clean_and_filter_text(text)

    #                 # Ghi 
    #                 f.write(f"\n--- PAGE {i+1} ---\n")
    #                 f.write(text)
    #                 f.flush()
                    
    #                 image.close()
                    
    #                 print(f"Đã ghi xong trang {i+1}/{total_pages} vào {os.path.basename(output_file)}")
                    
    #         return True
    #     except Exception as e:
    #         print(f"Lỗi: {e}")
    #         return False




if __name__ == "__main__":
    # Test 
    # test_pdf = os.path.join(project_root, "data", "raw", "test2.pdf")
    
    # if os.path.exists(test_pdf):
    #     success = extract_text_from_pdf(test_pdf, OUTPUT_PATH, poppler_path=POPPLER_BIN)
    #     if success:
    #         print(f"\n✅ Hoàn thành! Kết quả nằm tại: {OUTPUT_PATH}")
    # else:
    #     print("Vui lòng bỏ file PDF vào data/raw/ để test!")


    test_pdf = os.path.join(project_root, "data", "raw", "test2.pdf")
    engine = OCR_Engine()
    raw_results = engine.extract_raw_text(test_pdf)
    
    # Lưu tạm ra file raw để kiểm tra (không filter)
    output_raw = os.path.join(project_root, 'output', 'raw_dump.txt')
    with open(output_raw, "w", encoding="utf-8") as f:
        for page in raw_results:
            f.write(f"\n--- PAGE {page['page']} ---\n")
            f.write(page['content'])
    
    print(f"✅ Đã trích xuất xong văn bản thô tại: {output_raw}")