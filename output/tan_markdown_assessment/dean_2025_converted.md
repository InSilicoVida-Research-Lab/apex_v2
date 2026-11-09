<!-- PAGE 1 -->
### [Page 1]
SOT<sup>Society of</sup> Toxicology O X F OR D academic.oup.com/toxsci 

_Toxicological Sciences_ , 2025, **207(1),** 139–147 

**https://doi.org/10.1093/toxsci/kfaf087** Advance Access Publication Date: June 16, 2025 **Research article** 

# **Adapting existing toxicokinetic models to relate perfluoroalkyl and polyfluoroalkyl intake to biomarkers in humans** 

Kara J. Dean 1, , R gis Pouillot2, Jane M. Van Doren1, Sofia M. Santillana Farakos1 1Human Foods Program, U.S. Food and Drug Administration, College Park, MD 20740, United States 2Consultant, Rabat 10170, Morocco Corresponding author: Human Foods Program, U.S. Food and Drug Administration, 5001 Campus Drive, College Park, MD 20740, United States. Email: kara.dean@fda.hhs.gov 

#### Abstract 

Exposures to per- and polyfluoroalkyl substances (PFAS) are associated with various adverse health outcomes, and a wide range of PFAS compounds have been detected in human serum, the environment, and food. Toxicokinetic models, however, have been developed for only a subset of the compounds of interest. To facilitate reverse dosimetry and risk assessment for the less studied PFAS compounds in food, we developed and evaluated an approach to adapt existing toxicokinetic models for nonhuman primates to predict human serum levels. The approach was validated with perfluorooctanoic acid and perfluorooctanesulfonic acid data and applied to perfluorohexanesulfonate. Results indicate that the approach yields similar dosimetry estimates to those of other models, particularly those used for regulatory purposes, suggesting the methodology can be leveraged to inform decision-making in datasparse spaces. Applying and adapting the framework will improve our ability to connect dietary PFAS exposures to endpoints of concern for a wide range of PFAS compounds. 

##### Keywords: compartmental model; toxicokinetics; animals; perfluorinated chemicals; biomarkers; mathematical modeling 

Per- and polyfluoroalkyl substances (PFAS) are a class of synthetic chemicals composed of thousands of compounds that are known to be highly persistent in the environment. Available epidemiological studies indicate associations between exposure to perfluorooctanoic acid (PFOA) and perfluorooctanesulfonic acid (PFOS) and several health outcomes, including decreased antibody response, increases in serum lipids, pregnancy-induced hypertension, increases in serum hepatic enzymes, and decreased birth weights (ATSDR 2021; US EPA 2024a, 2024b). Exposure to other PFAS, such as perfluorononanoic acid (PFNA), perflourodecanoic acid (PFDA), perfluorohexanesulfonate (PFHxS), perfluorobutanoic acid (PFBA), and perfluorobutanesulfonic acid (PFBS), has also been reported to be associated with developmental, thyroid, immune, hepatic, kidney, and/or reproductive effects (Gleason et al. 2015; ATSDR 2021; US EPA 2021, 2022, 2023). 

Higher concentrations of PFAS in serum have been detected in some individuals with occupational exposures and some residents of communities with proximity to military sites, commercial airports, landfills, or fluorochemical manufacturers (Calafat et al. 2019; ATSDR 2021). However, for most individuals, the primary routes of exposure are considered to be the ingestion of contaminated water and food (Domingo and Nadal 2017). A study by the US Centers for Disease Control and Prevention reports serum to be the best biomarker for biomonitoring PFAS, 

regardless of biopersistence, and summarizes National Health and Nutrition Examination Survey (NHANES) biomonitoring data from 2013 to 2014 in serum indicating universal exposure to PFOS, PFOA, PFNA, and PFHxS among the US general population (Calafat et al. 2019). 

Toxicokinetic (TK) modeling is used to describe and quantify the relationship between external measures of exposure (i.e. food intake) and internal biomarkers (i.e. serum). Compartmental models are considered the simplest form of TK model in which a system is represented by one or few compartments, and modified compartment models have extensions that can also describe the toxicokinetics during pregnancy and lactation. Physiologically based toxicokinetic (PBTK) models are the most complex TK models, in which the concentration of a substance is modeled in multiple tissues synchronously using physiologically based parameters. PBTK models are the most physiologically accurate, but the model complexity is data-intensive. 

Detailed reviews of available PFAS TK models have been published elsewhere (Chou and Lin 2021; East et al. 2023; US EPA 2024a, 2024b). Briefly, several TK models, including animal, human, PBTK, as well as compartmental models, have been published for the long-chain PFOA and PFOS compounds (e.g. Andersen et al. 2006; Tan et al. 2008; Wambaugh et al. 2008; Wambaugh et al. 2013; Loccisano et al. 2011; Verner et al. 2016; Ruark et al. 2017; Brochot et al. 2019; Chou and Lin 2019; Goeden 

> © The Author(s) 2025. Published by Oxford University Press on behalf of the Society of Toxicology. This is an Open Access article distributed under the terms of the Creative Commons Attribution License (https://creativecommons.org/licenses/by/4.0/), which permits unrestricted reuse, distribution, and reproduction in any medium, provided the original work is properly cited.

<!-- PAGE 2 -->
### [Page 2]
140 | Dean et al. 

et al. 2019). A few of these compartment and PBTK models have been applied for regulatory purposes (Loccisano et al. 2011; Wambaugh et al. 2013; Verner et al. 2016; Goeden et al. 2019). There are fewer TK models (e.g. Fabrega et al. 2015; Kim et al. 2018, 2019; Sweeney 2022) available, however, for the large number of additional compounds that can be found in foods (e.g. PFDA, PFHxS, PFNA, PFBS), and the implementation of compartment developmental and PBTK models for compounds such as PFHxS, PFBS, and PFNA has shown inconsistencies with empirical data, which has limited their utility for risk assessments (Fabrega et al. 2015; Verner et al. 2016; Kim et al. 2018; Sweeney 2022; US EPA 2023, 2024c). 

To facilitate TK modeling for compounds with limited human data, this study aims to develop an approach that makes use of existing animal data and models and scales it to humans. To achieve this goal, we developed an approach that adapts an existing TK model for nonhuman primates and relates PFAS exposures to the concentration of PFAS in the serum for humans. Given the available data for PFOS and PFOA, the approach was developed and validated for those 2 compounds and was then used to parameterize models for PFHxS forward and reverse dosimetry. The framework presented herein can be used to parametrize models for additional compounds, as data permits, and will improve the ability to better relate dietary PFAS exposures to endpoints of concern for a wider range of PFAS compounds. 

## Materials and methods 

### **Selected model** 

Given the high number of compounds of interest found in food that are associated with minimal human-specific data for calibration, we selected the animal model in Wambaugh et al. (2013) for further adaptation herein. Importantly, the multicompartment animal model in Wambaugh et al. (2013), referred to hereafter as the Wambaugh model, can accommodate nonlinear elimination patterns, which will maximize the utility of the TK modeling approach for leveraging animal datasets and will facilitate applications of the models for normal and extreme exposure scenarios. 

The Wambaugh model is an adaptation of the Andersen et al. (2006) model and includes three compartments: A central compartment, a second (“deep”) compartment, and a filtrate compartment, where a saturable process with a Michaelis–Menten kinetics dictates reabsorption from the filtrate compartment to the central compartment (Fig. 1) (Andersen et al. 2006). 

### **Experimental data on PFOS and PFOA** 

In Wambaugh et al. (2013), the PFOS and PFOA pharmacokinetic models were fitted to cynomolgus monkey data originating from Butenhoff et al. (2004), Chang et al. (2012), and Seacat et al. (2002). We obtained the raw data for the PFOS experiments directly from 3M in personal communications (Chang 2020a; Chang 2020b). Both oral and intravenous (IV) datasets were made available. 

### **TK modeling approach: a case study with PFOS and PFOA** 

We used the following stepwise approach to estimate human model parameters in our adapted Wambaugh model for PFOS and PFOA: 

- i) We first estimated an identifiable set of sensitive parameters of the PFOA and PFOS Wambaugh model to fit the experimental data on nonhuman primates. 

