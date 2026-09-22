import requests
import os

pmcids = [
    "PMC13461864",
    "PMC13569985",
    "PMC13545016",
    "PMC13388495",
    "PMC13462044"
]

out_dir = "pk_pipeline/test_data"
os.makedirs(out_dir, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}

for pmcid in pmcids:
    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
    print(f"Downloading {pmcid}...")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("application/pdf"):
            with open(os.path.join(out_dir, f"{pmcid}.pdf"), "wb") as f:
                f.write(r.content)
            print(f"Saved {pmcid}.pdf")
        else:
            print(f"Failed for {pmcid}, status={r.status_code}, content_type={r.headers.get('Content-Type')}")
    except Exception as e:
        print(f"Error for {pmcid}: {e}")
