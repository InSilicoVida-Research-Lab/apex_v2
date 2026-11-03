for each parameter are shown in Table 1. Changing the value of $k_a$, $k_{12}$, or $k_{12}$ by up to 2 orders of magnitude resulted in an average change in value for VCC, Tmc, $K_t$, and bioAv (PFOA) of less than 10% (Tables S2 and S3), suggesting a robustness of the inference process given the available data. Increasing the ratio $k_{12}/k_{21}$ to values equal to or greater than 100 resulted in changes in VCC of greater than 10%, as noted in Wambaugh et al. (2013). The Free parameter was found to be highly correlated to the resorption parameters; changing Free will then result in a change in Tmc and $K_t$.

The animal models were scaled to humans by adjusting the cardiac blood output (QCC) to 12.5 L/h/kg$^{0.74}$ and fitting a saturable resorption rate (Tmc) for a half-life of 3.4 years and 2.7 years for PFOS and PFOA, respectively (Li et al. 2018; Pizzurro et al. 2019). The remaining parameters were held constant between the animal and human models, as shown in Table 1, with the exception of the PFOA bioAv and $K_t$ parameters, which were refit to the nonhuman primate data assuming a bioavailability of 90% for application in the human model, as the lower bioavailability observed in the nonhuman primate model was assumed to be the result of experiment-specific conditions. The resulting values for Tmc were 1.07 and 0.54 mg/h/kg for PFOS and PFOA, respectively.

## Model validation

### Animal models

Model performance was first evaluated by visually comparing model predictions to observed data (Fig. 2). The MSLE for the PFOS and PFOA models were 0.07 and 0.58, respectively, which fall within the range of MSLEs deemed acceptable by the EPA for

the mice and rat data used to train and test the Wambaugh model (US EPA 2024a, 2024b). For PFOS, the model predictions were within a factor of 2 of the observed serum levels for 98% of the data points, whereas for PFOA, the model predictions were within a factor of 2 of the observed serum levels for 71% of the data. Models more closely approximated the serum levels during and after repeated oral exposures to PFOS and PFOA, than the serum levels after singular IV exposures (Figs S1 to S4) (US EPA 2024a, 2024b).

### Human models—simulating biomonitoring data

Mean parameter estimates for the human PFOS and PFOA models were used to simulate NHANES biomonitoring data. The PFOS model predicted serum levels with an MSLE of 0.07 (Fig. 3) and an underlying exposure model that peaked in 1990 at 14.9 ng PFOS/kg BW/day, fell to 2.5 ng PFOS/kg BW/day in 1998, and continued decreasing to 0.24 ng PFOS/kg BW/day in 2017 (Fig. S5). The PFOA model more closely predicted the NHANES observed serum levels with an MSLE of 0.03 (Fig. 4) and an underlying exposure model that increased from 0.45 ng/kg BW/day in 1990 to 1.1 ng/kg BW/day in 1998 and fell to 0.13 ng/kg BW/day in 2017 (Fig. S6). The models were able to match the trends for change in PFOS (Fig. S7) and PFOA (Fig. S8) serum levels for individuals born in the 1940s through 1990s. Notably, including variability and uncertainty in the parameter estimates for simulating the biomonitoring data would capture even more of the observed data (Figs S7 and S8).

### Comparisons to the EPA-modified Verner model

The human models were also used to calculate the $POD_{HED}$ for the cardiovascular and hepatic endpoints evaluated in the EPA’s

Table 1. Mean (95% CI) TK parameters for PFOS and PFOA fit to nonhuman primate data and scaled to humans.

<table>
<thead>
  <tr class="table-header">
    <th rowspan="2">Species</th>
    <th rowspan="2">Type of variable</th>
    <th rowspan="2">Variable</th>
    <th rowspan="2">Name</th>
    <th colspan="2">Mean (95% CI)</th>
    <th rowspan="2">Source</th>
  </tr>
  <tr>
    <th>PFOS</th>
    <th>PFOA</th>
  </tr>