- ii) We scaled the reparametrized Wambaugh model from Part I to humans using human values for the bodyweight (70 kg) and cardiac output (12.5 L/h/kg<sup>0.74</sup> ) following the procedure of Loccisano et al. (2011); 

- iii) We then adjusted the maximum rate of the saturable resorption parameter ( _Tm_ , mg/h) to match the half-life estimated in humans from an exposure study deemed to be representative of the general population (Li et al. 2018). 

### **Inferences** 

The Wambaugh model was coded and studied in R using the mrgsolve package framework and the FME package (Soetaert and Petzoldt 2010; Baron 2023) for model adjustment. Further details are provided in the R code (Section S1). 

Not all the parameters were able to be independently estimated from the available data, as evident in the large credible intervals reported in Wambaugh et al. (2013). The number of identifiable parameters was first determined herein using the “collin” function from the FME package (Soetaert and Petzoldt 2010). An iterative process was then applied, through the analysis of the convergence and the outputs of Monte-Carlo Markov Chain (MCMC) inference processes (modMCMC function from FME), to further check the identifiability of the model. When a parameter could not be independently estimated, a value was assumed based on that reported in the literature or using an optimized value for other compounds as shown in the parameter tables. The initial parameter values for estimation are shown in Table S1. An iterative process was applied from these starting values as needed to minimize the sum of squared residuals. Most of these starting values were consistent with the optimized parameter values from Wambaugh et al. (2013); however, the values for _Free_ , the proportion of free compound in the central compartment, were updated to reflect the most current assessment of the fraction of unbound compound in human plasma (Smeltz et al. 2023). Additionally, a parameter for bioavailability was added to the model to align with the Verner et al. (2016) model implemented by the US EPA (2024a, 2024b) in their final reference dose level setting for PFOS and PFOA. The bioavailability was initially set at 90% for both compounds to reflect a high fraction of an administered dose reaching systemic circulation after oral ingestion; however, for PFOA, the parameter was found to be identifiable and estimable from the data for the nonhuman primate model only. The 95% credible intervals for the estimated parameter values were determined from the output of the MCMC. 

### **Model checking and validation** 

Model performance was evaluated with mean square log errors (MSLE) and by visually comparing the commonalities between the observed and predicted data. Predictions that were on average within a factor of 2 of the experimental data were considered adequate (World Health Organization 2010). For the human models specifically, the performance of the resulting models was assessed by (i) simulating biomonitoring data in the NHANES and (ii) predicting point of departure human equivalent doses (PODHED). 

For validation with NHANES biomonitoring data, the observed PFOS and PFOA serum levels were extracted from the NHANES data files (1999 to 2000, 2003 to 2004 and 2017 to 2018 surveys) with the respective date of birth. Data for individuals _<_ 20 years

<!-- PAGE 3 -->
### [Page 3]
_Toxicological Sciences_ , 2025, Vol 207, Issue 1 | 141 



<!-- Start of picture text -->
Second Compartment<br>Vt, CDeep<br>Vt=k12/k21 × Vc<br>Qd= k12 × Vc<br>ka Central Compartment<br>Oral Dose Vc, CPrim, Free<br>Vc=Vcc×BW<br>Qfíil Tm  = Tmc ×BW<br>Kt<br>Filtrate Compartment Qfil = QfilC × QCC × BW0.74<br>Vfil, Cfil<br>Vfil=VfilC × BW<br><!-- End of picture text -->

Fig. 1. Schematic for the three-compartment model ( _Vc_ , _Vt_ , _Vfil_ ) with a saturable resorption process ( _Tm_ , _Kt_ ) adapted from Wambaugh et al. (2013) and Andersen et al. (2006); _CPrim_ , _CDeep_ , and _Cfil_ are the chemical concentrations in the primary/central, deep/second, and filtrate compartments. 

of age were excluded from the fitting process because the TK model does not include a development compartment and thus underestimates serum levels in children and young adults by excluding gestation and breastfeeding exposures. Similarly, individuals ≥80 years of age were excluded as their exact age is not reported in NHANES. For each survey year and each age (21 to 79 years), the mean serum concentration of each PFAS was estimated using Centers for Disease Control and Prevention’s recommended procedure (Mirel et al. 2013; Chen et al. 2018, 2020) with the R survey package (Lumley 2004; Lumley et al. 2023). An exposure model was estimated based on the methodology and results obtained in Wong et al. (2014) for each compound, i.e. with PFAS exposure varying log-linearly with calendar time, starting in 1950 and with discontinuous breaks in 1990 and 1998. This time trend represents the increasing use of these chemicals from 1950 to 1990, followed by a decrease in their use and a transition to more restricted use after 1998 (Wong et al. 2014; Dzierlenga et al. 2020). The level of exposure in 1990, 1998, and 2017 were estimated using the FME modFit function. PFOS and PFOA serum levels in each survey were simulated using the corresponding modeled exposure to PFAS and the human-adapted models presented herein. The predicted and observed serum levels were compared to ensure the proposed approach yielded models capable of capturing available biomonitoring trends. 

