import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from pk_pipeline.ml_services import WeVisDocParser

def test_wevisdoc_parser_init():
    parser = WeVisDocParser()
    assert parser.model_id == "Tencent/WeVisDoc-4B"
    assert parser.is_loaded is False

def test_wevisdoc_parser_prompts():
    parser = WeVisDocParser()
    assert "HTML format" in parser.DEFAULT_SYSTEM_PROMPT
    assert "rowspan" in parser.DEFAULT_SYSTEM_PROMPT
    assert "Markdown" in parser.DEFAULT_USER_PROMPT

if __name__ == "__main__":
    test_wevisdoc_parser_init()
    test_wevisdoc_parser_prompts()
    print("All WeVisDoc unit tests passed successfully!")
