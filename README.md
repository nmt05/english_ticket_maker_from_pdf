# 📚 English Vocabulary Extractor (CEFR Filter)

Một công cụ hỗ trợ học ngoại ngữ bằng cách trích xuất từ vựng từ file PDF (sách, tài liệu scan) và phân loại chúng theo khung tham chiếu trình độ Châu Âu (CEFR: A1, B1, B2, C1...).

## 🚀 Tính năng chính
- **OCR Engine:** Chuyển đổi các trang PDF (kể cả dạng ảnh scan) thành văn bản thô.
- **NLP Processing:** Làm sạch dữ liệu, tách từ và đưa từ về dạng nguyên thể (Lemmatization).
- **Smart Filtering:** Đối soát với bộ dữ liệu Oxford 5000 để phân loại trình độ từ vựng.
- **Export:** Xuất báo cáo từ vựng theo cấp độ để người dùng dễ dàng theo dõi.

## 🛠 Tech Stack
- **Language:** Python 3.x
- **OCR:** [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- **PDF Rendering:** [Poppler](https://poppler.freedesktop.org/)
- **Libraries:** - `pytesseract`: Wrapper cho Tesseract.
  - `pdf2image`: Chuyển PDF thành Image stream.
  - `spaCy`: Xử lý ngôn ngữ tự nhiên (Natural Language Processing).
  - `pandas`: Quản lý và lọc dữ liệu từ vựng.

## 📂 Cấu trúc thư mục (Project Structure)
```text
english_ticket_maker_from_pdf/
├── data/
│   ├── raw/                # Chứa file PDF đầu vào
│   └── words/              # Chứa file oxford_5000.json (Database)
├── src/                    # Mã nguồn chính
│   ├── ocr_engine.py       # Xử lý PDF -> Text
│   ├── text_processor.py   # Làm sạch & Lemmatization
│   └── filter_engine.py    # Phân loại cấp độ CEFR
├── output/                 # Kết quả trích xuất (.txt, .csv)
├── main.py                 # Entry point của ứng dụng
└── requirements.txt        # Danh sách thư viện cần cài đặt