To further evaluate the utility of the approach for decisionmaking purposes, the resulting TK models were used to calculate the PODHED for points of departure for cardiovascular and hepatic endpoints selected by the EPA in the Final Human Health Toxicity Assessments for PFOA and PFOS (US EPA 2024a, 2024b). As the model developed herein does not account for pregnancy or breastfeeding, developmental and immunological effects were not selected for evaluation. 

### **Application to other compounds** 

Nonhuman primate data were also shared for PFBS and PFHxS (Chang 2020c; Chang 2020d) and available in Sundstrom et al. € (2012) and Olsen et al. (2009). Given the short half-life of PFBS ( _<_ 7 days) and the likely minimal relevance of the saturable resorption process, we decided not to pursue the study of this compound further. The adapted Wambaugh model was thus only further parameterized for PFHxS following the procedure outlined in sections “Toxicokinetic modeling approach: a case study with PFOS and PFOA,” “Inferences,” and “Model checking and validation”. The starting values for the parameter estimation for PFHxS were the same as the starting values used for PFOS in Table S1. 

## Results 

### **Model parameters estimated for humans for both PFOA and PFOS** 

The Wambaugh model was fitted to the available nonhuman primate data for PFOS (Seacat et al. 2002; Chang et al. 2012) and PFOA (Butenhoff et al. 2004). Of the 8 chemical-specific parameters in the model ( _bioAv_ , _VCC_ , _Tmc_ , _Kt, Free_ , _k12_ , _k21_ , and _ka_ ), 6 and 8 parameters were a priori identifiable for PFOA and PFOS, respectively, from the “collin” function. However, further MCMC tries clearly indicated additional collinearities in the estimates. As such, the proportion of free compound in the serum ( _Free_ ), the rate of absorption from the gut ( _ka_ ), and the rate to and from the second compartment ( _k12_ , _k21_ ) were assigned set values from the iterative evaluation of the starting parameters (Table S1). The impact of parameter changes was evaluated with a sensitivity analysis. 

The _VCC_ , _Tmc_ , _Kt_ , and _bioAv_ (PFOA) parameters were estimated from the data. The mean and MCMC 95% credible interval

<!-- PAGE 4 -->
### [Page 4]
142 | Dean et al. 

for each parameter are shown in Table 1. Changing the value of _ka_ , _k12_ , or _k12_ by up to 2 orders of magnitude resulted in an average change in value for _VCC_ , _Tmc_ , _Kt_ , and _bioAv_ (PFOA) of less than 10% (Tables S2 and S3), suggesting a robustness of the inference process given the available data. Increasing the ratio _k12_ / _k21_ to values equal to or greater than 100 resulted in changes in _VCC_ of greater than 10%, as noted in Wambaugh et al. (2013). The _Free_ parameter was found to be highly correlated to the resorption parameters; changing _Free_ will then result in a change in _Tmc_ and _Kt_ . 

The animal models were scaled to humans by adjusting the cardiac blood output ( _QCC_ ) to 12.5 L/h/kg<sup>0.74</sup> and fitting a saturable resorption rate ( _Tmc_ ) for a half-life of 3.4 years and 2.7 years for PFOS and PFOA, respectively (Li et al. 2018; Pizzurro et al. 2019). The remaining parameters were held constant between the animal and human models, as shown in Table 1, with the exception of the PFOA _bioAv_ and _Kt_ parameters, which were refit to the nonhuman primate data assuming a bioavailability of 90% for application in the human model, as the lower bioavailability observed in the nonhuman primate model was assumed to be the result of experiment-specific conditions. The resulting values for _Tmc_ were 1.07 and 0.54 mg/h/kg for PFOS and PFOA, respectively. 

### **Model validation** 

#### _Animal models_ 

Model performance was first evaluated by visually comparing model predictions to observed data (Fig. 2). The MSLE for the PFOS and PFOA models were 0.07 and 0.58, respectively, which fall within the range of MSLEs deemed acceptable by the EPA for 

the mice and rat data used to train and test the Wambaugh model (US EPA 2024a, 2024b). For PFOS, the model predictions were within a factor of 2 of the observed serum levels for 98% of the data points, whereas for PFOA, the model predictions were within a factor of 2 of the observed serum levels for 71% of the data. Models more closely approximated the serum levels during and after repeated oral exposures to PFOS and PFOA, than the serum levels after singular IV exposures (Figs S1 to S4) (US EPA 2024a, 2024b). 

#### _Human models—simulating biomonitoring data_ 

Mean parameter estimates for the human PFOS and PFOA models were used to simulate NHANES biomonitoring data. The PFOS model predicted serum levels with an MSLE of 0.07 (Fig. 3) and an underlying exposure model that peaked in 1990 at 14.9 ng PFOS/ kg BW/day, fell to 2.5 ng PFOS/kg BW/day in 1998, and continued decreasing to 0.24 ng PFOS/kg BW/day in 2017 (Fig. S5). The PFOA model more closely predicted the NHANES observed serum levels with an MSLE of 0.03 (Fig. 4) and an underlying exposure model that increased from 0.45 ng/kg BW/day in 1990 to 1.1 ng/kg BW/ day in 1998 and fell to 0.13 ng/kg BW/day in 2017 (Fig. S6). The models were able to match the trends for change in PFOS (Fig. S7) and PFOA (Fig. S8) serum levels for individuals born in the 1940s through 1990s. Notably, including variability and uncertainty in the parameter estimates for simulating the biomonitoring data would capture even more of the observed data (Figs S7 and S8). 

#### _Comparisons to the EPA-modified Verner model_ 

The human models were also used to calculate the PODHED for the cardiovascular and hepatic endpoints evaluated in the EPA’s 

**Table 1.** Mean (95% CI) TK parameters for PFOS and PFOA fit to nonhuman primate data and scaled to humans. 

