from google import genai
import json
import os
import time
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import threading

# src
current_dir = os.path.dirname(os.path.abspath(__file__))
# root
project_root = os.path.dirname(current_dir)

client = genai.Client(api_key=your_API_key)

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

        self.forbidden_lemmas = {
            'be', 'do', 'have', 'will', 'can', 'may', 'shall', 'must', 'would', 'should',
            'get', 'go', 'say', 'come', 'take', 'make', 'use', 'know', 'think', 'look',
            'a', 'an', 'the', 'not', 'very', 'too', 'also', 'just', 'only', 'this', 'that'
        }

        # self.lock = threading.Lock()  # Khóa luồng tránh quá tải API


    def filter_vocabulary(self, processed_data):
        final_vocab = {}

        for item in processed_data:
            lemma = item['lemma']
            pos = item['pos']
            
            if pos in self.excluded_pos or lemma in self.months or lemma in self.forbidden_lemmas:
                continue
                
            # Loại bỏ các từ quá ngắn hoặc chứa ký tự đặc biệt (rác OCR)
            if len(lemma) < 2 or not all(c.isalpha() or c.isspace() or c == '-' for c in lemma):
                continue

            # Lọc trùng theo Lemma
            if lemma not in final_vocab:
                final_vocab[lemma] = item

                
        try:
            f_words = os.path.join(project_root, 'output', 'filtered_words.txt')
            with open(f_words, "w", encoding="utf-8") as f:
                for lemma in final_vocab.keys():
                    f.write(lemma + "\n")

        except Exception as e:
            print(f"Lỗi khi ghi file: {e}")

        return list(final_vocab.values())
    


    # def dict_lookup(self, word):
    #     """Gọi API từ điển để lấy thông tin"""
    #     fword = word.replace(" ", "%20")  # Encode space for URL
    #     url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{fword}"


    #     with self.lock:  # Đảm bảo chỉ một luồng gọi API tại một thời điểm
    #         try:
    #             response = requests.get(url, timeout=5)

    #             time.sleep(random.uniform(0.5, 1))  # Nghỉ nửa giây giữa các lần gọi để tránh quá tải API miễn phí

    #             if response.status_code == 200:
    #                 data = response.json()[0]
                    
    #                 # Trích xuất thông tin
    #                 phonetic = data.get('phonetic', 'N/A')
    #                 meanings = data.get('meanings', [])
    #                 definition_en = meanings[0]['definitions'][0].get('definition', 'N/A') if meanings else 'N/A'
    #                 example = meanings[0]['definitions'][0].get('example', 'N/A') if meanings else 'N/A'
    #                 # audio = ""
    #                 # for p in data.get('phonetics', []):
    #                 #     if p.get('audio'):
    #                 #         audio = p['audio']
    #                 #         break
                    
    #                 return {
    #                     "phonetic": phonetic,
    #                     "definition_en": definition_en,
    #                     "example": example,
    #                     # "audio_url": audio
    #                 }
                
    #             elif response.status_code == 429:
    #                 print(f"⚠️ API Dictionary bị quá tải (Rate Limit).")
    #                 time.sleep(5)  # Nghỉ 5 giây nếu bị rate limit
                
    #             return None
    #         except:
    #             return None
        


    def estimate_tokens(self, prompt, word_items):
        """Kiểm tra số lượng token của một batch trước khi gửi"""
        prompt = f"Analyze these words: {word_items}"
        # Sử dụng hàm count_tokens của thư viện google-genai
        response = client.models.count_tokens(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.total_tokens
    




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

        Return ONLY a JSON list of objects.
        
        Data: {word_items}
        """


        response = client.models.count_tokens(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        print(f"Estimated tokens: {response.total_tokens}")

        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
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



    def process_in_batches_gemini(self, processed_data, batch_size=12, output_file="../output/word_results.json"):
        """ Workflow: clean vocab -> batch -> call API """

        print(f"--- Đang lọc dữ liệu thô ({len(processed_data)} items)... ---")
        vocab_list = self.filter_vocabulary(processed_data)
        print(f"Hoàn thành! Có {len(vocab_list)} từ cần tra")


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

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)

            print(f"✅ Đã lưu tạm thời {len(final_results)} từ vào {output_file}")
            
            # Nghỉ dựa trên RPM (15 RPM ~ 4 giây mỗi request là an toàn tuyệt đối)
            time.sleep(4) 
            
        return final_results



    # def process_in_batches_dict(self, processed_data, output_file="../output/word_results.json"):
    #     """ Workflow: clean vocab -> dictionary """

    #     print(f"--- Đang lọc dữ liệu thô ({len(processed_data)} items)... ---")
    #     vocab_list = self.filter_vocabulary(processed_data)
    #     print(f"Hoàn thành! Có {len(vocab_list)} từ cần tra")

    #     final_results = []

    #     for item in vocab_list:
    #         word = item['lemma']
    #         print(f"🔍 Đang tra từ điển: {word}...")


    #         dict_info = self.dict_lookup(word)

    #         if dict_info:
    #             item.update(dict_info)
    #             final_results.append(item)

    #             with open(output_file, 'w', encoding='utf-8') as f:
    #                 json.dump(final_results, f, ensure_ascii=False, indent=4)

    #             time.sleep(1)  # Nghỉ 1 giây giữa các lần gọi để tránh quá tải API miễn phí

    #     return final_results




    # def process_dict_api_parallel(self, processed_data, max_workers=3 , output_file="../output/word_results.json"):
    #     print(f"--- Đang lọc dữ liệu thô ({len(processed_data)} items)... ---")
    #     vocab_list = self.filter_vocabulary(processed_data)
    #     print(f"Hoàn thành! Có {len(vocab_list)} từ cần tra")

    #     final_results = []

    #     with ThreadPoolExecutor(max_workers=max_workers) as executor:
    #         future_to_item = {executor.submit(self.dict_lookup, item['lemma']): item for item in vocab_list}

    #         for future in as_completed(future_to_item):
    #             org_item = future_to_item[future]
    #             word = org_item['lemma']

    #             try:
    #                 dict_info = future.result()
    #                 if dict_info:
    #                     org_item.update(dict_info)
    #                     final_results.append(org_item)

    #                 else:
    #                     print(f"❌ Không tìm thấy: {word}")


    #             except Exception as exc:
    #                 print(f"⚠️ Lỗi khi tra từ '{word}': {exc}")

    #     try: 
    #         with open(output_file, 'w', encoding='utf-8') as f:
    #             json.dump(final_results, f, ensure_ascii=False, indent=4)
    #         print(f"--- Đã lưu {len(final_results)} từ vào {output_file} ---")

    #     except Exception as e:
    #         print(f"Lỗi khi ghi file JSON: {e}")

    #     return final_results


            
    



# if __name__ == "__main__":
#     # 1. Giả lập dữ liệu thô từ Text_Processor
#     sample_data = [
#         {"lemma": "machine learning", "pos": "NOUN", "context": "Machine learning is great.", "page": 1},
#         {"lemma": "the", "pos": "DET", "context": "The book is here.", "page": 1},
#         {"lemma": "in", "pos": "ADP", "context": "It is in the box.", "page": 1},
#         {"lemma": "algorithm", "pos": "NOUN", "context": "Use this algorithm.", "page": 1},
#         {"lemma": "2026", "pos": "NUM", "context": "In 2026 we fly.", "page": 1},
#         {"lemma": "january", "pos": "NOUN", "context": "It is January.", "page": 1},
#         {"lemma": "he", "pos": "PRON", "context": "He is a student.", "page": 1},
#         {"lemma": "analyze", "pos": "VERB", "context": "We need to analyze data.", "page": 1},
#         {"lemma": "state-of-the-art", "pos": "ADJ", "context": "We want state-of-the-art technology.", "page": 1}
#     ]

#     filter_tool = Word_Filter()

#     # TEST BƯỚC 1: Kiểm tra bộ lọc ngữ pháp (Chưa gọi AI)
#     print("--- TEST: Lọc ngữ pháp ---")
#     clean_list = filter_tool.filter_vocabulary(sample_data)
    
#     print(f"Tổng số từ ban đầu: {len(sample_data)}")
#     print(f"Số từ sau khi lọc: {len(clean_list)}")
#     for item in clean_list:
#         print(f"Giữ lại: {item['lemma']} ({item['pos']})")

#     result = filter_tool.process_in_batches(clean_list)
#     print(result)

