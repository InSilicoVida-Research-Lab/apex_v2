from pk_pipeline.main import _parameters_from_table_evidence
from pk_pipeline.schemas import ExtractedParameter


def test_recovers_parameter_cells_but_skips_outcome_tables():
    parameter_table = {
        "evidence_status": "success",
        "table_id": "Table 1",
        "title": "TK model parameters",
        "subject_compounds": ["PFOS"],
        "columns": [
            {"column_id": "c1", "path": ["Species"]},
            {"column_id": "c2", "path": ["Variable"]},
            {"column_id": "c3", "path": ["Name"]},
            {"column_id": "c4", "path": ["Mean (95% CI)", "PFOS"]},
            {"column_id": "c5", "path": ["Source"]},
        ],
        "rows": [
            {"row_id": "r1", "path": ["Human", "Body weight (kg)", "BW"]},
        ],
        "cells": [
            {"cell_id": "cell_r1_c2", "row_id": "r1", "column_id": "c2", "text": "Body weight (kg)"},
            {"cell_id": "cell_r1_c3", "row_id": "r1", "column_id": "c3", "text": "BW"},
            {"cell_id": "cell_r1_c4", "row_id": "r1", "column_id": "c4", "text": "70 (65, 75)", "numeric_value": 70.0},
            {"cell_id": "cell_r1_c5", "row_id": "r1", "column_id": "c5", "text": "Optimized"},
        ],
    }
    outcome_table = {
        "evidence_status": "success",
        "table_id": "Table 2",
        "columns": [
            {"column_id": "c1", "path": ["Outcome"]},
            {"column_id": "c2", "path": ["Mean value"]},
        ],
        "rows": [{"row_id": "r1", "path": ["Cholesterol"]}],
        "cells": [{"cell_id": "cell_r1_c2", "row_id": "r1", "column_id": "c2", "text": "1.2", "numeric_value": 1.2}],
    }

    recovered = _parameters_from_table_evidence([parameter_table, outcome_table])

    assert len(recovered) == 1
    parameter = ExtractedParameter.model_validate(recovered[0])
    assert parameter.parameter_name_original == "Body weight (kg)"
    assert parameter.symbol_original == "BW"
    assert parameter.context.species == "human"
    assert parameter.context.compound == "PFOS"
    assert parameter.quantitative_data.value == 70.0
    assert parameter.quantitative_data.uncertainty.lower == 65.0
    assert parameter.quantitative_data.uncertainty.upper == 75.0
    assert parameter.provenance.source_table == "Table 1"
    assert parameter.provenance.status == "fitted"
    assert parameter.needs_review is True
