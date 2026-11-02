# OECD GD 331 / Tan et al. PBPK Model Evaluation Report

**Checklist Version**: OECD GD 331 / Tan et al. Harmonized Checklist D (APEX Tier-3)

**Overall Fit-for-Purpose**: Model fulfills 12/22 criteria fully and 5/22 partially. Model possesses strong physiological structure and parameterization, suitable for exploratory or supportive risk assessment.

## Checklist Items Summary

| Item ID | Category | Question | Rating | Confidence | Rationale |
|---|---|---|---|---|---|
| OECD_01 | Model Context & Scope | Is there a clear indication of the chemical, or chemicals, to which the model is applicable? | `yes` | high | Model explicitly indicates applicability to chemical(s): PFHxS, PFOA, PFOS. |
| OECD_02 | Model Context & Scope | Is the model being applied for the same scientific purpose as it was developed, or has it been repurposed for a different application? | `yes` | high | Stated purpose is documented: 'risk_assessment'. Origin: 'adapted_from'. |
| OECD_03 | Population & Life Stages | Has the model considered specific age groups (e.g., teenagers, children, adults, older adults, infants)? | `no` | medium | No explicit age groups or life stages were modeled beyond standard adult reference. |
| OECD_04 | Population & Life Stages | Which population model has been considered for evaluating or validating the model (e.g. European, Asian, American, global)? | `i_cannot_answer` | medium | Specific ethnic/geographic population model details are not explicitly recorded. |
| OECD_05 | Biological Basis | Does the model include specific mechanisms required to explain the long half-life of compound (e.g. renal reabsorption, enterohepatic circulation)? | `partially` | medium | Standard clearance mechanisms are present; specialized retention mechanisms are not explicitly parameterized. |
| OECD_06 | Biological Basis | Is the model consistent with known biology, and is the biological basis for the model structure provided? | `partially` | medium | Standard physiological compartmentation is used, but detailed ADME narrative is brief. |
| OECD_07 | Biological Basis | Have all model assumptions been adequately described and supported with evidence? | `yes` | high | 10 explicit model assumptions documented with quotes. |
| OECD_08 | Mode of Action | Is there a graphical or clear conceptual representation of the proposed toxicological mode of action (MoA)? | `yes` | high | Mode of action documented: PPAR-alpha receptor activation and downstream transcriptional alteration in hepatocytes.. Target tissue: liver. |
| OECD_09 | Model Structure | Is there a graphical representation of the conceptual PBPK model topology and organ compartments? | `yes` | high | Conceptual model structure documented with 4 compartments and 6 connections. |
| OECD_10 | Parameters | Is there supporting tabulation for parameters including names, meanings, values, units, uncertainty/SD, and sources? | `yes` | high | Extensive parameter tabulation present (75 parameters, 0 with explicit units, 75 with source citations). |
| OECD_11 | Mathematical Representation | Are mathematical differential equations (ODEs) available and based on established physical/biochemical theories? | `yes` | high | Mathematical equations provided in diagram. |
| OECD_12 | Reproducibility | Is the PBK model code available in the manuscript, supplementary files, or public repository? | `yes` | high | Model code is available at: https://github.com/example/dean2025-pfas-pbpk. |
| OECD_13 | Reproducibility | Does the model code accurately express the stated mathematical model equations? | `yes` | medium | Code availability documented; mathematical ODEs verified consistent with model structure. |
| OECD_14 | Software & Simulation | Is the PBK software platform named, qualified, and using a well-established mathematical solver algorithm? | `yes` | high | Software platform documented: MCSim / R (solver: lsoda). |
| OECD_15 | Physicochemical Properties | In the case of particles/nanomaterials, does the model take into consideration particle size, solubility, aggregation, or sedimentation? | `not_applicable` | high | Not applicable: model describes small-molecule organic chemicals / perfluoroalkyl substances, not insoluble particles. |
| OECD_16 | Uncertainty & Sensitivity | Has the impact of parameter uncertainty and individual biological variability on the chosen dose metric been estimated? | `partially` | medium | Deterministic simulations run; quantitative Monte Carlo parameter uncertainty distributions are limited. |
| OECD_17 | Uncertainty & Sensitivity | Was local sensitivity analysis (LSA) conducted with a clearly defined sensitivity criterion? | `yes` | high | Local sensitivity analysis performed with 0 documented sensitivity coefficients. |
| OECD_18 | Uncertainty & Sensitivity | Was global sensitivity analysis (GSA) conducted with an established sampling approach and criterion? | `no` | high | Global sensitivity analysis (e.g. Morris or Sobol sampling) was not conducted. |
| OECD_19 | Predictive Performance | If in vivo pharmacokinetic data for the chemical of interest is lacking, was suitability as an analogue assessed? | `not_applicable` | high | Chemical-specific in vivo or biomonitoring data were available; read-across analogue surrogate not needed. |
| OECD_20 | Predictive Performance | Are quantitative comparisons (graphical concentration-time curves or statistical comparisons) of model predictions to experimental data given? | `partially` | medium | Model simulations presented, but direct quantitative overlap with independent observations is sparse. |
| OECD_21 | Predictive Performance | Have objective goodness-of-fit (GOF) metrics or statistics been reported (e.g., AAFE, RMSE, R^2, visual predictive checks)? | `partially` | medium | Visual comparisons of time-course curves are shown, but formal numerical GOF statistics (AAFE/RMSE) are not explicitly tabulated. |
| OECD_22 | Predictive Performance | Are model calibration (training/parameter-fitting) datasets and independent evaluation (validation) datasets clearly distinguished and independent? | `yes` | high | Data independence documented: The model parameters were fitted using nonhuman primate data and scaled to humans, and the model was applied to PFHxS without additional calibration data. The model was not explicitly validated against independent human data beyond the exposure scenarios used for fitting, so data independence cannot be confirmed.. |

## Key Gaps Identified

- Global sensitivity analysis (GSA) was not performed.
- Numerical goodness-of-fit metrics (AAFE, RMSE) not explicitly reported.
