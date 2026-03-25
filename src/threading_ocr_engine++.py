import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
import os
import re
import spacy
from queue import Queue
import threading
from spellchecker import SpellChecker
import time
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

# =========================
# THREAD 1: CAPTURE IMAGE
# =========================
def thread_capture_images(pdf_path):
    start_time = time.time()
    print(f"{Color.BLUE}[Capturer] 🔍 Đang quét thông tin PDF...{Color.END}")
    
    info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_BIN)
    total_pages = info["Pages"]
    print(f"{Color.BLUE}[Capturer] 📖 PDF có {total_pages} trang. Bắt đầu convert...{Color.END}")

    for i in range(1, total_pages + 1):
        page_image = convert_from_path(
            pdf_path, dpi=300, first_page=i, last_page=i, poppler_path=POPPLER_BIN
        )

        if page_image:
            image_queue.put((i, page_image[0]))
            # Debug nạp ảnh
            print(f"{Color.BLUE}[Capturer] 📸 Đã nạp trang {i}/{total_pages} (Queue size: {image_queue.qsize()}){Color.END}")

    # Gửi tín hiệu dừng
    for _ in range(num_workers):
        image_queue.put(None)
    
    duration = time.time() - start_time
    print(f"{Color.BLUE}[Capturer] ✅ Hoàn thành sau {duration:.2f}s.{Color.END}")

# =========================
# THREAD 2: OCR
# =========================
def thread_ocr_worker():
    worker_name = threading.current_thread().name
    print(f"{Color.YELLOW}[{worker_name}] 🤖 Sẵn sàng...{Color.END}")
    
    while True:
        data = image_queue.get()
        if data is None:
            print(f"{Color.YELLOW}[{worker_name}] 💤")
            break

        page_num, img = data
        # OCR
        raw_text = pytesseract.image_to_string(img, lang='eng')
        text_queue.put((page_num, raw_text))

        print(f"{Color.GREEN}[{worker_name}] 📝 Đã đọc xong trang {page_num}{Color.END}")

        img.close()
        image_queue.task_done()

# =========================
# NLP BATCH PROCESS
# =========================
def process_texts(page_items):
    start_time = time.time()
    print(f"{Color.CYAN}[NLP] ⚙️ Đang xử lý Batch {len(page_items)} trang với nlp.pipe...{Color.END}")
    
    page_items.sort(key=lambda x: x[0])
    texts = [item[1] for item in page_items]
    local_seen = set()
    results = []
    # Thêm n_process để tận dụng đa nhân cho spaCy
    for doc in nlp.pipe(texts, batch_size=20, n_process=2):
        clean_page_text = clean_and_filter_text(doc, local_seen)
        results.append(clean_page_text)

    duration = time.time() - start_time
    print(f"{Color.CYAN}[NLP] ✅ Xử lý xong sau {duration:.2f}s.{Color.END}")
    return [item[0] for item in page_items], results


def clean_and_filter_text(raw_text,local_seen):
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
            if clean_lemma in COMMON_WORDS:
                continue
            if spell.unknown([clean_lemma]):
                continue
            with data_lock:
                if clean_lemma in local_seen:
                    continue
                local_seen.add(clean_lemma)
            filtered_words.append(clean_lemma)
            
    return " ".join(filtered_words)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    test_pdf = os.path.join(project_root, "data", "raw", "test2.pdf")

    if os.path.exists(test_pdf):
        num_workers = 10

        t1 = threading.Thread(target=thread_capture_images, args=(test_pdf,))
        workers = [
            threading.Thread(target=thread_ocr_worker)
            for _ in range(num_workers)
        ]

        t1.start()
        for w in workers:
            w.start()

        t1.join()
        for w in workers:
            w.join()

        # ====== GOM TEXT ======
        page_items = []
        while not text_queue.empty():
            page_items.append(text_queue.get())

        # ====== NLP BATCH ======
        page_nums, processed = process_texts(page_items)

        # ====== WRITE FILE ======
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            for i, page_num in enumerate(page_nums):
                f.write(f"--- PAGE {page_num} ---\n")
                f.write(processed[i] + "\n")

        print("DONE:", OUTPUT_PATH)

    else:
        print("File not found")