|**Species**|**Type of variable**|**Variable**|**Name**|**Mean (**|**95**%**CI)**|**Source**|
|---|---|---|---|---|---|---|
|||||**PFOS**|**PFOA**||
|Nonhum|an primate||||||
||Physiological|Body weight (kg)|_BW_|5<sup>a</sup>|4.1<sup>a</sup>|Butenhoff et al. (2004);<br>Chang et al. (2012);|
|||||||Seacat et al. (2002)|
|||Cardiac blood output (L/h/kg<sup>0.74</sup>)|_QCC_|19.8|19.8|<br>Wambaugh et al. (2013)|
|||Fraction of cardiac output to filtrate|_QfilC_|0.15|0.15|Wambaugh et al. (2013)|
|||Volume of filtrate compartment (L/kg)|_VfilC_|4.00E-04|4.00E-04|Loccisano et al. (2011)|
||Chemical-specific|Bioavailability|_bioAv_|0.9|0.32 (0.20, 0.46)|US EPA (2024a)(PFOS)<br>Optimized (PFOA)|
|||Volume of distribution<br>central compartment (L/kg)|_VCC_|0.24 (0.24, 0.25)|0.23 (0.18, 0.29)|Optimized|
|||Saturable resorption rate (mg/h/kg)|_Tmc_|2.5 (2.31, 2.80)|0.28 (0.17, 0.53)|Optimized|
|||Saturable resorption affinity (mg/L)<br>Proportion of free compound in serum|_Kt_<br>_Free_|0.004 (0.003, 0.004)<br>4.50E-03|0.017 (0.010, 0.041)<br>1.20E-3|Optimized<br>Smeltz et al. (2023)|
|||Rate from central to<br>second compartment (1/h)|_k12_|3.3|3.3|Andersen et al. (2006)|
|||Rate from second to<br>central compartment (1/h)|_k21_|3.4|3.4|Andersen et al. (2006)|
|||<br>Rate from gut to central<br>compartment (1/h)|_ka_|132|230|Wambaugh et al. (2013)|
|Human|||||||
||Physiological|Body weight (kg)<br>|_BW_|70|70|Loccisano et al. (2011)|
|||Cardiac blood output (L/h/kg<sup>0.74</sup>)|_QCC_|12.5|12.5|Loccisano et al. (2011)|
||Chemical-specific|Bioavailability|_bioAv_|0.9|0.9|US EPA (2024a,2024b)|
|||Saturable resorption rate (mg/h/kg)|_Tmc_|1.07|0.54|<br>Optimized|
|||<br>Saturable resorption affinity (mg/L)|_Kt_|0.004|0.008<sup>b</sup>|Optimized (nonhuman<br>primate)|
|||Half-life (years)|_T1/2_|3.4|2.7|Li et al. (2018)|



> a The code uses the average body weight for each nonhuman primate or group of nonhuman primates as reported in the original studies. 

> b If the bioavailability is set to 90% for the nonhuman primate model of PFOA, the _Tmc_ and _Kt_ values for the nonhuman primates are 0.15 mg/h/kg and 0.008 mg/ L, respectively. For the human model, a set value of 0.008 mg/L for _Kt_ was used as it is representative of the higher bioavailability considered more typical for intake of food and water.

<!-- PAGE 5 -->
### [Page 5]
_Toxicological Sciences_ , 2025, Vol 207, Issue 1 | 143 



<!-- Start of picture text -->
A B<br>4 4<br>3 3<br>2 2<br>1<br>0 0<br>Observed Concentration<br>1 1 8<br>o<br>2 2<br>-2 -1 0 1 2 3 4 -2 -1 0 1 2 3 4<br>Predicted Concentration Predicted Concentration<br><!-- End of picture text -->

Fig. 2. Model predictions for training data of serum concentrations (log10 µg/mL) of a) PFOS and b) PFOA in cynomolgus monkeys; dashed lines represent ± one-half log10. 

Human Health Toxicity Assessments for PFOS and PFOA. The PODHEDs calculated at steady state for a 70 kg individual using the model presented in this study were approximately 1.5 times greater than those calculated with the Verner model (US EPA 2024a, 2024b) as shown in Table 2. The differences at doses below saturation arise from the faster clearance predicted by the human models developed herein compared with the clearance in the EPA-modified Verner model. 

### **Application to PFHxS** 

After validating the described approach, a human model for PFHxS was developed using available nonhuman primate data (Chang 2020d). Only IV data were available for PFHxS, and thus the same chemical-specific parameters ( _bioAv, Free_ , _k12_ , and _k21_ ) were held constant in the model as for the previous compounds in addition to the rate of absorption from the stomach ( _ka_ ). For PFHxS, _Tmc_ and _Kt_ were also determined to be too highly correlated to be estimated independently. The _ka_ and _Kt_ parameters were assumed to be similar to those for PFOS (Table 3), and _VCC_ and _Tmc_ were fitted to the data. The optimized model parameters are shown in Table 3, and the final model predictions for the nonhuman primate model were within a factor of 2 of the observed serum levels for 86% of the data points, with an MSLE of 0.17 (Figs S9 and S10). The animal model was scaled to human using a half-life of 5.3 years, resulting in a _Tmc_ of 0.47 mg/h/kg (Li et al. 2018). Notably, for doses well below saturation ( _<_ 1000 mg/kg BW/day), the human model is associated with a clearance of approximately 0.06 mL/kg-day for a 70 kg adult, which falls between the clearance values applied for males and females outside of reproductive ages (0.041 mL/kg-day) and females of reproductive ages (0.072 mL/kg-day) in the EPA’s derivation of PFHxS candidate toxicity values (US EPA 2025). 

## Discussion 

We developed an approach that improves our ability to connect PFAS exposures to endpoints of concern for less studied PFAS compounds through the adaptation of published TK models for 

nonhuman primates for use in humans over the age of 20. Our results suggest that only a few key parameters ( _BW_ , _QCC_ , _T1/2_ ) are needed to adapt the Wambaugh nonhuman primate compartment model to be useful for human inferences, minimizing the reliance on human-specific data for new TK model development. A nonhuman primate PBTK model was similarly adapted in Loccisano et al. (2011), and although PBTK models are generally preferred over compartment approaches, a compartment modelbased approach is an attractive alternative herein considering the need for simplicity when conducting dosimetry calculations for PFAS compounds with minimal human TK data. The Wambaugh model was the foundation of our approach because of its simplicity and its demonstrated use in regulatory works (US EPA 2024a, 2024b). Although PBTK models have been developed for PFOA, PFOS, and PFHxS, and these models can estimate additional tissue concentrations beyond the serum, serum contains the major proportion of the compounds in question (Forsthuber et al. 2020). Furthermore, our knowledge of dietary exposure to PFAS is primarily informed by serum data (Calafat et al. 2007 2019). Thus, the simplicity of a multi-compartment model for this approach makes it fit for use. 

A specific effort was made in this study to identify correlations among parameters that would impair the inference process. These correlations can lead to extremely large credible intervals in the estimates of the MCMC inference process, as can be observed in Wambaugh et al. (2013). The parameters deemed identifiable were associated with much narrower credible intervals. Sensitivity analyses were conducted for the parameters held constant in the fitting process, and although some parameters ( _k12, k21, ka_ ) were found to have a minimal impact on model outputs for the tested values (Tables S2 and S3), the values for _Free_ and bioavailability for each compound were found to have a strong influence on results. The _Free_ parameters in these models were selected based on protein binding assay findings (Smeltz et al. 2023). An advantage of this approach is the availability of compound-specific _Free_ values for multiple PFAS compounds of interest. However, the binding efficacy may be higher in vitro than in vivo. Different _Free_ values will correspond to different

