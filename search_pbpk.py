import requests

query = "PBPK OR \"physiologically based pharmacokinetic\""
url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
params = {
    "query": f'({query}) AND (OPEN_ACCESS:y)',
    "format": "json",
    "resultType": "core",
    "pageSize": 10
}
r = requests.get(url, params=params)
data = r.json()
count = 0
for result in data.get('resultList', {}).get('result', []):
    pmcid = result.get('pmcid')
    doi = result.get('doi')
    title = result.get('title')
    if pmcid and doi:
        print(f"- **{title}**\n  - DOI: {doi}\n  - PMCID: {pmcid}")
        count += 1
    if count >= 5:
        break
