import pdfplumber

def check_tables():
    with pdfplumber.open("test_data/1-s2.0-S0378427423002060-main.pdf") as pdf:
        for i, page in enumerate(pdf.pages):
            words = page.extract_words()
            table_words = [w for w in words if "Table" in w['text']]
            if table_words:
                print(f"Page {i+1}: Found {len(table_words)} 'Table' words.")

if __name__ == "__main__":
    check_tables()
