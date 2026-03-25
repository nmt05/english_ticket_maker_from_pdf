import pytesseract
from pdf2image import convert_from_path
import os
import re
import spacy
nlp = spacy.load("en_core_web_sm")
# src
current_dir = os.path.dirname(os.path.abspath(__file__))
# root
project_root = os.path.dirname(current_dir)

# ocr
tesseract_folder_name = "Tesseract-OCR" 
tesseract_exe_path = os.path.join(project_root, tesseract_folder_name, "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path

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

    # Indefinite Pronouns
    "someone", "somebody", "something", "anyone", "anybody", "anything",
    "everyone", "everybody", "everything", "noone", "nobody", "nothing",


    "s", "t", "d", "re", "ve", "m", "ll", "etc", "eg", "ie",

    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "january", "february", "march", "april", "may", "june", 
    "july", "august", "september", "october", "november", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
}
SAFE_2_LETTER_WORDS = {"is", "am", "be", "do", "go"}
seen_words = set()
def clean_and_filter_text(raw_text):
    doc = nlp(raw_text)
    filtered_words = []
    exclude_entities = ["PERSON", "GPE", "ORG", "LOC"]

    for token in doc:

        if token.ent_type_ in exclude_entities:
            continue
        
        clean_word = re.sub(r'[^a-zA-Z]', '', token.text)
        if clean_word:
            lemma_lower = token.lemma_.lower()
            if lemma_lower in seen_words:
                continue
            if lemma_lower in COMMON_WORDS:
                continue
            length = len(clean_word)
            if length == 1 and lemma_lower not in ['a', 'i']:
                continue
            if length == 2 and lemma_lower not in SAFE_2_LETTER_WORDS:
                continue
            if length > 1 and len(set(lemma_lower)) == 1:
                continue
            seen_words.add(lemma_lower)
            filtered_words.append(clean_word)
            
    return " ".join(filtered_words)
def extract_text_from_pdf(pdf_path,output_file, poppler_path=None):
    try:
        images = convert_from_path(pdf_path,dpi = 300, poppler_path=poppler_path)
        total_pages = len(images)
        
        print(f"--- Đang xử lý file: {os.path.basename(pdf_path)} ---")
        
        with open(output_file, "w", encoding="utf-8") as f:
            for i, image in enumerate(images):
                # OCR trang hiện tại
                text = pytesseract.image_to_string(image, lang='eng')
                text = clean_and_filter_text(text)

                # Ghi 
                f.write(f"\n--- PAGE {i+1} ---\n")
                f.write(text)
                f.flush()
                
                image.close()
                
                print(f"Đã ghi xong trang {i+1}/{total_pages} vào {os.path.basename(output_file)}")
                
        return True
    except Exception as e:
        print(f"Lỗi: {e}")
        return False

if __name__ == "__main__":
    # Test 
    test_pdf = os.path.join(project_root, "data", "raw", "test2.pdf")
    
    if os.path.exists(test_pdf):
        success = extract_text_from_pdf(test_pdf, OUTPUT_PATH, poppler_path=POPPLER_BIN)
        if success:
            print(f"\n✅ Hoàn thành! Kết quả nằm tại: {OUTPUT_PATH}")
    else:
        print("Vui lòng bỏ file PDF vào data/raw/ để test!")