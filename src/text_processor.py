import spacy

nlp = spacy.load("en_core_web_sm")


class Text_Processor:
    def __init__(self):
        pass


    def process_raw_text(self, raw_text):
        """
        Xử lý danh sách kết quả từ OCR Engine.
        raw_text: [{"page": 1, "content": "..."}, ...]
        """
        all_vocab_data = []

        for page in raw_text:
            page_number = page.get('page')
            text = page.get('content', '')
            
            if not text:
                continue

            # Sử dụng spaCy để phân tích toàn bộ văn bản của trang
            doc = nlp(text)

            # 1. Chia văn bản thành các câu (Sentence Segmentation)
            for sent in doc.sents:
                clean_sentence = " ".join(sent.text.split())
                
                # 2. Duyệt từng từ trong câu (Tokenization)
                for token in sent:
                    # Lọc: chỉ lấy từ thực (không lấy dấu câu, số, hay stopword)
                    if token.is_space or token.is_punct: 
                        continue
                        
                    all_vocab_data.append({
                        "word": token.text,           # Từ gốc (ví dụ: "running")
                        "lemma": token.lemma_.lower(), # Từ nguyên thể (ví dụ: "run")
                        "pos": token.pos_,             # Loại từ để filter sau này
                        "is_stop": token.is_stop,      # Đánh dấu stopword để filter sau
                        "context": clean_sentence,      # Ngữ cảnh của câu
                        "page": page_number
                    })
        
        return all_vocab_data



if __name__ == "__main__":
    # Giả lập dữ liệu từ OCR để test file này độc lập
    sample_ocr = [{"page": 1, "content": "Machine Learning is a field of Artificial Intelligence. It uses algorithms to analyze data."}]
    
    processor = Text_Processor()
    results = processor.process_raw_text(sample_ocr)
    
    for item in results:
        print(f"Từ: {item['word']} ({item['pos']}) | Từ gốc: ({item['lemma']}) | Ngữ cảnh: {item['context']}")