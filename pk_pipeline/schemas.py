from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractionRequest(BaseModel):
    pdf_path: str
    target_compounds: Optional[List[str]] = None

class PageMetadata(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None

class ModelClassification(BaseModel):
    model_type: str = Field(description="Must be 'pbpk', 'simple_empirical_compartmental', or 'not_applicable'")
    evidence_quote: Optional[str] = None

class Connection(BaseModel):
    from_comp: str = Field(alias="from")
    to_comp: str = Field(alias="to")

class Structure(BaseModel):
    compartments: Optional[List[str]] = None
    connections: Optional[List[Connection]] = None
    source_location: Optional[str] = None

class Parameter(BaseModel):
    symbol: str
    full_name: Optional[str] = None
    value: str
    value_qualifier: Optional[str] = None
    unit: Optional[str] = None
    unit_inherited_from_group_header: Optional[bool] = None
    compound: Optional[str] = None
    species: Optional[str] = None
    population: Optional[str] = None
    source_location: str
    source_quote: str
    confidence: str = Field(description="Must be 'high', 'medium', or 'low'")

class ExtractedPage(BaseModel):
    page_metadata: PageMetadata
    model_classification: ModelClassification
    structure: Optional[Structure] = None
    parameters: List[Parameter]
