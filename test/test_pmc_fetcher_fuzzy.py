import pytest
from unittest.mock import patch, MagicMock
from pk_pipeline.ingestion.pmc_fetcher import try_semantic_scholar, try_europe_pmc

def test_semantic_scholar_rejects_wrong_title_match():
    """
    Test that try_semantic_scholar rejects a paper if the returned title 
    does not closely match the requested title.
    """
    requested_title = "A physiologically based pharmacokinetic model for PFOA in humans"
    wrong_returned_title = "A pharmacokinetic model for PFOS in rats" # Different chemical and species

    # Mock the requests.get response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{
            "title": wrong_returned_title,
            "openAccessPdf": {"url": "http://fake-pdf.com/paper.pdf"},
            "externalIds": {"DOI": "10.1234/wrong"}
        }]
    }

    with patch("requests.get", return_value=mock_response):
        pdf_path = try_semantic_scholar(title=requested_title)
        
        # Currently the code blindly takes the first result.
        # This test ensures we assert it returns None if the title doesn't match!
        assert pdf_path is None, "Semantic Scholar downloaded a paper with a mismatched title!"

def test_europe_pmc_rejects_wrong_title_match():
    """
    Test that try_europe_pmc rejects a paper if the returned title 
    does not closely match the requested title.
    """
    requested_title = "A physiologically based pharmacokinetic model for PFOA in humans"
    wrong_returned_title = "A pharmacokinetic model for PFOS in rats"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "resultList": {
            "result": [{
                "title": wrong_returned_title,
                "pmcid": "PMC9999999",
                "hasTextMinedTerms": "Y"
            }]
        }
    }

    with patch("requests.get", return_value=mock_response):
        # We also need to patch the actual XML download since we expect it to fail early
        with patch("pk_pipeline.ingestion.pmc_fetcher.fetch_pmc_xml") as mock_xml:
            xml_path = try_europe_pmc(title=requested_title)
            # The function should realize the title doesn't match and return None
            # instead of returning a valid path
            assert xml_path is None, "Europe PMC downloaded a paper with a mismatched title!"
