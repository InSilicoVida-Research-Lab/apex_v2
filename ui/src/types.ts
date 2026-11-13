export interface DocumentSummary {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  journal?: string;
  parameter_count: number;
  has_pdf: boolean;
  has_markdown: boolean;
  has_tan: boolean;
  tan_score?: {
    total: number;
    supported: number;
    fit_for_purpose: string;
  };
  model_type: string;
  compounds: string[];
  species: string[];
}

export interface QuantitativeData {
  value_text?: string;
  value?: number | null;
  start_value?: number | null;
  end_value?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  variance?: number | null;
  variance_type?: string | null;
  unit?: string | null;
  unit_original?: string | null;
  unit_standardized?: string | null;
  uncertainty?: {
    type?: string;
    lower?: number;
    upper?: number;
    absolute?: number;
    raw_text?: string;
  } | null;
}

export interface BiologicalContext {
  species?: string | null;
  compound?: string | null;
  organ?: string | null;
  tissue?: string | null;
  life_stage?: string | null;
  population?: string | null;
  strain?: string | null;
  sex?: string | null;
  formulation?: string | string[] | null;
}

export interface ParameterProvenance {
  source_page?: number | null;
  source_table?: string | null;
  source_location?: string | null;
  source_section?: string | null;
  source_quote?: string | null;
  confidence?: 'high' | 'medium' | 'low' | string | null;
  confidence_basis?: string | null;
  cell_id?: string | null;
  row_id?: string | null;
  column_id?: string | null;
  row_path?: string[] | null;
  column_path?: string[] | null;
  status?: string | null;
  reference?: string | null;
  derivation?: {
    method?: string;
    source_species?: string;
    source_reference?: string;
  } | string | null;
  reviewed_by_human?: boolean;
  curator_notes?: string;
}

export interface ExtractedParameter {
  parameter_id: string;
  parameter_name?: string;
  parameter_name_original?: string;
  parameter_name_standardized?: string;
  symbol_original?: string;
  symbol_standardized?: string;
  parameter_class?: string;
  parameter_subclass?: string;
  context?: BiologicalContext;
  quantitative_data?: QuantitativeData;
  provenance?: ParameterProvenance;
}

export interface ParameterFlag {
  param_index: number;
  param_name: string;
  severity: 'error' | 'warning' | string;
  rule: string;
  message: string;
  suggested_fix?: string;
}

export interface VerificationReport {
  tier: number;
  elapsed_ms: number;
  total_parameters: number;
  parameters_with_flags: number;
  total_flags: number;
  error_count: number;
  warning_count: number;
  clean: boolean;
  flags: ParameterFlag[];
  summary: string;
}

export interface EvidenceReference {
  source_page?: number | null;
  source_section?: string | null;
  source_location?: string | null;
  source_quote?: string | null;
}

export interface TanQuestionnaireItem {
  item_id: string;
  section: string;
  question: string;
  allowed_source_sections?: string[];
  routing_rule?: string | null;
  response: 'yes' | 'partially' | 'no' | 'not_applicable' | 'i_cannot_answer' | string;
  details: string;
  structured_details?: Record<string, any>;
  evidence?: EvidenceReference[];
  confidence: 'high' | 'medium' | 'low' | string;
  confidence_basis?: string | null;
}

export interface TanPBPKAssessment {
  template_name: string;
  template_version: string;
  assessment_date?: string | null;
  reviewer?: string;
  pipeline_version?: string;
  model_identification?: {
    model_name?: string;
    target_compounds?: string[];
    authors?: string[];
    publication_year?: number;
    journal?: string;
  };
  assessment_scope?: string;
  items: TanQuestionnaireItem[];
  verification_summary?: Record<string, any>;
  overall_fit_for_purpose?: string;
  key_gaps?: string[];
  reviewer_notes?: string[];
}

export interface ExtractedDocument {
  page_metadata?: {
    title?: string;
    authors?: string[];
    year?: number;
    journal?: string;
    doi?: string;
  };
  model_classification?: {
    model_type?: string;
    confidence?: number;
    evidence_quote?: string;
  };
  model_context?: {
    stated_purpose?: string;
    species?: string[];
    compounds?: string[];
    life_stages?: string[];
    target_populations?: string[];
  };
  model_structure?: {
    model_type?: string;
    equations_provided?: string;
    compartments?: string[];
    connections?: Array<{
      source: string;
      target: string;
      direction: string;
      type?: string;
    }>;
  };
  model_parameters?: ExtractedParameter[];
  table_evidence?: any[];
  dosing?: any[];
  observed_data?: any[];
  simulated_data?: any[];
  software?: {
    name?: string;
    version?: string;
    solver?: string;
    optimization_method?: string;
  };
  tan_assessment?: TanPBPKAssessment;
}