<!-- PAGE 6 -->
### [Page 6]
144 | Dean et al. 



<!-- Start of picture text -->
30<br>%.c<br>10<br>Predicted Serum Level ( p b)<br>3<br>3 10 30<br>Observed Serum Level (ppb)<br>Fig. 3. Observed and predicted PFOS serum levels (ppb) for NHANES 1999 Observed and predicted PFOS serum levels (ppb) for NHANES 1999<br>to 2017; dashed lines represent ± one-half log10.10..<br>5<br>Predicted Serum Level ( p b)<br>3 10<br>Observed Serum Level (ppb)<br><!-- End of picture text -->

Fig. 3. Observed and predicted PFOS serum levels (ppb) for NHANES 1999 Observed and predicted PFOS serum levels (ppb) for NHANES 1999 to 2017; dashed lines represent ± one-half log10.10.. 

Fig. 4. Observed and predicted PFOA serum levels (ppb) for NHANES 1999 to 2017; dashed lines represent ± one-half log10. 

resorption parameters, and the model can be adjusted accordingly with newer findings. The bioavailability parameter directly impacts the amount of the compounds that enter the serum, and the default values were chosen to reflect the high absorption observed in animals after ingestion exposures (US EPA 2024a, 2024b). The parameter could be adjusted in future applications to reflect dosing scenario and experiment-specific conditions as needed. 

Our approach was validated using NHANES biomonitoring data. Both the PFOS and PFOA TK models were able to simulate the observed trends in US serum concentrations between the 1940s and 2000s (Figs S7 and S8). In addition to evaluating the TK 

models’ ability to simulate general biomonitoring data trends over time, the feasibility of the underlying exposure models was also considered. Wong et al. (2014) assumed a constant exposure between 1990 and 1998, and the optimized intake was found to be 3.9 ng PFOS/kg BW/day. The optimized exposure model herein estimated a peak weight-based intake of 14 ng PFOS/kg BW/day in 1990 that fell to 2.5 ng PFOS/kg BW/day in 1998 for the same population. The earliest available serum data for both approaches was recorded in 1999, thus limiting the inferences that can be made about the weight-based intakes in previous years. Accordingly, the lower 1998 estimated intake herein may be due to the use of an exposure model that predicts higher exposures pre-1998, or the use of a TK model with a slower clearance rate compared with Wong et al. (2014). The estimated PFOA peak intake in 1998 of 1.1 ng PFOA/kg BW/day was also lower than previous estimates of approximately 6 ng PFOA/kg BW/day (Dzierlenga et al. 2020). This could also be explained by a slower clearance rate in our TK model compared with the Dzierlenga et al. (2020) model that included menstrual clearance and agedependent glomerular filtration rates. Importantly, these comparisons highlight the variability in reverse dosimetry estimates using NHANES data that can arise from exposure and TK model selection. 

We also calculated the PODHED for the cardiovascular and hepatic endpoints evaluated in the EPA’s Human Health Toxicity Assessments to validate our approach. In that regard, our estimated human equivalent doses for the selected PODs were approximately 1.5 times greater than those estimated by the Verner model at steady state for a 70 kg individual (US EPA 2024a, 2024b). The differences arise from the higher volume of distribution estimated in our Wambaugh-adapted models compared with the one-compartment EPA-modified Verner model. If we consider the full spectrum of possible exposure doses, the EPAmodified Verner model would not be applicable for doses past the point of saturation, whereas the Wambaugh-adapted model incorporates saturable absorption and could be used. These comparisons suggest that the TK models developed with our approach are sufficiently similar to those applied for regulatory purposes, while being able to incorporate the more advanced saturable resorption mechanism, which increases the model’s utility for making inferences from animal datasets and extreme human exposure scenarios. The utility of the approach is further demonstrated by its application to PFHxS, which yielded a model with a clearance rate between those selected for males and females outside of reproductive ages and females of reproductive age in the EPA’s derivation of PFHxS candidate toxicity values (US EPA 2025). 

This work demonstrates the feasibility of our approach to adapt TK models from nonhuman primates to humans with a level of accuracy. The application and continued development of this approach for PFAS compounds of interest will advance our ability to relate dietary PFAS to endpoints of concern. The inclusion of a development compartment to model gestational and lactational exposure to infants is a noted area for future improvement, as this is needed for baby and infant applications. Modifications were made to the Wambaugh animal model to account for gestation, lactation, and postweaning phases in other works (US EPA 2024a, 2024b), and the applicability of these modifications for our proposed approach to adapting nonhuman primate models for humans needs to be further explored. To our knowledge, there are limited additional nonhuman primate studies available in the literature for the wide range of PFAS compounds found in the diet (Olsen et al. 2009; Chang 2020c). Our

<!-- PAGE 7 -->
### [Page 7]
_Toxicological Sciences_ , 2025, Vol 207, Issue 1 | 145 

**Table 2.** Comparing the PODHEDs calculated with the Verner model in (US EPA 2024a, 2024b) for PFOS and PFOA to estimates calculated with the human-adapted Wambaugh model. 

|**Compound**|**Effect**|**Outcome**|**Study**|**POD (mg/L)**|**EPA’s PODHED**<br>**(mg/kg/day)**|**Our PODHED**<br>**(mg/kg/day)**|
|---|---|---|---|---|---|---|
|PFOS|Cardiovascular|Increased total choles-|Dong et al. (2019)|0.009|1.20E-06|1.43E-06|
|||terol|Steenland et al. (2009)|0.010|1.22E-06|1.45E-06|
||||Lin et al. (2019)|0.067|8.51E-06|1.02E-05|
||Hepatic|Elevated ALT|Gallo et al. (2012)|0.057|7.27E-06|8.68E-06|
||||Nian et al. (2019)|0.015|1.94E-06|2.31E-06|
|||Increased individual<br>cell necrosis|Butenhoff et al. (2012)|27|3.45E-03|4.43E-03|
|PFOA|Cardiovascular|Increased total choles-|Dong et al. (2019)|0.002|2.75E-07|4.15E-07|
|||terol|Steenland et al. (2009)|0.004|5.10E-07|7.70E-07|
||||Lin et al. (2019)|0.005|6.34E-07|9.57E-07|
||Hepatic|Elevated ALT|Gallo et al. (2012)|0.02|2.15E-06|3.25E-06|
||||Darrow et al. (2016)|0.07|7.92E-06|1.20E-05|
||||Nian et al. (2019)|0.004|4.51E-07|6.82E-07|
|||Increased focal<br>necrosis|Loveless et al. (2008)|10|1.20E-03|1.84E-03|
|||Increased individual<br>cell necrosis|Loveless et al. (2008)|36|4.32E-03|6.86E-03|
|||Increased hepatocyte<br>single cell death|NTP (2020)|100|1.20E-02|2.10E-02|
|||Increased necrosis|NTP (2020)|26.9|3.23E-03|5.06E-03|



