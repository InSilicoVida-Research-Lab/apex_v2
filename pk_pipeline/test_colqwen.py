from pdf2image import convert_from_path
import torch
from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor

def main():
    images = convert_from_path("test_data/Loccisano 2013.pdf", dpi=150)
        
    model_name = "vidore/colqwen2.5-v0.2"
    model = ColQwen2_5.from_pretrained(model_name, torch_dtype=torch.float16, device_map="cuda").eval()
    processor = ColQwen2_5_Processor.from_pretrained(model_name)
    
    with torch.no_grad():
        batch_images = processor.process_images(images).to(model.device)
        image_embeddings = model(**batch_images)
        
        batch_queries = processor.process_queries(["Pharmacokinetic parameters table", "References Bibliography"]).to(model.device)
        query_embeddings = model(**batch_queries)
        
        pos_scores = processor.score_multi_vector(query_embeddings[0:1], image_embeddings)[0]
        neg_scores = processor.score_multi_vector(query_embeddings[1:2], image_embeddings)[0]
        
    for i in range(len(images)):
        print(f"Page {i+1}: POS={pos_scores[i].item():.2f}, NEG={neg_scores[i].item():.2f}")
        
if __name__ == "__main__":
    main()
