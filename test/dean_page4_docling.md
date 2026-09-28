for each parameter are shown in Table 1. Changing the value of ka, k12, or k12 by up to 2 orders of magnitude resulted in an aver­ age change in value for VCC, Tmc, Kt, and bioAv (PFOA) of less than 10% (Tables S2 and S3), suggesting a robustness of the infer­ ence process given the available data. Increasing the ratio k12/k21 to values equal to or greater than 100 resulted in changes in VCC of greater than 10%, as noted in Wambaugh et al. (2013). The Free parameter was found to be highly correlated to the resorption parameters; changing Free will then result in a change in Tmc and Kt.

The animal models were scaled to humans by adjusting the cardiac blood output (QCC) to 12.5L/h/kg 0.74 and fitting a satura­ ble resorption rate (Tmc) for a half-life of 3.4years and 2.7years for PFOS and PFOA, respectively (Li et al. 2018; Pizzurro et al. 2019). The remaining parameters were held constant between the animal and human models, as shown in Table 1, with the exception of the PFOA bioAv and Kt parameters, which were refit to the nonhuman primate data assuming a bioavailability of 90% for application in the human model, as the lower bioavailability observed in the nonhuman primate model was assumed to be the result of experiment-specific conditions. The resulting values for Tmc were 1.07 and 0.54mg/h/kg for PFOS and PFOA, respec­ tively.

## Model validation

## Animal models

Model performance was first evaluated by visually comparing model predictions to observed data (Fig. 2). The MSLE for the PFOS and PFOA models were 0.07 and 0.58, respectively, which fall within the range of MSLEs deemed acceptable by the EPA for the mice and rat data used to train and test the Wambaugh model (US EPA 2024a, 2024b). For PFOS, the model predictions were within a factor of 2 of the observed serum levels for 98% of the data points, whereas for PFOA, the model predictions were within a factor of 2 of the observed serum levels for 71% of the data. Models more closely approximated the serum levels during and after repeated oral exposures to PFOS and PFOA, than the serum levels after singular IV exposures (Figs S1 to S4) (US EPA 2024a, 2024b).

## Human models-simulating biomonitoring data

Mean parameter estimates for the human PFOS and PFOA mod­ els were used to simulate NHANES biomonitoring data. The PFOS model predicted serum levels with an MSLE of 0.07 (Fig. 3) and an underlying exposure model that peaked in 1990 at 14.9ng PFOS/ kg BW/day, fell to 2.5ng PFOS/kg BW/day in 1998, and continued decreasing to 0.24ng PFOS/kg BW/day in 2017 (Fig. S5). The PFOA model more closely predicted the NHANES observed serum levels with an MSLE of 0.03 (Fig. 4) and an underlying exposure model that increased from 0.45ng/kg BW/day in 1990 to 1.1ng/kg BW/ day in 1998 and fell to 0.13ng/kg BW/day in 2017 (Fig. S6). The models were able to match the trends for change in PFOS (Fig. S7) and PFOA (Fig. S8) serum levels for individuals born in the 1940s through 1990s. Notably, including variability and uncertainty in the parameter estimates for simulating the biomonitoring data would capture even more of the observed data (Figs S7 and S8).

## Comparisons to the EPA-modified Verner model

The human models were also used to calculate the PODHED for the cardiovascular and hepatic endpoints evaluated in the EPA's

Table 1. Mean (95% CI) TK parameters for PFOS and PFOA fit to nonhuman primate data and scaled to humans.

|                          |                                                 |       |                      |                      |                                                                    |
|--------------------------|-------------------------------------------------|-------|----------------------|----------------------|--------------------------------------------------------------------|
| Species Type of variable | Variable                                        | Name  | Mean (95% CI)        | PFOA                 | Source                                                             |
|                          |                                                 |       | PFOS                 |                      |                                                                    |
| Nonhuman primate         |                                                 |       |                      |                      |                                                                    |
| Physiological            | Body weight (kg)                                | BW    | 5 a                  | 4.1 a                | Butenhoff et al. (2004); Chang et al. (2012); Seacat et al. (2002) |
|                          | Cardiac blood output (L/h/kg 0.74 )             | QCC   | 19.8                 | 19.8                 | Wambaugh et al. (2013)                                             |
|                          | Fraction of cardiac output to filtrate          | QfilC | 0.15                 | 0.15                 | Wambaugh et al. (2013)                                             |
|                          | Volume of filtrate compartment (L/kg)           | VfilC | 4.00E-04             | 4.00E-04             | Loccisano et al. (2011)                                            |
| Chemical-specific        | Bioavailability                                 | bioAv | 0.9                  | 0.32 (0.20, 0.46)    | US EPA (2024a)(PFOS) Optimized (PFOA)                              |
|                          | Volume of distribution central compartment      | VCC   | 0.24 (0.24, 0.25)    | 0.23 (0.18, 0.29)    | Optimized                                                          |
|                          | (L/kg) Saturable resorption rate (mg/h/kg)      | Tmc   | 2.5 (2.31, 2.80)     | 0.28 (0.17, 0.53)    | Optimized                                                          |
|                          | Saturable resorption affinity (mg/L)            | Kt    | 0.004 (0.003, 0.004) | 0.017 (0.010, 0.041) | Optimized                                                          |
|                          | Proportion of free compound in serum            | Free  | 4.50E-03             | 1.20E-3              | Smeltz et al. (2023)                                               |
|                          | ate from central to second compartment (1/h)    | k12   | 3.3                  | 3.3                  | Andersen et al. (2006)                                             |
|                          | ate from second to central compartment          | k21   | 3.4                  | 3.4                  | Andersen et al. (2006)                                             |
|                          | (1/h) ate from gut to central compartment (1/h) | ka    | 132                  | 230                  | Wambaugh et al. (2013)                                             |
| Physiological            | Body weight (kg)                                | BW    | 70                   | 70                   | Loccisano et al. (2011)                                            |
|                          | Cardiac blood output (L/h/kg 0.74 )             | QCC   | 12.5                 | 12.5                 | Loccisano et al. (2011)                                            |
| Chemical-specific        | Bioavailability                                 | bioAv | 0.9                  | 0.9                  | US EPA (2024a, 2024b)                                              |
|                          | Saturable resorption rate (mg/h/kg)             | Tmc   | 1.07                 | 0.54                 | Optimized                                                          |
|                          | Saturable resorption affinity (mg/L)            | Kt    | 0.004                | 0.008 b              | Optimized (nonhuman primate)                                       |
|                          | Half-life (years)                               | T1/2  | 3.4                  | 2.7                  | Li et al. (2018)                                                   |