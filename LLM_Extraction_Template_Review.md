# LLM Extraction & Evaluation Template

This document outlines the **revised extraction and evaluation specification** for the LLM pipeline. 

*Core Principles for the LLM:*
*   **Hierarchy:** Paper → Model(s) → Species/Population Variant → Parameter Set → Dosing Scenario → Dataset.
*   **Null Policy:** Fields must explicitly use `not reported`, `not applicable`, or `unclear` instead of null or invented placeholders.
*   **Evidence Basis:** Every field requires a type/enum, a direct evidence quote, source location (page/table), and an extraction confidence score.
*   **Extraction vs. Evaluation:** The extraction pass captures what the authors *stated*; a separate evaluation pass captures derived judgments based on the extracted evidence.

---

## 1. Chemical Identity & Physicochemical Properties
*   [ ] **Compound Name & Identifiers:** Primary name, CAS number, synonyms, and identifiers for any modeled metabolites.
*   [ ] **Physicochemical Parameters (Extracted):** Molecular weight (MW), logKow/logP, pKa, vapor pressure (VP), solubility, etc.

## 2. Publication Metadata & Reproducibility
*   [ ] **Metadata:** Title, Authors, Journal, Year, DOI.
*   [ ] **Supplementary Info (SI):** Is SI available, and does it contain equations, code, or parameters?
*   [ ] **Implementation:** Software used (e.g., acslX, Berkeley Madonna, MATLAB, R, PK-Sim, Simcyp, GastroPlus, MCSim).
*   [ ] **Code Availability:** Is the model code provided in the text, SI, or a public repository?

## 3. Model Scope & Context
*   [ ] **Model Origin/Lineage:** Is this model `new`, `adapted from [citation]` (with notes on what changed), or `reused unchanged`?
*   [ ] **Model Classification:** PBPK, semi-PBPK, or simple empirical compartmental.
*   [ ] **Species & Population:** All species, strains, and life stages/demographics modeled.
*   [ ] **Context of Use (COU) / Stated Purpose:** The authors' stated purpose for the model (e.g., risk assessment, extrapolation, hypothesis testing). If not stated, mark `not reported`.
*   [ ] **Extrapolations Performed:** Did the model perform extrapolations across species, route, dose, life stage, or duration?
*   [ ] **Dose Metric:** What metric does the model compute to link to toxicity? (e.g., liver AUC of metabolite, peak plasma concentration of parent).

## 4. Biological Basis & Assumptions
*   [ ] **ADME Determinants:** What physiological/physicochemical factors drive the kinetics? (e.g., high lipophilicity, saturable metabolism, protein binding).
*   [ ] **MoA Linkage:** Is the model structure linked to the Mode of Action (MoA) / toxicodynamics? (Parent vs. metabolite, specific target tissues).
*   [ ] **Stated Assumptions:** Explicit list of assumptions stated by the authors with direct quotes.
*   [ ] **Specialized Mechanisms:** Mechanisms explaining unusual kinetics (e.g., renal reabsorption, enterohepatic recirculation).

## 5. Model Structure & Equations
*   [ ] **Compartments & Type:** List of compartments and their type (e.g., flow-limited vs. permeability-limited).
*   [ ] **Absorption Submodels:** How is absorption modeled? (e.g., gut transit, skin penetration).
*   [ ] **Elimination Routes:** Specific routes of excretion and metabolic clearance (e.g., hepatic metabolic clearance, extrahepatic, renal excretion, biliary, exhalation, milk/hair). Include flags for enterohepatic recirculation.
*   [ ] **Scaling Rules & Equations:** Are ODEs provided? Are allometric scaling rules defined (e.g., $QC = QCC \cdot BW^{0.75}$, $V = VC \cdot BW$)? What is the reference body weight?
*   [ ] **Graphical Representation:** Reference to the figure showing the conceptual model.

## 6. Metabolism
*   [ ] **Pathways & Enzymes:** Specific enzymes (e.g., CYP450, CYP1A2, glucuronidation) per pathway.
*   [ ] **Location:** Specific tissues/compartments where metabolism occurs.
*   [ ] **Kinetics Type (Per Pathway):** clearance-based (CLint with IVIVE scaling), Michaelis-Menten (with/without inhibition), Hill, mixed.
*   [ ] **Metabolite Linkage:** Are metabolites actively tracked in the model, or treated as sink compartments?
*   [ ] **IVIVE:** Was In Vitro to In Vivo Extrapolation used for metabolic parameters?

## 7. Parameters (The Core Data)
*   [ ] **Name & Symbol:** Descriptive name (e.g., "Cardiac output allometric constant") and printed symbol (e.g., "QCC").
*   [ ] **Value, Bounds, & Distribution:** Numerical value, bounds, standard deviation, distribution type (CV, lognormal) if Monte Carlo was used.
*   [ ] **Scaling Status:** Are the values scaled or unscaled?
*   [ ] **Unit:** The unit exactly as printed.
*   [ ] **Parameter Taxonomy:** Physiological, Physicochemical, Biochemical (Vmax, Km, CLint, fu, transporters), Exposure, or Empirical/Fitted.
*   [ ] **Context:** Species, Compound/Metabolite, Life Stage.
*   [ ] **Provenance Enum:** `measured here`, `literature (cite)`, `in vitro + IVIVE`, `predicted/QSAR`, `fitted (to [dataset])`, or `assumed/default`.

## 8. Dosing & Exposure Scenarios
*(Linked to specific datasets)*
*   [ ] **Compound/Vehicle:** Chemical dosed and the vehicle used.
*   [ ] **Animal Group:** n, sex, strain, body weight.
*   [ ] **Scenario Details:** Route, duration, and exposure metrics (e.g., inhalation: ppm × h/day × days; dermal: area, dose, duration).

## 9. Datasets & Model Performance
*   [ ] **Dataset Types:** Differentiate between `calibration datasets` (used to fit parameters) and `independent evaluation datasets`.
*   [ ] **Performance Metrics:** Goodness-of-fit metrics reported (e.g., fold-error, % within 2-fold, $R^2$, AFE, RMSE).
*   [ ] **Visual Checks:** References to figures showing simulated vs. observed data.

## 10. Sensitivity, Uncertainty, & Variability
*   [ ] **Analysis Performed:** Was sensitivity/uncertainty/variability analysis performed?
*   [ ] **Methodology:** local vs. global, Monte Carlo, Bayesian MCMC.
*   [ ] **Key Findings:** Which parameters were most sensitive?

## 11. Limitations & Evaluator Judgments (Second Pass)
*This section contains derived evaluations and judgments based on the extracted evidence, including a rationale string for each.*
*   [ ] **Author-Stated Limitations:** What limitations did the authors explicitly note?
*   [ ] **Missing Standard Assumptions:** Which standard assumptions are necessary for the model but absent from the text?
*   [ ] **Data Independence:** Were the evaluation datasets truly independent of the calibration data?
*   [ ] **Repurposed Context:** If applied to a new context, is it appropriate?
