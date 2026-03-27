from google import genai
import json
import os
import time


client = genai.Client(api_key="AIzaSyCAIS5PPjcB4oJeXYeTTpjydnc-jlxjxKU")

# print("--- Danh sách các Model khả dụng ---")
# for model in client.models.list():
#     print(f"Name: {model.name} | Supported Methods: {model.supported_actions}")


class Word_Filter:
    def __init__(self):
        self.excluded_pos = {
            'PRON',   # Đại từ (I, you, who, what...)
            'DET',    # Mạo từ/Chỉ định (a, an, the, those...)
            'ADP',    # Giới từ (in, on, at...)
            'CCONJ',  # Liên từ kết hợp (and, or, but...)
            'SCONJ',  # Liên từ phụ thuộc (because, although...)
            'AUX',    # Trợ động từ/Động từ khuyết thiếu (can, will, must...)
            'NUM',    # Số đếm (1, two, 2024...)
            'PART',   # Các tiểu từ (not, 's, to...)
            'PUNCT'   # Dấu câu (nếu text_processor chưa lọc hết)
        }

        self.months = {
            'january', 'february', 'march', 'april', 'may', 'june', 
            'july', 'august', 'september', 'october', 'november', 'december',
            'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
        }

        # API URL: https://api.dictionaryapi.dev/api/v2/entries/en/
        self.api_url = "https://api.dictionaryapi.dev/api/v2/entries/en/"



    def filter_vocabulary(self, processed_data):
        final_vocab = {}

        for item in processed_data:
            lemma = item['lemma']
            pos = item['pos']
            
            # ĐIỀU KIỆN LOẠI BỎ THÔNG MINH:
            # 1. Nếu loại từ nằm trong danh sách loại bỏ (ngữ pháp)
            if pos in self.excluded_pos:
                continue
                
            # 2. Nếu từ đó là tháng
            if lemma in self.months:
                continue
                
            # 3. Loại bỏ các từ quá ngắn hoặc chứa ký tự đặc biệt (rác OCR)
            if len(lemma) < 2 or not lemma.isalpha():
                continue

            # Lọc trùng theo Lemma
            if lemma not in final_vocab:
                final_vocab[lemma] = item
                
        return list(final_vocab.values())
    



    def enrich_vocabulary(self, word_items):
        """
        Gửi batch từ vựng sang Gemini để lấy thông tin chi tiết.
        word_items: List các dict [{"word": "...", "context": "..."}, ...]
        """
        # Tạo prompt hướng dẫn AI trả về định dạng JSON để dễ xử lý trong Python
        prompt = f"""
        You are an English teacher. Analyze these words from a technical PDF based on their context.
        For each word, provide: 
        1. phonetic (IPA)
        2. cefr level (A1, A2, B1, B2, C1, or C2)
        3. definition_vi (Vietnamese)
        4. definition_en (English)
        5. example (English)
        If the combination of the word forward or backward that word make a meaning, 
        return the combination instead, with the same form as the description above.

        Return ONLY a JSON list of objects. After a word, enter a new line.
        
        Data: {word_items}
        """

        # try:
        #     response = self.model.generate_content(prompt)
        #     # Làm sạch chuỗi trả về để ép kiểu về list trong Python
        #     raw_text = response.text.strip().replace('```json', '').replace('```', '')
        #     return json.loads(raw_text)
        # except Exception as e:
        #     print(f"Lỗi API Gemini: {e}")
        #     return []

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            # Làm sạch text trả về
            raw_text = response.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            
            return json.loads(raw_text)
        
        except Exception as e:
            print(f"Lỗi API Gemini (chuẩn mới): {e}")
            return []



    def process_in_batches(self, processed_data, batch_size=10):
        """ Workflow: clean vocab -> batch -> call API """

        print(f"--- Đang lọc dữ liệu thô ({len(processed_data)} items)... ---")
        vocab_list = self.filter_vocabulary(processed_data)
        print(f"Hoàn thành!")


        """ Chia nhỏ danh sách để tránh quá tải Prompt (Rate limit) """
        final_results = []

        for i in range(0, len(vocab_list), batch_size):
            batch = vocab_list[i : i + batch_size]
            print(f"--- Đang gửi nhóm {i//batch_size + 1} sang Gemini... ---")
            
            # Chỉ gửi word và context để tiết kiệm token
            ai_input = [{"word": x['lemma'], "context": x['context']} for x in batch]
            enriched_data = self.enrich_vocabulary(ai_input)
            
            # Gộp dữ liệu AI trả về với dữ liệu gốc (số trang, POS)
            # for original, ai_info in zip(batch, enriched_data):
            #     original.update(ai_info)
            #     final_results.append(original)

            for j in range(min(len(batch), len(enriched_data))):
                original = batch[j]
                ai_info = enriched_data[j]
                original.update(ai_info)
                final_results.append(original)
            
            # Nghỉ 1-2 giây giữa các lần gọi để tránh lỗi quá tải API miễn phí
            time.sleep(2) 
            
        return final_results
    



if __name__ == "__main__":
    # 1. Giả lập dữ liệu thô từ Text_Processor
    sample_data = [
        {"lemma": "machine", "pos": "NOUN", "context": "Machine learning is great.", "page": 1},
        {"lemma": "the", "pos": "DET", "context": "The book is here.", "page": 1},
        {"lemma": "in", "pos": "ADP", "context": "It is in the box.", "page": 1},
        {"lemma": "algorithm", "pos": "NOUN", "context": "Use this algorithm.", "page": 1},
        {"lemma": "2026", "pos": "NUM", "context": "In 2026 we fly.", "page": 1},
        {"lemma": "january", "pos": "NOUN", "context": "It is January.", "page": 1},
        {"lemma": "he", "pos": "PRON", "context": "He is a student.", "page": 1},
        {"lemma": "analyze", "pos": "VERB", "context": "We need to analyze data.", "page": 1}
    ]

    filter_tool = Word_Filter()

    # TEST BƯỚC 1: Kiểm tra bộ lọc ngữ pháp (Chưa gọi AI)
    print("--- TEST: Lọc ngữ pháp ---")
    clean_list = filter_tool.filter_vocabulary(sample_data)
    
    # print(f"Tổng số từ ban đầu: {len(sample_data)}")
    # print(f"Số từ sau khi lọc: {len(clean_list)}")
    # for item in clean_list:
    #     print(f"Giữ lại: {item['lemma']} ({item['pos']})")

    result = filter_tool.process_in_batches(clean_list, batch_size=1)
    print(result)