**Table 3.** Optimized TK parameters and 95% CI for nonhuman primate and human models of PFHxS. 

|**Species**|**Type of variable**|**Variable**|**Name**|**Mean (95**%**CI)**|**Source**|
|---|---|---|---|---|---|
|Nonhum|an primate|||||
||Physiological<br>Chemical-specific|Body weight (kg)<br>Cardiac blood output (L/h/kg<sup>0.74</sup>)<br>Fraction of cardiac output to filtrate<br>Volume of filtrate compartment (L/Kg)<br>Bioavailability|_BW_<br>_QCC_<br>_QfilC_<br>_VfilC_<br>_bioAv_|5<br>19.8<br>0.15<br>4.00E-04<br>0.9|Chang (2020d)<br>Wambaugh et al. (2013)<br>Wambaugh et al. (2013)<br>Loccisano et al. (2011)<br>Assumed (PFOS)|
|||Volume of distribution central compartment (L/kg)|_VCC_|0.17 (0.16, 0.20)|Optimized|
|||Saturable resorption rate (mg/h/kg)<br>Saturable resorption affinity (mg/L)<br>Proportion of free compound in serum|_Tmc_<br>_Kt_<br>_Free_|0.21 (0.18, 0.25)<br>0.004<br>0.0009|Optimized<br>Assumed (PFOS)<br>Smeltz et al. (2023)|
|||Rate from central to second compartment (1/h)|_k12_|3.3|Andersen et al. (2006)|
|||Rate from second to central compartment (1/h)|_k21_|3.4|Andersen et al. (2006)|
|||Rate from gut to central compartment (1/h)|_ka_|132|Wambaugh et al. (2013)|
|Human||||||
||Physiological|Body weight (kg)<br>Cardiac blood output (L/h/kg<sup>0.74</sup>)|_BW_<br>_QCC_|70<br>12.5|Loccisano et al. (2011)<br>Loccisano et al. (2011)|
||Chemical-specific|Saturable resorption rate (mg/h/kg)<br>Half-life (years)|_Tmc_<br>_T1/2_|0.47<br>5.3|Optimized<br>Li et al. (2018)|



framework could also be used to leverage data from other animal studies, with the determination of the necessary species-specific adaptations to the approach. Accommodating data from test animals with less physiological similarities to humans will likely require the scaling of additional parameters beyond those identified in the nonhuman primate–human framework. The results presented herein can be used to guide the determination of the species-specific parameters for scaling and to calibrate the final model forms. 

## Supplementary material 

Supplementary material is available at _Toxicological Sciences_ online. 

## Funding 

This work was carried out under official FDA duties and contract (75F40123D00017 with Goldbelt C6, LLC (R.P.)). 

Conflicts of interest. None declared. 

## Acknowledgments 

The authors would like to thank other subject matter experts in the Human Foods Program for their input including Jacqueline Heilman and Lynn Crosby. We also would like to thank Sherri Dennis for her leadership and review of the paper. We thank Sue Chang for sharing the raw published data files. We also acknowledge the experts provided by Versar, Inc. [HHSF223201700015B] for their consultation on our approach that informed this study. 

## References 

- Andersen ME, Clewell HJ 3rd, Tan YM, Butenhoff JL, Olsen GW. 2006. Pharmacokinetic modeling of saturable, renal resorption of perfluoroalkylacids in monkeys—probing the determinants of long plasma half-lives. Toxicology. 227:156–164. 

- ATSDR. 2021. Toxicological profile for perfluoroalkyls. Atlanta, GA: U.S. Department of Health and Human Services, Public Health Service.

<!-- PAGE 8 -->
### [Page 8]
146 | Dean et al. 

- Baron KT. 2023. Mrgsolve: simulate from ode-based models. R package version 1.3.0. https://mrgsolve.org/docs/ 

- Brochot C, Casas M, Manzano-Salgado C, Zeman FA, Schettgen T, Vrijheid M, Bois FY. 2019. Prediction of maternal and foetal exposures to perfluoroalkyl compounds in a spanish birth cohort using toxicokinetic modelling. Toxicol Appl Pharmacol. 379:114640. 

- Butenhoff JL, Chang S-C, Olsen GW, Thomford PJ. 2012. Chronic dietary toxicity and carcinogenicity study with potassium perfluorooctanesulfonate in sprague dawley rats. Toxicology. 293:1–15. 

- Butenhoff JL, Kennedy GL Jr., Hinderliter PM, Lieder PH, Jung R, Hansen KJ, Gorman GS, Noker PE, Thomford PJ. 2004. Pharmacokinetics of perfluorooctanoate in cynomolgus monkeys. Toxicol Sci. 82:394–406. 

- Calafat AM, Kato K, Hubbard K, Jia T, Botelho JC, Wong LY. 2019. Legacy and alternative per- and polyfluoroalkyl substances in the U.S. General population: paired serum-urine data from the 2013-2014 National Health and Nutrition Examination Survey. Environ Int. 131:105048. 

- Calafat AM, Wong LY, Kuklenyik Z, Reidy JA, Needham LL. 2007. Polyfluoroalkyl chemicals in the U.S. Population: data from the national health and nutrition examination survey (NHANES) 2003-2004 and comparisons with nhanes 1999-2000. Environ Health Perspect. 115:1596–1602. 

- Chang SC. 2020a. Final report on the a analytical laboratory report from the 26-week capsule toxicity study with perfluorooctanesulfonate (PFOS) in liver and serum samples to 3M corporation. Personal Communication Available from FDA upon request. 

- Chang SC. 2020b. Final report on the a pharmacokinetic study of potassium perfluorooctanesulfonate in the cynomolgus monkey to 3M corporation. Personal Communication Available from FDA upon request. 

- Chang SC. 2020c. Final report on the a pharamcokinetic study of perfluorobutanesulfonate in the cynolomogous monkey to 3M corporation. Personal Communication Available from FDA upon request. 

