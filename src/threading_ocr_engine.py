import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
import os
import re
import spacy
from queue import Queue
import threading
import concurrent.futures
from spellchecker import SpellChecker
spell = SpellChecker()
image_queue = Queue(maxsize=20)
text_queue = Queue()
nlp = spacy.load("en_core_web_md")  
# src
current_dir = os.path.dirname(os.path.abspath(__file__))
# root
project_root = os.path.dirname(current_dir)

# ocr
tesseract_folder_name = "Tesseract-OCR" 
tesseract_exe_path = os.path.join(project_root, tesseract_folder_name, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path

#########################################################################
#                                                                       #
#                                DEBUG                                  #
#                                                                       #
#########################################################################
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m' 

ICON_CAM = "📸"
ICON_OCR = "🤖"
ICON_FILE = "📝"
ICON_WAIT = "⏳"


POPPLER_BIN = os.path.join(project_root, 'poppler', 'Library', 'bin')
OUTPUT_PATH = os.path.join(project_root, 'output', 'output.txt')
COMMON_WORDS = {
    # Pronouns
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "we", "us", "our", "ours", "ourselves", "they", "them", "their", "theirs", "themselves",

    # Articles & Demonstratives
    "a", "an", "the", "this", "that", "these", "those",

    # Conjunctions & Connectors
    "and", "but", "or", "so", "because", "although", "though", "while", "if",
    "then", "thus",

    # Verbs: Be, Do, Have, Modals
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",

    # Prepositions
    "in", "on", "at", "by", "with", "about", "for", "of", "to", "from",
    "into", "onto", "over", "under",
    "up", "down", "out", "off",

    # Quantifiers & Adverbs
    "all", "any", "some", "many", "much", "few", "more", "most", "other", "another",
    "such", "no", "nor", "not", "only", "own", "same", "than", "too", "very",
    "quite", "rather", "extremely", "really", "enough", "almost", "nearly", "just", "already",
    "always", "never", "often", "sometimes", "usually", "rarely", "seldom", "ever",

    # Question Words
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",

    "s", "t", "d", "re", "ve", "m", "ll", "etc", "eg", "ie",
}
SAFE_2_LETTER_WORDS = {"is", "am", "be", "do", "go"}
seen_words = set()
data_lock = threading.Lock()

def thread_capture_images(pdf_path, poppler_path):
    print(f"{Color.BLUE}[Thread 1] Đang lấy thông tin PDF...")
    info = pdfinfo_from_path(pdf_path, poppler_path=poppler_path)
    total_pages = info["Pages"]
    
    print(f"{Color.BLUE}[Thread 1] PDF có {total_pages} trang. Bắt đầu chuyển đổi cuốn chiếu...")

    for i in range(1, total_pages + 1):
        page_image = convert_from_path(
            pdf_path, 
            dpi=300, 
            first_page=i, 
            last_page=i, 
            poppler_path=poppler_path
        )
        
        if page_image:
            image_queue.put((i, page_image[0])) 
            print(f"{Color.RED}{ICON_CAM}[Thread 1] Đã nạp trang {i}/{total_pages}")
    print(f"{Color.BLUE}[Thread 1] Đã hoàn thành nhiệm vụ.") 
    for _ in range(num_workers):
        image_queue.put(None)   
def thread_ocr_worker():
    print(f"{Color.BLUE}[{threading.current_thread().name}] Worker đã sẵn sàng...")
    while True:
        data = image_queue.get()
        if data is None: 
            break 

        page_num, img = data

        raw_text = pytesseract.image_to_string(img, lang='eng')
        result = clean_and_filter_text(raw_text)
        

        text_queue.put((page_num, result))
        print(f"{Color.YELLOW}{ICON_OCR}[{threading.current_thread().name}] Đã đọc xong trang {page_num}")
        img.close()
        image_queue.task_done()
    

def thread_file_writer(output_path):
    print(f"{Color.BLUE}[Thread 3] Đang đợi dữ liệu...")
    buffer = {} # Cái rổ chứa các trang chưa đến lượt ghi
    next_page_to_write = 1
    
    with open(output_path, "w", encoding="utf-8") as f:
        while True:
            data = text_queue.get()
            if data is None: break
            
            p_num, content = data
            buffer[p_num] = content
            
            # Kiểm tra xem trang tiếp theo mình cần ghi đã có trong rổ chưa
            while next_page_to_write in buffer:
                f.write(f"--- PAGE {next_page_to_write} ---\n")
                f.write(buffer[next_page_to_write] + "\n")
                del buffer[next_page_to_write] # Ghi xong thì xóa cho nhẹ RAM
                print(f"{Color.GREEN}{ICON_FILE}[Thread 3] Đã ghi xong trang {next_page_to_write}")
                next_page_to_write += 1
                f.flush()
                
            text_queue.task_done()
def clean_and_filter_text(raw_text):
    doc = nlp(raw_text)
    filtered_words = []
    exclude_entities = ["PERSON", "GPE", "ORG", "LOC", "DATE", "TIME", "MONEY", "PERCENT"]

    for token in doc:

        if token.ent_type_ in exclude_entities:
            continue
        word_lemma = token.lemma_.lower()
        clean_lemma = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', word_lemma)
        if clean_lemma:
            length = len(clean_lemma)
            if length < 3 and clean_lemma not in SAFE_2_LETTER_WORDS and clean_lemma not in ["i", "a"]:
                continue
            if clean_lemma in seen_words:
                continue
            if clean_lemma in COMMON_WORDS:
                continue
            if spell.unknown([clean_lemma]):
                continue
            with data_lock:
                if clean_lemma in seen_words:
                    continue
                seen_words.add(clean_lemma)
            filtered_words.append(clean_lemma)
            
    return " ".join(filtered_words)
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
    test_pdf = os.path.join(project_root, "data", "raw", "test2.pdf")
    
    if os.path.exists(test_pdf):
        print(f"--- BẮT ĐẦU PIPELINE XỬ LÝ: {os.path.basename(test_pdf)} ---")
        #worker threads
        t1 = threading.Thread(target=thread_capture_images, args=(test_pdf, POPPLER_BIN), name="Capturer")
        
        workers = []
        num_workers = 2#tang len dc 
        for i in range(num_workers): 
            tw = threading.Thread(target=thread_ocr_worker, name=f"Worker-{i+1}")
            workers.append(tw)
            
        t3 = threading.Thread(target=thread_file_writer, args=(OUTPUT_PATH,), name="Writer")

        # Kích hoạt
        t1.start()
        for tw in workers: tw.start()
        t3.start()

        t1.join() 
        

        for _ in range(len(workers)):
            image_queue.put(None)
            
        for tw in workers: tw.join()
        
        text_queue.put(None) 
        
        t3.join()

        print(f"\n✅ HOÀN THÀNH XUẤT SẮC! Kết quả tại: {OUTPUT_PATH}")
    else:
        print(f"Lỗi: Không tìm thấy file {test_pdf}")