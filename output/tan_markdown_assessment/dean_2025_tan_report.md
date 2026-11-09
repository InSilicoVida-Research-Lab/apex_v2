# Tan et al. PBPK Reporting Assessment Report
**Template**: Tan et al. PBPK Reporting Template (Refined-Tan-PBPK-Research-v1)  
**Model Scope**: Model-specific evidence only; generic Introduction/Background statements are excluded unless explicitly tied to the model.  
**Fit-for-purpose Summary**: 28/36 Tan items have an evidence-backed rating; 8/36 remain i_cannot_answer.  

## Summary of Questionnaire Items

| Item ID | Section | Response | Confidence | Details & Verbatim Evidence |
|---|---|:---:|:---:|---|
| `TAN_1.1` | 1. Model identification | **YES** | high | Wambaugh model adapted for PFOS, PFOA, PFHxS; no metabolites or CAS stated. <br/>*Evidence*: *we selected the animal model in Wambaugh et al. (2013) for further adaptation he...* (Selected model) |
| `TAN_1.2` | 1. Model identification | **YES** | high | Dean et al., 2025, Toxicological Sciences, DOI 10.1093/toxsci/kfaf087. <br/>*Evidence*: *Toxicological Sciences, 2025, 207(1), 139–147 https://doi.org/10.1093/toxsci/kfa...* (Title page) |
| `TAN_1.3` | 1. Reviewer context | **NOT_APPLICABLE** | low | Pipeline metadata not derivable from paper text. <br/>*Evidence*: None |
| `TAN_2.1.1` | 2.1 Executive summary | **YES** | high | Adapt animal TK models to humans for reverse dosimetry of data-sparse PFAS in food. <br/>*Evidence*: *To facilitate reverse dosimetry and risk assessment for the less studied PFAS co...* (Abstract) |
| `TAN_2.1.2` | 2.1 Executive summary | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.1.3` | 2.1 Executive summary | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.3.1` | 2.3 Model purpose | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.2.1` | 2.2 & 2.4.2 Chemical properties and active moiety | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.4.1` | 2.4.1 Modeling strategy | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.4.2A` | 2.4.2 Data summary: parameterization studies | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.4.2B` | 2.4.2 Calibration datasets | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.4.2C` | 2.4.2 Evaluation datasets | **I_CANNOT_ANSWER** | low | The LLM did not return this Tan questionnaire item. <br/>*Evidence*: None |
| `TAN_2.4.3.1` | 2.4.3A Structure and lineage | **YES** | high | Refines Wambaugh (2013) and Andersen (2006) by adding bioavailability and updating free fraction for human scaling. <br/>*Evidence*: *The Wambaugh model is an adaptation of the Andersen et al. (2006) model... a par...* (Selected model; Inferences) |
| `TAN_2.4.3.2` | 2.4.3A Structure and platform | **YES** | high | Three-compartment model (central, deep, filtrate) coded in R using mrgsolve and FME. <br/>*Evidence*: *includes three compartments: A central compartment, a second (“deep”) compartmen...* (Selected model; Fig. 1) |
| `TAN_2.4.3.3` | 2.4.3B ADME: absorption | **PARTIALLY** | high | Oral absorption uses first-order rate (ka) and bioavailability; IV is modeled but lacks detailed presystemic mechanism. <br/>*Evidence*: *a parameter for bioavailability was added... the rate of absorption from the gut...* (Inferences; Fig. 1) |
| `TAN_2.4.3.4` | 2.4.3B ADME: binding and blood partitioning | **PARTIALLY** | high | Free fraction (Free) in central compartment is modeled; hematocrit and blood-to-plasma partitioning are not explicitly detailed. <br/>*Evidence*: *the proportion of free compound in the central compartment, were updated to refl...* (Inferences) |
| `TAN_2.4.3.5` | 2.4.3B ADME: tissue partitioning | **PARTIALLY** | high | Three-compartment model with rate constants k12/k21; no explicit tissue partition coefficients or perfusion/diffusion distinction. <br/>*Evidence*: *Vt=k12/k21 × Vc...Qd= k12 × Vc...* (Page 140, Fig. 1) |
| `TAN_2.4.3.6` | 2.4.3B ADME: metabolism | **NOT_APPLICABLE** | high | PFAS are persistent; model contains no metabolism compartment or metabolite formation. <br/>*Evidence*: *three compartments: A central compartment, a second...and a filtrate compartment...* (Page 140, Methods) |
| `TAN_2.4.3.7` | 2.4.3B ADME: excretion and recirculation | **PARTIALLY** | high | Renal filtration and saturable reabsorption modeled; no biliary, fecal, exhaled, or enterohepatic mechanisms. <br/>*Evidence*: *saturable process with a Michaelis–Menten kinetics dictates reabsorption from th...* (Page 140, Methods) |
| `TAN_2.4.3.8` | 2.4.3B ADME: barrier and life-stage transfer | **NOT_APPLICABLE** | high | Paper explicitly states model excludes pregnancy, breastfeeding, and developmental compartments. <br/>*Evidence*: *the TK model does not include a development compartment...underestimates serum l...* (Page 141, Methods) |
| `TAN_2.4.3.9` | 2.4.3C Assumptions: perfusion/diffusion/lumping | **YES** | high | Three-compartment lumped model; developmental compartments explicitly omitted. <br/>*Evidence*: *the TK model does not include a development compartment and thus underestimates ...* (p.141, paragraph on NHANES exclusion) |
| `TAN_2.4.3.10` | 2.4.3C Assumptions: binding/free fraction | **YES** | high | Free parameter set to human plasma unbound fraction; correlated with resorption parameters. <br/>*Evidence*: *values for Free, the proportion of free compound in the central compartment, wer...* (p.140, paragraph on parameter assumptions) |
| `TAN_2.4.3.11` | 2.4.3C Assumptions: borrowing | **YES** | high | Parameters held constant animal-to-human; PFHxS starting values borrowed from PFOS. <br/>*Evidence*: *The remaining parameters were held constant between the animal and human models...* (p.142, paragraph on scaling) |
| `TAN_2.4.3.12` | 2.4.3C Assumptions: clearance/resorption/ontogeny | **PARTIALLY** | high | Saturable renal resorption modeled; no metabolism described; ontogeny omitted. <br/>*Evidence*: *a saturable process with a Michaelis–Menten kinetics dictates reabsorption from ...* (p.140, paragraph on Wambaugh model) |
| `TAN_2.4.3.13` | 2.4.3C Assumptions: dosing/steady state | **NOT_APPLICABLE** | high | Model explicitly excludes pregnancy, breastfeeding, and developmental compartments; no run-in, suckling, or milk assumptions exist. <br/>*Evidence*: *the TK model does not include a development compartment and thus underestimates ...* (Page 141, Methods) |
| `TAN_2.4.4` | 2.4.4 Model equations | **PARTIALLY** | high | Schematic (Fig 1) shows compartment relationships and scaling; no explicit ODEs written in text. Saturable resorption via Michaelis-Menten stated. <br/>*Evidence*: *Vc=Vcc×BW; Tm=Tmc×BW; Qfil=QfilC×QCC×BW0.74; Vt=k12/k21×Vc...* (Page 141, Fig 1) |
| `TAN_2.4.5A` | 2.4.5A Parameter tabulation and scaling | **PARTIALLY** | high | Table 1 referenced but content truncated. 8 chemical-specific params named; human BW=70kg, QCC=12.5 L/h/kg^0.74; Tmc values given. <br/>*Evidence*: *human values for the bodyweight (70 kg) and cardiac output (12.5 L/h/kg0.74)...* (Page 140, Methods) |
| `TAN_2.4.5B` | 2.4.5B Parameter sources and competing values | **PARTIALLY** | high | Sources cited for Free (Smeltz 2023), bioAv (Verner 2016/EPA), Tmc (Li 2018), scaling (Loccisano 2011), base model (Wambaugh 2013/Andersen 2006). Table 1 source column truncated. <br/>*Evidence*: *values for Free...updated to reflect the most current assessment...Smeltz et al....* (Page 140, Methods) |
| `TAN_2.4.5C` | 2.4.5C Parameter distributions and uncertainty | **PARTIALLY** | high | MCMC 95% credible intervals reported for estimated parameters; no explicit distribution types or bounds stated. <br/>*Evidence*: *The 95% credible intervals for the estimated parameter values were determined fr...* (Page 141, Inferences paragraph) |
| `TAN_2.4.6A` | 2.4.6A Exposure and dosing | **PARTIALLY** | high | Oral and IV routes in animal data; NHANES exposure model with log-linear time-varying intake rates in ng/kg BW/day. <br/>*Evidence*: *PFAS exposure varying log-linearly with calendar time, starting in 1950 and with...* (Page 141, NHANES paragraph) |
| `TAN_2.4.6B` | 2.4.6B Samples, subjects, trials, and probabilistic setup | **PARTIALLY** | high | Serum matrix; NHANES ages 21–79; MCMC inference used but iteration count not stated. <br/>*Evidence*: *Data for individuals < 20 years of age were excluded... individuals ≥80 years of...* (Page 141, NHANES paragraph) |
| `TAN_2.4.7` | 2.4.7 Software and numerical solvers | **PARTIALLY** | high | R with mrgsolve and FME packages; modMCMC for inference; code in Section S1; solver not named. <br/>*Evidence*: *The Wambaugh model was coded and studied in R using the mrgsolve package framewo...* (Page 141, Inferences paragraph) |
| `TAN_2.5.1A` | 2.5.1A Evaluation: training versus validation | **YES** | high | Calibration to monkey data; validation via NHANES simulation and PODHED comparison to EPA model. <br/>*Evidence*: *The PFOS model predicted serum levels with an MSLE of 0.07... The PFOA model mor...* (Page 141, Results) |
| `TAN_2.5.1B` | 2.5.1B Goodness-of-fit and applicability | **YES** | high | MSLE reported; factor-of-2 criterion stated; visual comparison noted; applicability to datasparse compounds discussed. <br/>*Evidence*: *Predictions that were on average within a factor of 2 of the experimental data w...* (Page 141, Methods) |
| `TAN_2.5.2A` | 2.5.2A Sensitivity protocol | **PARTIALLY** | high | Local perturbation of ka, k12, k21 by 2 orders of magnitude; MCMC for identifiability; full protocol in supplementary. <br/>*Evidence*: *Changing the value of ka, k12, or k12 by up to 2 orders of magnitude resulted in...* (Page 142, Results) |
| `TAN_2.5.2B` | 2.5.2B Sensitive parameters and uncertainty impact | **YES** | high | Free correlated with Tmc/Kt; k12/k21>100 affects VCC; MCMC CIs reported; variability would capture more NHANES data. <br/>*Evidence*: *The Free parameter was found to be highly correlated to the resorption parameter...* (Page 142, Results) |

## Key Gaps Identified

- TAN_2.1.2: model-specific evidence not sufficient for a supported rating
- TAN_2.1.3: model-specific evidence not sufficient for a supported rating
- TAN_2.3.1: model-specific evidence not sufficient for a supported rating
- TAN_2.2.1: model-specific evidence not sufficient for a supported rating
- TAN_2.4.1: model-specific evidence not sufficient for a supported rating
- TAN_2.4.2A: model-specific evidence not sufficient for a supported rating
- TAN_2.4.2B: model-specific evidence not sufficient for a supported rating
- TAN_2.4.2C: model-specific evidence not sufficient for a supported rating
