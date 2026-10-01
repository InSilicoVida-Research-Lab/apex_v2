import argparse
import json
import os
import sys

from pk_pipeline.compartmental_assembler import assemble_compartmental_model
from pk_pipeline.simulator import simulate_antimony
from pk_pipeline.figure_digitizer import digitize_figure
from pk_pipeline.fit_reporter import generate_report

def run_replication(pdf_path, compound=None):
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    # Default output dir from main.py is "output"
    out_dir = os.path.join(os.path.dirname(os.path.dirname(pdf_path)), "output") if "test_data" in pdf_path else os.path.join(os.path.dirname(pdf_path), "output")
    # For now, hardcode project root output/ just in case
    out_dir = os.path.join("/home/gautam/Desktop/project/apex_v2/output")
    json_path = os.path.join(out_dir, f"{pdf_stem}.json")
    
    if not os.path.exists(json_path):
        print(f"Error: Could not find extraction output at {json_path}")
        print("Please run the extraction pipeline on this PDF first.")
        sys.exit(1)
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    params = data.get("parameters", [])
    if compound:
        # Filter for Physiological parameters (compound=None or 'Physiological') and the specific compound
        filtered_params = []
        for p in params:
            c = p.get("context", {}).get("compound")
            if not c or c.lower() == "physiological" or c.lower() == compound.lower():
                filtered_params.append(p)
        params = filtered_params
        
    dosing = data.get("dosing", [])
    
    print("--- 1. Assembling Model ---")
    antimony_model = assemble_compartmental_model(params, dosing)
    print(antimony_model)
    print("---------------------------\n")
    
    print("--- 2. Simulating ---")
    duration = 24.0
    if dosing and dosing[0].get("duration_h"):
        duration = dosing[0]["duration_h"]
        
    try:
        df = simulate_antimony(antimony_model, duration_h=duration)
        print(df.head(10))
        print("...")
        print(df.tail(5))
        
        # Save output
        out_csv = os.path.join(out_dir, f"{pdf_stem}_simulation_{compound or 'all'}.csv")
        df.to_csv(out_csv, index=False)
        print(f"\nSimulation saved to {out_csv}")
        
        print("\n--- 3. Digitizing Figure (Phase 4) ---")
        # Attempt to find a figure to digitize
        # Note: images are usually placed by MinerU in <pdf_dir>/<pdf_stem>/auto/images/
        pdf_dir = os.path.dirname(pdf_path)
        img_dir = os.path.join(pdf_dir, pdf_stem, "auto", "images")
        fig_candidates = [f for f in os.listdir(img_dir) if f.endswith(".jpg") or f.endswith(".png")] if os.path.exists(img_dir) else []
        
        digitized_json = os.path.join(out_dir, f"{pdf_stem}_digitized_{compound or 'all'}.json")
        
        if fig_candidates:
            fig_path = os.path.join(img_dir, fig_candidates[0])
            import asyncio
            print(f"Digitizing {fig_path}...")
            # For this to work, the sglang server needs to be running.
            try:
                loop = asyncio.get_event_loop()
                extracted_data = loop.run_until_complete(digitize_figure(fig_path))
                with open(digitized_json, "w") as f:
                    json.dump(extracted_data, f, indent=2)
                print(f"Saved digitized data to {digitized_json}")
            except Exception as e:
                print(f"Failed to digitize figure: {e}")
        else:
            print("No figure images found to digitize.")
            
        print("\n--- 4. Fit Comparison & Report (Phase 5) ---")
        if os.path.exists(digitized_json):
            out_prefix = os.path.join(out_dir, f"report_{compound or 'all'}")
            report = generate_report(out_csv, digitized_json, out_prefix, compound or "")
            print(json.dumps(report, indent=2))
        else:
            print("No digitized data available for fit comparison.")
            
    except Exception as e:
        print(f"Simulation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replicate a paper using extracted PK parameters.")
    parser.add_argument("pdf_path", help="Path to the source PDF")
    parser.add_argument("--compound", default=None, help="Target compound to simulate")
    args = parser.parse_args()
    
    run_replication(args.pdf_path, args.compound)
