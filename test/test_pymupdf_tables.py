import pymupdf
doc = pymupdf.open("pk_pipeline/test_data/s12249-023-02680-y.pdf")
page = doc[5] # Page 6
tables = page.find_tables()
print("Tables found on Page 6:", len(tables.tables))