- Chang SC. 2020d. Final report on the a pharmacokinetic study of potassium perfluorohexanasulfonate in the cynomolgus monkey to 3M corporation. Personal Communication Available from FDA upon request 

- Chang SC, Noker PE, Gorman GS, Gibson SJ, Hart JA, Ehresman DJ, Butenhoff JL. 2012. Comparative pharmacokinetics of perfluorooctanesulfonate (PFOS) in rats, mice, and monkeys. Reprod Toxicol. 33:428–440. 

- Chen TC, Clark J, Riddles MK, Mohadjer LK, Fakhouri THI. 2020. National health and nutrition examination survey, 2015–2018: sample design and estimation procedures. National Center for Health Statistics. Vital Health Stat 2. (184):1–35. https://pubmed. ncbi.nlm.nih.gov/33663649/ 

- Chen TC, Parker JD, Clark J, Shin HC, Rammon JR, Burt LV. 2018. National health and nutrition examination survey: estimation procedures, 2011–2014. National Center for Health Statistics. Vital Health Stat 2. (177):1–26. https://pubmed.ncbi.nlm.nih.gov/29775431/ 

- Chou W-C, Lin Z. 2019. Bayesian evaluation of a physiologically based pharmacokinetic (PBPK) model for perfluorooctane sulfonate (PFOS) to characterize the interspecies uncertainty between mice, rats, monkeys, and humans: Development and performance verification. Environ Int. 129:408–422. 

- Chou WC, Lin Z. 2021. Development of a gestational and lactational physiologically based pharmacokinetic (PBPK) model for perfluorooctane sulfonate (PFOS) in rats and humans and its implications in the derivation of health-based toxicity values. Environ Health Perspect. 129:37004. 

- Darrow LA, Groth AC, Winquist A, Shin H-M, Bartell SM, Steenland K. 2016. Modeled perfluorooctanoic acid (PFOA) exposure and liver function in a mid-Ohio valley community. Environ Health Perspect. 124:1227–1233. 

- Domingo JL, Nadal M. 2017. Per- and polyfluoroalkyl substances (PFASs) in food and human dietary intake: a review of the recent scientific literature. J Agric Food Chem. 65:533–543. 

- Dong Z, Wang Hao, Yu YY, Li YB, Naidu R, Liu Y. 2019. Using 20032014 U.S. NHANES data to determine the associations between per- and polyfluoroalkyl substances and cholesterol: Trend and implications. Ecotoxicol Environ Saf. 173:461–468. 

- Dzierlenga MW, Moreau M, Song G, Mallick P, Ward PL, Campbell JL, Housand C, Yoon M, Allen BC, Clewell HJ 3rd, _et al._ 2020. Quantitative bias analysis of the association between subclinical thyroid disease and two perfluoroalkyl substances in a single study. Environ Res. 182:109017. 

- East A, Dawson DE, Brady S, Vallero DA, Tornero-Velez R. 2023. A scoping assessment of implemented toxicokinetic models of perand polyfluoro-alkyl substances, with a focus on onecompartment models. Toxics. 11:163. 

- Fabrega F, Kumar V, Benfenati E, Schuhmacher M, Domingo JL, Nadal M. 2015. Physiologically based pharmacokinetic modeling of perfluoroalkyl substances in the human body. Toxicol Environ Chem. 97:814–827. 

- Forsthuber M, Kaiser AM, Granitzer S, Hassl I, Hengstschlager M, € Stangl H, Gundacker C. 2020. Albumin is the major carrier protein for PFOS, PFOA, PFHxS, PFNA and PFDA in human plasma. Environ Int. 137:105324. 

- Gallo V, Leonardi G, Genser B, Lopez-Espinosa M-J, Frisbee SJ, Karlsson Lee, Ducatman AM, Fletcher T. 2012. Serum perfluorooctanoate (PFOA) and perfluorooctane sulfonate (PFOS) concentrations and liver function biomarkers in a population with elevated PFOA exposure. Environ Health Perspect. 120:655–660. 

- Gleason JA, Cooper KR, Klotz JB, Post GB, Van Orden G. 2015. Healthbased maximum contaminant level support document: perfluorononanoic acid (PFNA). New Jersey Drinking Water Quality Institute, Health Effects Subcommittee. https://www.nj.gov/dep/ watersupply/g_boards_dwqi.html 

- Goeden HM, Greene CW, Jacobus JA. 2019. A transgenerational toxicokinetic model and its use in derivation of Minnesota PFOA water guidance. J Expo Sci Environ Epidemiol. 29:183–195. 

- Kim S-J, Choi E-J, Choi G-W, Lee Y-B, Cho H-Y. 2019. Exploring sex differences in human health risk assessment for PFNA and PFDA using a PBPK model. Arch Toxicol. 93:311–330. 

- Kim SJ, Shin H, Lee YB, Cho HY. 2018. Sex-specific risk assessment of PFHxS using a physiologically based pharmacokinetic model. Arch Toxicol. 92:1113–1131. 

- Li Y, Fletcher T, Mucs D, Scott K, Lindh CH, Tallving P, Jakobsson K. 2018. Half-lives of PFOS, PFHxS and PFOA after end of exposure to contaminated drinking water. Occup Environ Med. 75:46–51. 

- Lin D, Cardenas A, Hauser R, Gold DR, Kleinman KP, Hivert M-F, Fleisch AF, Calafat AM, Webster TF, Horton ES, _et al._ 2019. Perand polyfluoroalkyl substances and blood lipid levels in pre-diabetic adults-longitudinal analysis of the diabetes prevention program outcomes study. Environ Int. 129:343–353. 

- Loccisano AE, Campbell JL, Andersen ME, Clewell HJ. 2011. Evaluation and prediction of pharmacokinetics of PFOA and PFOS in the monkey and human using a PBPK model. Regul Toxicol Pharmacol. 59:157–175. 

- Loveless SE, Hoban D, Sykes G, Frame SR, Everds NE. 2008. Evaluation of the immune system in rats and mice administered linear ammonium perfluorooctanoate. Toxicol Sci. 105:86–96.

<!-- PAGE 9 -->
### [Page 9]
_Toxicological Sciences_ , 2025, Vol 207, Issue 1 | 147 

- Lumley T. 2004. Analysis of complex survey samples. J Stat Soft. 9:1–19. 

- Lumley T, Gao P, Schneider B. 2023. Survey: analysis of complex survey samples. https://cran.r-project.org/web/packages/survey/ index.html 

- Mirel LB, Mohadjer LK, Dohrmann SM, Clark J, Burt CL, Johnson CL, Curtin LR. 2013. National health and nutrition examination survey: estimation procedures, 2007–2010. National Center for Health Statistics. Vital Health Stat 2. (159):1–17. 