</thead>
<tbody>
  <tr class="data-row">
    <th rowspan="2">Nonhuman primate Physiological</th>
    <th rowspan="2">Body weight (kg)</th>
    <th rowspan="2">BW</th>
    <th rowspan="2">5<sup>a</sup></th>
    <th rowspan="2">4.1<sup>a</sup></th>
    <th>Butenhoff et al. (2004); Chang et al. (2012); Seacat et al. (2002)</th>
  </tr>
  <tr>
    <th>Cardiac blood output (L/h/kg$^{0.74}$)</th>
    <th>QCC</th>
    <th>19.8</th>
    <th>19.8</th>
    <th>Wambaugh et al. (2013)</th>
  </tr>
  <tr class="data-row">
    <th rowspan="4">Chemical-specific</th>
    <th>Fraction of cardiac output to filtrate</th>
    <th>QfIC</th>
    <th>0.15</th>
    <th>0.15</th>
    <th>Wambaugh et al. (2013)</th>
  </tr>
  <tr class="data-row">
    <th>Volume of filtrate compartment (L/kg)</th>
    <th>VfIC</th>
    <th>4.00E-04</th>
    <th>4.00E-04</th>
    <th>Loccisano et al. (2011)</th>
  </tr>
  <tr class="data-row">
    <th>Bioavailability</th>
    <th>bioAv</th>
    <th>0.9</th>
    <th>0.32 (0.20, 0.46)</th>
    <th>US EPA (2024a) (PFOS) Optimized (PFOA) Optimized</th>
  </tr>
  <tr class="data-row">
    <th rowspan="6">Human Physiological</th>
    <th>Volume of distribution central compartment (L/kg)</th>
    <th>VCC</th>
    <th>0.24 (0.24, 0.25)</th>
    <th>0.23 (0.18, 0.29)</th>
    <th>Optimized</th>
  </tr>
  <tr class="data-row">
    <th>Saturable resorption rate (mg/h/kg)</th>
    <th>Tmc</th>
    <th>2.5 (2.31, 2.80)</th>
    <th>0.28 (0.17, 0.53)</th>
    <th>Optimized</th>
  </tr>
  <tr class="data-row">
    <th>Saturable resorption affinity (mg/L)</th>
    <th>K<sub>t</sub></th>
    <th>0.004 (0.003, 0.004)</th>
    <th>0.017 (0.010, 0.041)</th>
    <th>Optimized</th>
  </tr>
  <tr class="data-row">
    <th>Proportion of free compound in serum</th>
    <th>Free</th>
    <th>4.50E-03</th>
    <th>1.20E-3</th>
    <th>Smeltz et al. (2023)</th>
  </tr>
  <tr class="data-row">
    <th>Rate from central to second compartment (1/h)</th>
    <th>$k_{12}$</th>
    <th>3.3</th>
    <th>3.3</th>
    <th>Andersen et al. (2006)</th>
  </tr>
  <tr class="data-row">
    <th>Rate from second to central compartment (1/h)</th>
    <th>$k_{21}$</th>
    <th>3.4</th>
    <th>3.4</th>
    <th>Andersen et al. (2006)</th>
  </tr>
  <tr class="data-row">
    <th>Ratio from gut to central compartment (1/h)</th>
    <th>$k_a$</th>
    <th>132</th>
    <th>230</th>
    <th>Wambaugh et al. (2013)</th>
  </tr>
  <tr class="data-row">
    <th colspan="7">Human</th>
  </tr>
  <tr class="data-row">
    <th rowspan="4">Chemical-specific</th>
    <th>Body weight (kg)</th>
    <th>BW</th>
    <th>70</th>
    <th>70</th>
    <th>Loccisano et al. (2011)</th>
  </tr>
  <tr class="data-row">
    < 5<sup>a</sup> Cardiac blood output (L/h/kg$^{0.74}$)</th>
    <th>QCC</th>
    <th>12.5</th>
    <th>12.5</th>
    <th>Loccisano et al. (2011)</th>
  </tr>
  <tr class="data-row">
    <td rowspan="2">Bioavailability</td>
    <th>bioAv</th>
    <th>0.9</th>
    <th>0.9</th>
    <th>US EPA (2024a, 2024b)</th>
  </tr>
  <tr class="data-row">
    <th>Saturable resorption rate (mg/h/kg)</th>
    <th>T mc</th>
    <th>1.07</th>
    <th>0.54</th>
    <th>Optimized</th>
  </tr>
  <tr class="data-row">
    <th>Saturable resorption affinity (mg/l)</th>
    <th>$K_t$</th>
    <th>0.004</th>
    <th>0.008<sup>b</sup></th>
    <th>Optimized (nonhuman primate)</th>
  </tr>
  <tr class="data-row">
    <th colspan="2">Half-life (years)</th>
    <th>$T_{1/2}$</th>
    <th>3.4</th>
    <th>2.7</th>
    <th>Li et al. (2018)</th>
  </tr>
</tbody>
</table>

<sup>a</sup> The code uses the average body weight for each nonhuman primate or group of nonhuman primates as reported in the original studies.

<sup>b</sup> If the bioavailability is set to 90% for the nonhuman primate model of PFOA, the Tmc and $K_t$ values for the nonhuman primates are 0.15 mg/h/kg and 0.008 mg/L, respectively. For the human model, a set value of 0.008 mg/L for $K_t$ was used as it is representative of the higher bioavailability considered more typical for intake of food and water.