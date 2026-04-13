from ocr_engine import OCR_Engine
from text_processor import Text_Processor
from filter_engine_api import Word_Filter

def main():
    ocr_tool = OCR_Engine()
    processor = Text_Processor()
    filter_tool = Word_Filter()


    pdf_path = "../data/raw/test4.pdf"

    print("--- Đang trích xuất văn bản từ PDF... ---")
    raw_pages = ocr_tool.extract_raw_text(pdf_path)



    print("--- Đang phân tích từ vựng... ---")
    extracted_vocab = processor.process_raw_text(raw_pages)



    print("--- Đang lọc từ vựng... ---")
    # final_vocab = filter_tool.filter_vocabulary(extracted_vocab)
    # print(f"\nTìm thấy {len(final_vocab)} từ vựng tiềm năng:")
    
    output = filter_tool.process_in_batches_gemini(extracted_vocab)

if __name__ == "__main__":
    main()