- Nian Min, Li Q-Q, Bloom M, Qian ZM, Syberg KM, Vaughn MG, Wang S-Q, Wei Qi, Zeeshan M, Gurram N, _et al._ 2019. Liver function biomarkers disorder is associated with exposure to perfluoroalkyl acids in adults: Isomers of C8 health project in China. Environ Res. 172:81–88. 

- NTP. 2020. NTP technical report on the toxicology and carcinogenesis studies of perfluorooctanoic acid (CASRN 335-67-1) administered in feed to Sprague Dawley (Hsd:Sprague Dawley SD) rats [NTP]. (Technical Report 598). Research Triangle Park, NC. 

- Olsen G, Chang SC, Noker PE, Gorman GS, Ehresman DJ, Lieder P, Butenhoff JL. 2009. A comparison of the pharmacokinetics of perfluorobutanesulfonate (PFBS) in rats, monkeys, and humans. Toxicology. 256:65–74. 

- Pizzurro DM, Seeley M, Kerper LE, Beck BD. 2019. Interspecies differences in perfluoroalkyl substances (PFAS) toxicokinetics and application to health-based criteria. Regul Toxicol Pharmacol. 106:239–250. 

- Ruark CD, Song G, Yoon M, Verner M-A, Andersen ME, Clewell HJ, Longnecker MP. 2017. Quantitative bias analysis for epidemiological associations of perfluoroalkyl substance serum concentrations and early onset of menopause. Environ Int. 99:245–254. 

- Seacat AM, Thomford PJ, Hansen KJ, Olsen GW, Case MT, Butenhoff JL. 2002. Subchronic toxicity studies on perfluorooctanesulfonate potassium salt in cynomolgus monkeys. Toxicol Sci. 68:249–264. 

- Smeltz M, Wambaugh JF, Wetmore BA. 2023. Plasma protein binding evaluations of per- and polyfluoroalkyl substances for categorybased toxicokinetic assessment. Chem Res Toxicol. 36:870–881. 

- Soetaert K, Petzoldt T. 2010. Inverse modelling, sensitivity, and Monte Carlo analysis in R using package FME. J Stat Soft. 33:1–28. 

- Steenland K, Tinker S, Frisbee S, Ducatman A, Vaccarino V. 2009. Association of perfluorooctanoic acid and perfluorooctane sulfonate with serum lipids among adults living near a chemical plant. Am J Epidemiol. 170:1268–1278. 

- Sundstrom M, Chang S-C, Noker PE, Gorman GS, Hart JA, Ehresman € DJ, Bergman Åke, Butenhoff JL. 2012. Comparative pharmacokinetics of perfluorohexanesulfonate (PFHxS) in rats, mice, and monkeys. Reprod Toxicol. 33:441–451. 

- Sweeney LM. 2022. Physiologically based pharmacokinetic (PBPK) modeling of perfluorohexane sulfonate (PFHxS) in humans. Regul Toxicol Pharmacol. 129:105099. 

- Tan Y-M, Clewell HJ, Andersen ME. 2008. Time dependencies in perfluorooctylacids disposition in rat and monkeys: A kinetic analysis. Toxicol Lett. 177:38–47. 

- US EPA. 2021. Human health toxicity values for perfluorobutane sulfonic acid (casrn 375-73-5) and related compound potassium perfluorobutane sulfonate (casrn 29420-49-3). Washington, DC: U.S. Environmental Protection Agency. EPA/600/R-20/345F. 

- US EPA. 2022. IRIS toxicological review of perfluorobutanoic acid (PFBA, casrn 375-22-4) and related salts. Washington, DC: U.S. Environmental Protection Agency. EPA/635/R-22/277Fa. 

- US EPA. 2023. IRIS toxicological review of perfluorohexanesulfonic acid (PFHxS, casrn 335-46-4) and related salts (public comment and external review draft). Washington, D.C.: U.S. Environmental Protection Agency. EPA/635/R-23/148a. 

- US EPA. 2024a. Final human health toxicity assessment for perfluorooctane sulfonic acid (PFOS) and related salts. Washington, D.C.: U.S. Environmental Protection Agency. EPA Document Number: 815R24007. 

- US EPA. 2024b. Final human health toxicity assessment for perfluorooctanoic acid (PFOA) and related salts. Washington, D.C.: U.S. Environmental Protection Agency. EPA Document Number: 815R24006. 

- US EPA. 2024c. IRIS toxicological review of perfluorononanoic acid (PFNA) and related salts (public comment and external review draft). Washington D.C.: U.S. Environmental Protection Agency. EPA/635/R-24/031. 

- US EPA. 2025. IRIS toxicological review of perfluorohexanesulfonic acid (PFHXS, casrn 335-46-4) and related salts. Washington D.C.: U.S Environmental Protection Agency. EPA/635/R-25/012Fa. 

- Verner M-A, Ngueta G, Jensen ET, Fromme H, Volkel W, Nygaard UC, € Granum B, Longnecker MP. 2016. A simple pharmacokinetic model of prenatal and postnatal exposure to perfluoroalkyl substances (PFASs). Environ Sci Technol. 50:978–986. 

- Wambaugh JF, Barton HA, Setzer RW. 2008. Comparing models for perfluorooctanoic acid pharmacokinetics using bayesian analysis. J Pharmacokinet Pharmacodyn. 35:683–712. 

- Wambaugh JF, Setzer RW, Pitruzzello AM, Liu Jie, Reif DM, Kleinstreuer NC, Wang NCY, Sipes N, Martin M, Das K, _et al._ 2013. Dosimetric anchoring of in vivo and in vitro studies for perfluorooctanoate and perfluorooctanesulfonate. Toxicol Sci. 136:308–327. 

- Wong F, MacLeod M, Mueller JF, Cousins IT. 2014. Enhanced elimination of perfluorooctane sulfonic acid by menstruating women: evidence from population-based pharmacokinetic modeling. Environ Sci Technol. 48:8807–8814. 

- World Health Organization. 2010. Characterization and application of physiologically based pharmacokinetic models in risk assessment. https://www.who.int/publications/i/item/9789241500906. 

> © The Author(s) 2025. Published by Oxford University Press on behalf of the Society of Toxicology. 

> This is an Open Access article distributed under the terms of the Creative Commons Attribution License (https://creativecommons.org/licenses/by/4.0/ ), which permits unrestricted reuse, distribution, and reproduction in any medium, provided the original work is properly cited. Toxicological Sciences, 2025, 207, 139–147 

https://doi.org/10.1093/toxsci/kfaf087 Research article