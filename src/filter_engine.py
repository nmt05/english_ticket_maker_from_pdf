import os



class Word_Filter:
    def __init__(self, blacklist_path="blacklist.txt"):
        self.blacklist = self._load_file(blacklist_path)
        # API URL: https://api.dictionaryapi.dev/api/v2/entries/en/
        self.api_url = "https://api.dictionaryapi.dev/api/v2/entries/en/"

    def _load_file(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return {line.strip().lower() for line in f if line.strip()}
        return set()

    def get_dictionary_info(self, word):
        """Gọi API để lấy phiên âm, nghĩa, và âm thanh"""
        try:
            response = requests.get(f"{self.api_url}{word}", timeout=5)
            if response.status_code == 200:
                data = response.json()[0]
                
                # Trích xuất thông tin
                phonetic = data.get('phonetic', 'N/A')
                meanings = data.get('meanings', [])
                definition = meanings[0]['definitions'][0].get('definition', 'N/A') if meanings else 'N/A'
                audio = ""
                for p in data.get('phonetics', []):
                    if p.get('audio'):
                        audio = p['audio']
                        break
                
                return {
                    "phonetic": phonetic,
                    "definition_en": definition,
                    "audio_url": audio
                }
        except:
            pass
        return None

    def filter_and_enrich(self, processed_data):
        final_vocab = {}
        
        for item in processed_data:
            lemma = item['lemma']
            
            # 1. Lọc cơ bản
            if (lemma in self.blacklist or len(lemma) <= 2 or not lemma.isalpha()):
                continue
            
            if lemma not in final_vocab:
                print(f"Đang tra từ điển cho từ: {lemma}...")
                dict_info = self.get_dictionary_info(lemma)
                
                if dict_info:
                    # Gộp dữ liệu từ TextProcessor và Dictionary
                    item.update(dict_info)
                    final_vocab[lemma] = item
                    
        return list(final_vocab.values())







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
WEB_GARBAGE = {
        "www", "http", "https", "com", "net", "org", "gov", "edu", "io", "co", "us", "uk", "ca", "de", "fr", "jp",
        "ebook","html", "htm", "php", "url", "href"
    }
seen_words = set()
def clean_and_filter_text(raw_text):
    doc = nlp(raw_text)
    filtered_words = []
    exclude_entities = ["PERSON", "GPE", "ORG", "LOC"]

    for token in doc:

        if token.ent_type_ in exclude_entities:
            continue
        word_lemma = token.lemma_.lower()
        clean_lemma = re.sub(r'[^a-zA-Z]', '', word_lemma)
        if clean_lemma:
            
            if clean_lemma in seen_words:
                continue
            if clean_lemma in COMMON_WORDS:
                continue
            length = len(clean_lemma)
            if length < 3 and clean_lemma not in SAFE_2_LETTER_WORDS and clean_lemma not in ["i", "a"]:
                continue
            if length > 1 and len(set(clean_lemma)) == 1:
                continue
            seen_words.add(clean_lemma)
            filtered_words.append(clean_lemma)
            
    return " ".join(filtered_words)