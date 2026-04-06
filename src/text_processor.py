import spacy
import re
from spacy.util import compile_infix_regex
from spacy.util import filter_spans

nlp = spacy.load("en_core_web_sm")    


class Text_Processor:
    def __init__(self):
        pass


    def auto_merge_hyphens(self, doc):
        """Tự động tìm và gộp mọi cụm từ có dấu gạch nối (Ví dụ: state-of-the-art)"""
        matches = []
        i = 0
        while i < len(doc) - 1:
            # Nếu tìm thấy dấu gạch nối dính liền (không có khoảng trắng xung quanh)
            if doc[i].text == "-" and not doc[i].is_space:
                # Xác định vùng bắt đầu và kết thúc của cụm từ ghép
                start = i - 1
                end = i + 1
                
                # Mở rộng về phía sau nếu vẫn còn cấu trúc -Từ-Từ...
                while end < len(doc) and (doc[end].text == "-" or (end > 0 and doc[end-1].text == "-")):
                    end += 1
                
                # Chỉ gộp nếu vùng này hợp lệ (bắt đầu bằng từ, kết thúc bằng từ)
                if start >= 0:
                    matches.append(doc[start:end])
                i = end # Nhảy qua cụm đã xử lý để tránh lặp
            else:
                i += 1

            # Thực hiện gộp các vùng đã tìm thấy
            for token in doc:
                if token.dep_ == "compound":
                    # Tạo span từ từ bổ nghĩa đến từ chính
                    matches.append(doc[token.i : token.head.i + 1])
        
        # 3. Lọc bỏ các cụm chồng lấn, chỉ giữ lại cụm dài nhất (Xử lý lỗi E102)
        return filter_spans(matches)
    
    


    def process_raw_text(self, raw_text):
        """
        Xử lý danh sách kết quả từ OCR Engine.
        raw_text: [{"page": 1, "content": "..."}, ...]
        """
        all_vocab_data = []
        unwanted_pos = {"DET", "PRON", "PART", "NUM"}

        for page in raw_text:
            page_number = page.get('page')
            text = page.get('content', '')

            if not text:
                continue

            # Sử dụng spaCy để phân tích toàn bộ văn bản của trang
            doc = nlp(text)

            merge_spans = self.auto_merge_hyphens(doc)

            with doc.retokenize() as retokenizer:
                for span in merge_spans:
                    # Nếu cụm có dấu gạch nối, ép kiểu sang ADJ để noun_chunks hoạt động đúng
                    attrs = {"POS": "ADJ"} if "-" in span.text else {}
                    retokenizer.merge(span, attrs=attrs)

            # Chia văn bản thành các câu (Sentence Segmentation)
            for sent in doc.sents:
                clean_sentence = " ".join(sent.text.split())

                token_in_compounds = set()

                for token in sent:
                    if "-" in token.text and not token.is_punct:
                        all_vocab_data.append({
                            "word": token.text,
                            "lemma": token.lemma_.lower(),
                            "pos": token.pos_,
                            "is_stop": token.is_stop,
                            "context": clean_sentence,
                            "page": page_number
                        })
                        token_in_compounds.add(token.i)

                # # Noun Chunks
                # chunks = []
                # for chunk in sent.noun_chunks:
                #     if any(t.i in token_in_compounds for t in chunk):
                #         continue 

                #     start = chunk.start
                #     while start < chunk.end and doc[start].pos_ in unwanted_pos:
                #         start += 1

                #     chunk_text = doc[start : chunk.end].text
                #     if len(chunk_text.split()) > 1:
                #         chunks.append({ 
                #             "word": chunk.text, 
                #             "lemma": chunk.lemma_.lower(), 
                #             "pos": "NOUN_PHRASE", 
                #             "is_stop": False, 
                #             "context": clean_sentence, 
                #             "page": page_number
                #         })

                #         for i in range(start, chunk.end):
                #             token_in_compounds.add(i)


                
                # Tokenization
                for token in sent:
                    # Lọc: chỉ lấy từ thực (không lấy dấu câu, số, hay stopword)
                    if token.i in token_in_compounds or token.is_space or token.is_punct: 
                        continue
                        
                    all_vocab_data.append({
                        "word": token.text,           # Từ gốc (ví dụ: "running")
                        "lemma": token.lemma_.lower(), # Từ nguyên thể (ví dụ: "run")
                        "pos": token.pos_,             # Loại từ để filter sau này
                        "is_stop": token.is_stop,      # Đánh dấu stopword để filter sau
                        "context": clean_sentence,      # Ngữ cảnh của câu
                        "page": page_number
                    })

                # all_vocab_data.extend(chunks)
        
        return all_vocab_data



if __name__ == "__main__":
    # Giả lập dữ liệu từ OCR để test file này độc lập
    sample_ocr = [{"page": 1, "content": "There isn't a cloud in sight, and the wind has hung in the east for nigh on to a week."}]
    
    processor = Text_Processor()
    results = processor.process_raw_text(sample_ocr)
    
    for item in results:
        print(f"Từ: {item['word']} ({item['pos']}) | Từ gốc: ({item['lemma']}) | Ngữ cảnh: {item['context']}")