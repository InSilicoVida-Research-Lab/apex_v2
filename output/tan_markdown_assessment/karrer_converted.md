Research 

A Section 508–conformant HTML version of this article is available at https://doi.org/10.1289/EHP2739. 

# Physiologically Based Pharmacokinetic (PBPK) Modeling of the Bisphenols BPA, BPS, BPF, and BPAF with New Experimental Metabolic Parameters: Comparing the Pharmacokinetic Behavior of BPA with Its Substitutes 

Cecile Karrer,<sup>1</sup> Thomas Roiss,<sup>1</sup> Natalie von Goetz,<sup>1</sup> Darja Gramec Skledar,<sup>2</sup> Lucija Peterlin Maši�c,<sup>2</sup> and Konrad Hungerbühler<sup>1</sup> 

1Institute for Chemical and Bioengineering, Swiss Federal Institute of Technology Zurich, Zürich, Switzerland 2Faculty of Pharmacy, University of Ljubljana, Ljubljana, Slovenia 

BACKGROUND: The endocrine disrupting chemical bisphenol A (BPA) has been facing stricter regulations in recent years. BPA analogs, such as the bisphenols S, F, and AF (BPS, BPF, and BPAF) are increasingly used as replacement chemicals, although they were found to exert estrogenic effects similar to those of BPA. Research has shown that only the parent compounds have affinity to the estrogen receptors, suggesting that the pharmacokinetic behavior of bisphenols (BPs) can influence their potency. 

OBJECTIVES: Our goal was to compare the pharmacokinetic behaviors of BPA, BPS, BPF, and BPAF for different age groups after environmentally relevant external exposures by taking into account substance-specific metabolism kinetics and partitioning behavior. This comparison allowed us to investigate the consequences of replacing BPA with other BPs. METHODS: We readjusted a physiologically based pharmacokinetic (PBPK) model for peroral exposure to BPA and extended it to include dermal exposure. We experimentally assessed hepatic and intestinal glucuronidation kinetics of BPS, BPF, and BPAF to parametrize the model for these BPs and calibrated the BPS model with a biomonitoring study. We used the PBPK models to compare resulting internal exposures and focused on females of childbearing age in a two-dimensional Monte Carlo uncertainty analysis. RESULTS: Within environmentally relevant concentration ranges, BPAF and BPS were glucuronized at highest and lowest rates, respectively, in the intestine and the liver. The predominant routes of BPS and BPAF exposure were peroral and dermal exposure, respectively. The calibration of the BPS model with measured concentrations showed that enterohepatic recirculation may be important. Assuming equal external exposures, BPS exposure led to the highest internal concentrations of unconjugated BPs. CONCLUSIONS: Our data suggest that the replacement of BPA with structural analogs may not lower the risk for endocrine disruption. Exposure to both BPS and BPAF might be more critical than BPA exposure, if their respective estrogenic potencies are taken into account. https://doi.org/ 10.1289/EHP2739 

## Introduction 

Bisphenol A (BPA) is a high production–volume chemical and is used in many consumer products, such as polycarbonate plastics, epoxy resins, and thermal paper (Vandenberg et al. 2007). BPA and its derivatives were found in more than 90% of over 2,500 urine samples in a U.S. study conducted between 2003 and 2004 (Calafat et al. 2008). European Union (EU) countries also face widespread BPA exposure, as shown by the detection frequency of over 90% in urinary samples of 600 child–mother pairs from six EU member states (Covaci et al. 2015). There is growing evidence that BPA exerts endocrine-disrupting effects (Rubin 2011), and therefore BPA has been facing stricter regulations in recent years. Since 2011, the EU has prohibited the use of BPA in polycarbonate baby bottles and set a migration limit of 0:6 mg=kg for the production of plastics (EC 2011a, 2011b). France has expanded these restrictions and prohibited the use of BPA in all food contact material since 2015 (French National Assembly and Senate 2010). In the United States, where the use of BPA in food contact material is generally permitted, there are restrictions for baby bottles, sippy cups, and infant formula packaging (U.S. FDA 2013, 2014). 

Address correspondence to N. von Goetz, Vladimir-Prelog-Weg 1, 8093 Zürich, Switzerland. Telephone: +41 58 469 6150. Email: natalie.von.goetz@ chem.ethz.ch 

Supplemental Material is available online (https://doi.org/10.1289/EHP2739). Received 25 August 2017; Revised 11 May 2018; Accepted 22 May 2018; Published 10 July 2018. 

Note to readers with disabilities: EHP strives to ensure that all journal content is accessible to all readers. However, some figures and Supplemental Material published in EHP articles may not conform to 508 standards due to the complexity of the information being presented. If you need assistance accessing journal content, please contact ehponline@niehs.nih.gov. Our staff will work with you to assess and meet your accessibility needs within 3 working days. 

Due to the stricter regulation of BPA, industry has increased the use of replacement substances, such as the structurally similar bisphenols AF, AP, B, F, P, S, and Z. In the following, we focus on bisphenol S (BPS), bisphenol F (BPF), and bisphenol AF (BPAF), as BPS and BPF are extensively used, and BPAF has been found to exert comparatively high estrogenic and antiandrogenic potencies (Chen et al. 2016). In food samples from the United States, BPS was detected second most frequently after BPA (21% vs. 57%). BPF was detected in 10% of the samples, but when detected, the second highest average concentrations were found (Liao and Kannan 2013). BPAF was found in rather low concentrations, with an occurrence of 11% (Liao and Kannan 2013). Apart from food, BPS, BPF, and BPAF are present in indoor dust as ubiquitous contaminants (Liao et al. 2012a). Another source of exposure to BPS is thermal paper, because BPS has partially replaced BPA as a color developer (Thayer et al. 2016). This exposure route can substantially contribute to dermal exposure (Goldinger et al. 2015; Hormann et al. 2014; Liao et al. 2012b; Rocha et al. 2015). 

Several studies showed that BPS, BPF, and BPAF exert estrogenic effects and partly exert antiandrogenic and thyroiddisrupting effects with potencies similar to or higher than that of BPA (e.g., Fic et al. 2014; Rochester and Bolden 2015; Skledar et al. 2016). All studies reviewed by Chen et al. (2016) found that BPAF has a considerably higher potency than BPA in the estrogenic, antiandrogenic, and antiestrogenic assays conducted; for instance, the estrogenic potency of BPAF was found to be 7 to 13 times higher than the potency of BPA (Kitamura et al. 2005; Stossi et al. 2014). Evidence suggests that only unconjugated bisphenols (BPs) bind to estrogen receptors and that all are extensively metabolized. In the liver and the intestines, BPs are mainly metabolized to glucuronides, to a lesser extent to sulfates, and to a minor extent to hydroxylated compounds and other metabolites (reviewed by Gramec Skledar and Peterlin Maši�c 2016). Most BP glucuronides have been found to lack estrogenic activity (Li et al. 2013; Matthews et al. 2001; Skledar et al. 2016; Snyder et al. 

126(7) July 2018 

Environmental Health Perspectives 

077002-1 

2000). Yet, the BPA glucuronide (BPA-g) cannot be regarded as completely inactive, as it possibly induces adipocyte differentiation (Boucher et al. 2015). Also, deconjugation is possible and may even be more relevant in sensitive age groups, e.g., the fetus (in fetal compartments and placenta, b–glucuronidase-mediated deconjugation of BPA-g is substantial, according to Ginsberg and Rice 2009; Lucier et al. 1977; Paigen 1989). As deconjugation may also occur with BPA sulfate (BPA-s), the concentrations of unconjugated BPs could be considerably higher in fetal than in adult serum (Reed et al. 2005; Tobacman et al. 2002). 

The velocity and extent of the metabolism processes depend on the exposure route (Mielke et al. 2011). Therefore, it is important to consider the pharmacokinetic behavior specific to routes of exposure when assessing the exposure and risk of BPs. For this purpose, physiologically based pharmacokinetic (PBPK) modeling is valuable. Several publications already addressed PBPK modeling of BPA (Mielke and Gundert-Remy 2009; Teeguarden et al. 2005; Yang et al. 2015), and they considered exposure via the peroral and the dermal route (Mielke et al. 2011). However, to the best of our knowledge, no PBPK models are currently available for BPS, BPF, and BPAF, although exposure to these compounds is on the rise and their estrogenic potencies have been proven to be similar or even higher than the potency of BPA. 

In this paper, we have modified a PBPK model for peroral exposure to BPA developed by Yang et al. (2015) so that it corresponds well with a human kinetic data set (Thayer et al. 2015) and includes dermal exposure. We have then parametrized this optimized BPA model for BPS, BPF, and BPAF. To characterize the metabolic behavior of the BP analogs, we conducted in vitro experiments on their hepatic and intestinal glucuronidation. For estimating tissue-to-serum partition coefficients (PTS), we identified the most suitable and relevant quantitative structure–activity relationships (QSARs) from established models. A recent biomonitoring study on BPS was used to calibrate the kinetic profiles of BPS and BPS-g in the corresponding PBPK model (Oh et al. 2018). With a two-dimensional (2D) Monte Carlo (MC) analysis, we investigated the interindividual variability and uncertainty of the models. We used the PBPK models to compare internal exposures after peroral and dermal exposures for different age groups. This comparison allowed us to investigate possible consequences of a BPA replacement with its structural analogs. 

## Methods 

### PBPK Model for BPA 

To model the pharmacokinetic behavior of BPA, BPS, BPF, and BPAF (chemical structures, see Figure 1), we refined an eightcompartment PBPK model, which had been calibrated for BPA in human adults using biomonitoring data (Thayer et al. 2015; Yang et al. 2015). It consists of the compartments titled serum, liver, fat, skin, gonads, brain, “richly perfused tissue,” “slowly perfused tissue”, and two single-compartment submodules for 



<!-- Start of picture text -->
HO BPA OH BPF OH<br>F{3C CF3<br>HO BPAF OH BPS OH<br><!-- End of picture text -->

Figure 1. Chemical structures of BPA, BPS, BPF, and BPAF. Note: BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S. 

BPA-g and BPA-s in serum (see Figure 2). In the compartment titled “richly perfused tissue,” compartments were lumped with a perfusion greater than 0:1 mL=min=g tissue (heart, kidneys, small and large intestine, pancreas, spleen, and stomach), and in the compartment titled “slowly perfused tissue,” compartments were lumped with a perfusion smaller than 0:1 mL=min=g tissue (muscle and skeleton) (Edginton et al. 2006; ICRP 2002, see Table S1 for the aggregated parameters). When we translated the model from the language AsclX to R, we noticed a discrepancy between the model predictions and the biomonitoring data, which is shown in Figure S1A. Together with Dr. Yang, we identified a mistake in the published code: The constant for the maximum velocity of glucuronidation in the gut had not been scaled up according to the bodyweight (BW). Fixing the scaling error caused the aforementioned discrepancy, and we had to review and readjust the model parameters to the biomonitoring data. 

In a first step to readjust and further develop the PBPK model, we collected all studies that investigated the metabolism parameters used in the model and gathered data from different studies that measured the same metabolism routes (see Table S2). In the following, we used all possible combinations of parameter sets in the model and examined which parameter set reflected the biomonitoring data by Thayer et al. (2015) for unconjugated BPA in serum best. For this purpose, we calculated the mean relative deviation (MRD) and average fold error (AFE) to assess precision and bias of the model predictions using Equations 1 and 2 (Sheiner and Beal 1981), as done previously (Ito and Houston 2005; Vogt 2014; Yang et al. 2015). The resulting parameter set was used as the deterministic, basic PBPK model. We also compared model outputs with biomonitoring data for BPA-g and BPA-s to ensure plausibility in this respect [their MRD and AFE should also be low and not exceed a value of 2 (Edginton et al. 2006)]. 



In our calculations, predicted was the value predicted by our model and observed was the value measured by Thayer et al. (2015), averaged over all test persons per observation point respectively. Furthermore, n stands for the number of observation points (28 for BPA and 15 for BPA-g and BPA-s). We compared model output with biomonitoring data under two scenarios: one that incorporated an enterohepatic recirculation (EHR) rate of 10% into the model (Yang et al. 2015) and one that assumed that EHR was not occurring. 

For the PTS of BPA, just like Yang et al. (2015), we used parameters from the experimental study of Doerge et al. (2011), except for the skin compartment, which had not been investigated. As Pskin=serum had been calculated with a QSAR, we recalculated it with another QSAR that we also used for the other BP analogs (see next section). After optimizing the model for peroral exposure, we extended it to also include dermal exposure by using the dosing procedure and parameters developed by Mielke et al. (2011). Their model assumes that dermal exposure leads to a skinsurface depot, from which the substance first enters the skin compartment and then the blood compartment. 

### Parametrization for BPS, BPF, and BPAF 

The chemical-specific parameters indispensable for adapting the model to the BP analogs were the PTS and the metabolism 

126(7) July 2018 

Environmental Health Perspectives 

077002-2 



<!-- Start of picture text -->
Urinary excretion<br>Glucuronides in Sulfates in<br>Oral exposure serum serum<br>Glucuronidation Sulfation<br>Stomach Gut Liver<br>Gastric<br>emptying<br>Fat<br>Skin surface<br>Dermal exposure Skin<br>depot<br>Dermal uptake<br>Gonads<br>Brain<br>Rich<br>Slow<br>Serum<br>Urinary excretion<br><!-- End of picture text -->

Figure 2. Schematic overview of the PBPK model for BPA, BPS, BPF, and BPAF and their glucuronides and sulfates (PBPK-compartments in gray, single-compartment submodules with dotted lines). The perorally ingested bisphenols are presystemically metabolized in the gut and in the liver to the respective metabolites. The metabolites enter a subserum compartment without being distributed to the other tissues before excretion. Dermally absorbed bisphenols enter the skin compartment via the skin surface depot without presystemic metabolism. Note: BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; PBPK, physiologically based pharmacokinetic; Rich, richly perfused tissue; slow, slowly perfused tissue [perfusion higher/lower than 0:1 mL=min=g tissue, respectively (Edginton et al. 2006; ICRP 2002)]. 

parameters for the Michaelis-Menten and substrate inhibition enzyme kinetics, for glucuronidation and sulfation. To the best of our knowledge, no applicable experimental data on the PTS for BPS, BPF, and BPAF were available. Therefore, these parameters were estimated with QSARs. Among the QSARs described by DeJongh et al. (1997), Zhang and Zhang (2006), and Schmitt (2008), we selected the relationship that corresponded best to the respective experimental measurements for BPA from Doerge et al. (2011) (see Table S3). We placed largest emphasis on those PTS to which our model is most sensitive. For this, we calculated residual sum of squares and maximal concentrations (Cmax) for the concentration–time curve of unconjugated BPA after decreasing and increasing the PTS values (Table S4) and identified the PTS causing the greatest changes. 

### Measurement of Glucuronidation Kinetics of BPS, BPF, and BPAF 

We determined the glucuronidation kinetics of BPS, BPF, and BPAF experimentally in both human liver and intestinal microsomes. We did not conduct additional experiments on BPA glucuronidation kinetics, as several well-conducted studies already exist (Coughlin et al. 2012; Elsby et al. 2001; Kuester and Sipes 2007; Kurebayashi et al. 2010; Mazur et al. 2010; Street et al. 2017; Trdan Lušin et al. 2012). 

For each substrate, we prepared at least eight different substrate concentrations in methanol (Table 1) and further diluted them in the reaction mixture to a final volume of 100 lL, containing 50 mM phosphate buffer at pH 7.4, 10 mM magnesium chloride, the specific concentration of liver or intestinal microsomes (0:1 mg=mL for BPS, 0:05 mg=mL for BPF, and 0:01 mg=mL for BPAF), and alamethicin (5% of the total protein concentration). Pooled human liver microsomes (20 mg=mL) and pooled human intestinal microsomes (20 mg=mL) were from BD Biosciences. We first placed the reaction mixtures for 30 min on ice and then incubated them for 5 min at 37°C. The addition of uridine 5'-diphospho-glucuronic acid (Sigma-Aldrich) to a final concentration of 5 mM started the reaction. For the enzyme reactions, we used a temperature of 37°C; the incubation times differed, subject to the BP and microsome type regarded (Table 1). We terminated the glucuronidation reactions with the addition of 10 lL perchloric acid (Merck). In the following step, we put the samples on ice for 15 min, centrifuged at 16,000 × g for 10 min, and analyzed the supernatants using HPLC-UV. 

We conducted the HPLC-UV analysis on an Agilent 1,100 series HPLC system (Agilent Technologies). For this, we injected 10 lL of each sample onto a Poroshell 120 EC-C18 column (4:6 × 100 mm, 2:7 lm, Agilent Technologies) maintained at 40°C. The mobile phases were 0.1% formic acid (A) and acetonitrile (B). The elution of different BPs consisted of a linear gradient (see Table 2). We further analyzed the results with the GraphPad Prism software (version 5.04; GraphPad Software Inc.,) and selected the most suitable kinetic model (Michaelis-Menten or substrate inhibition, Equations 3 and 4), based on the curve fitting and the shape of the Eadie-Hofstee plots (see Figure S2). 

Michaelis-Menten equation: 



In the above equation, v represents the measured velocity of the enzyme-catalyzed reaction, vmax is the maximum reaction velocity, S is the substrate concentration, and Km is the MichaelisMenten constant, the substrate concentration at which the reaction velocity is half of the maximum. 

Substrate inhibition equation: 

Table 1. Experimental conditions for measuring bisphenol glucuronidation kinetics. 

|Parameter|BPS|BPF|BPAF|
|---|---|---|---|
|Substrate concentrations (lM)||||
|HLM|20; 50; 100; 200; 350; 500; 650; 800; 1,000|5; 10; 25; 40; 80; 120; 200; 300; 400; 500|0.2; 1; 2.5; 5; 10; 20; 30; 40; 50; 75|
|HIM|20; 50; 100; 250; 800; 1,100; 1,400|10; 25; 50; 75; 100; 150; 200; 300; 400|0.1; 0.4; 1; 3; 20; 35; 75; 100; 130|
|Enzyme concentration (mg=mL)|0.100|0.0500|0.0100|
|Incubation time (min)||||
|HLM|20.0|20.0|5.00|
|HIM|20.0|30.0|15.0|



Note: BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; HIM, human intestinal microsomes; HLM, human liver microsomes. 

126(7) July 2018 

Environmental Health Perspectives 

077002-3 

Table 2. HPLC-UV analytical conditions. 

|Substrate|Gradient (B = Acetonitril)<br>Detection wavelength<br>(nm)|Retention time<br>(min)|
|---|---|---|
|BPS|0–2 min, 10% B; 2–6 min, 10!55%B; 6–8 min, 55% B; 8–8.20 min, 55!10%B; 8.2–10 min, 10% B<br>260|BPS: 6.50<br>BPS-g: 4.20|
|BPF|0–2 min, 15% B; 2–6 min, 15!60%B; 6–8 min, 60% B; 8–8.20 min, 60!15%B; 8.2–10 min, 15% B<br>279|BPF: 6.90<br>BPF-g: 5.60|
|BPAF|0–3.5 min, 35% B; 3.5–6 min, 35!65%B; 6–8 min, 65% B; 8–8.20 min, 65!35%B; 8.2–10 min, 35% B<br>231|BPAF: 7.70<br>BPAF-g: 4.10|



Note: BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; g, glucuronide. 





### Calibration of the BPS Model with Biomonitoring Data and Adjustments for the Other Models 

Oh et al. (2018) conducted a study on the pharmacokinetics of BPS in adults, which we used to calibrate the BPS PBPK model and to draw conclusions on possible adjustments for the other models. They perorally exposed seven healthy adults to 8:75 lg=kg BW deuterated BPS administered in a chocolate cookie. Serum and urine samples were collected within a 48-h period, and related BPS concentrations were measured before and after enzymatic hydrolysis with b-glucuronidase. The b-glucuronidase used for the enzymatic hydrolysis also contained low sulfatase activity (1:04 units=mL, in comparison with 130 units=mL glucuronidase activity). The resulting concentrations were labeled “BPS total,” but it was acknowledged that the sulfatase activity probably had not been sufficient to release all BPS-s. Therefore, we considered the respective BPS concentrations measured being at least the sum of unconjugated BPS and BPS-g. We derived the minimal serum concentrations of BPS-g by subtracting the concentrations of unconjugated BPS from the concentrations of “total” BPS. We could not draw any conclusions on the extent of sulfation of BPS from this study. 

In our PBPK model, we used the volunteers’ individual physiological parameters and BW-specific single peroral exposures and compared the concentration–time profiles observed in the experiment 

with our model predictions. Subsequently, we adjusted the model to get a good correlation with the biomonitoring data by staying as close as possible to the kinetics observed experimentally. The calibrated model was used as the basic PBPK model for BPS, including the analog-specific glucuronidation kinetics. 

### Comparison of Model Predictions with Internal Exposure Assessments 

We assessed internal exposures for different age groups to compare the PBPK models for the different BPs. This approach served to compare the consequences of completely replacing BPA with different structural analogs. We compared the internal exposure assessments stepwise, so that different effects would not overlap. Table 3 gives an overview of the different scenarios. 

First, we compared predicted serum concentrations in adults after a single peroral and a single dermal dose of 500 ng=kg BW, respectively [rough average of peroral and dermal high exposure estimates for adults by the EFSA CEF (2015)]. This comparison is closest to available measurements, because BPA and BPS have been measured in the serum of adults in the pharmacokinetic studies used to calibrate their PBPK models (Table 3, scenario 1). In a second step, we used the same scenario to compare internal concentrations in the gonads of adults. These organs are especially relevant due to their vulnerability regarding endocrine disruption, but related concentrations are subject to higher uncertainty than serum concentrations (Table 3, scenario 2). Thirdly, we compared the models for the younger age groups infants (6 d–3 months), toddlers (1–3 y), children (3–10 y), and adolescents (10–18 y) using age- 

Table 3. Scenario-specific parameters used in the internal exposure assessments and the two-dimensional Monte Carlo analysis. 

|Sc|Dosing|tdosing (h)|Age group regarded|Compartment<br>regarded|Figure|
|---|---|---|---|---|---|
|1|Single peroral or dermal dosing of 500 ng=kg BW,<br>respectively<sup>a</sup>|0|Adults<sup>b</sup><br>|Serum|4-A|
|2|Single peroral or dermal dosing of 500 ng=kg BW,<br>respectively<sup>a</sup>|0|Adults<sup>b</sup>|Gonads|4-B|
|3|Single peroral or dermal dosing of 500 ng=kg BW,<br>respectively<sup>a</sup>|0|Infants, toddlers, children,<br>adolescents, adults<sup>b</sup>|Serum and gonads|S4–S7|
|4|Age group and route-specific parallel peroral and<br>dermal dosings.<sup>c </sup>Environmentally relevant expo-<br>sure estimates (Table 4) were divided into 3 and 2<br>daily doses for peroral and dermal exposure,<br>respectively.|Peroral: 0, 6, 12, 24, 30, 36, 48,<br>54, 60, 72, 78, 84; dermal: 0,<br>12, 24, 36, 48, 60, 72, 84|Infants, toddlers, children,<br>adolescents, adults<sup>b</sup>|Serum and gonads|5|
|5|Route-specific parallel peroral and dermal dosings.<sup>c</sup><br>Environmentally relevant exposure estimates<br>(Table 4) were divided into 3 and 2 daily doses for<br>peroral and dermal exposure respectively.|Peroral: 0, 6, 12, 24, 30, 36, 48,<br>54, 60, 72, 78, 84; dermal: 0,<br>12, 24, 36, 48, 60, 72, 84|Female adults<sup>b</sup>|Serum|6|



aRough average of peroral and dermal high exposure estimates for adults by the EFSA CEF (2015). bInfants, 6 days – 3 months; toddlers, 1–3 years; children, 3–10 years; adolescents, 10–18 years; adults, 18–45 years. cReferences supporting this value: EFSA CEF (2015), von Goetz et al. (2017). Note: Scenarios 1–4 refer to different internal exposure assessments; scenario 5 refers to the exposure assessment by which the two-dimensional Monte Carlo analysis was conducted. BW, body weight; Sc, scenario; t, time. 

126(7) July 2018 

Environmental Health Perspectives 

077002-4 

specific physiological parameters (Tables 4 and S1) to investigate age-dependent differences of internal exposures with equal external exposures per kg BW (Table 3, scenario 3). Last, we used environmentally relevant external exposure estimates for BPA (instead of the standard 500 ng=kg BW before) via both the dermal and peroral exposure route as model inputs for all BPs [route- and agespecific high-exposure estimates for BPA (EFSA CEF 2015; von Goetz et al. 2017), see Table 4]. We simulated peroral exposure by mimicking a diet with three meals per day within 12 h (Nicklas et al. 2001) and dermal exposure by touching thermal paper and using personal care products (PCPs) twice a day, in the morning and in the evening (Garcia-Hidalgo et al. 2017; Liao and Kannan 2011). The simulation was run for 4 d, until we reached a steady state (see Table 3, scenario 4). 

To account for the multiple dosings, we divided the estimated daily peroral and dermal exposure estimates into three and two daily doses, respectively. As absorption fractions we used 100% (EU 2008), 20% (Toner et al. 2016), and 60% (Biedermann et al. 2010) for peroral exposure and dermal exposure from thermal paper and PCPs, respectively. As PCPs can also contain ingredients enhancing skin penetration, the value of 60% for BPA dissolved in ethanol was chosen. As dermal absorption half-lives we used 6 h for thermal paper (Demierre et al. 2012) and 10 min for PCPs (Biedermann et al. 2010). As uptake periods, we used 15 min for peroral exposure (Tsukioka et al. 2004; Völkel et al. 2002) and 24 h for dermal exposure, representing exposures after which BPs are not washed off for a long time, so that they can penetrate the stratum corneum, where they are protected from removal (Demierre et al. 2012). All these uptake parameters were used in all exposure assessments, and they are summarized in Table 5. To interpret the results, we focused on comparing the Cmax and the area under the curve (AUC). 

### Uncertainty Analysis 

In an MC analysis, values are randomly sampled from probability distributions defined for variables of interest, which results in a user-defined number of realizations of the underlying model and its output (Thomopoulos 2013). MC simulations can be used to assess the combined effect of several sources of variability and/or uncertainty on the model output (Hoffman and Hammonds 1994). 

For our model, following a tiered approach (EFSA Scientific Committee 2016) parameter uncertainty was first assessed qualitatively (see Table S5). For parameters categorized with a medium to high (MH) or high (H) uncertainty, we subsequently quantified the impact of uncertainty in a 2D-MC analysis. The variability of all parameters was assessed in an inner loop of 1,000 iterations, and the uncertainty of the selected parameters was assessed in an outer loop of 1,000 iterations, resulting in 2D-MC assessments with 1,000 × 1,000 iterations for each BP. In the outer uncertainty loop, we used trapezoidal distributions on the basis of parameter values that had been found in different experiments, using the lowest and highest parametrizations reported as modes and using the outer 

Table 5. Route-specific uptake parameters used in all PBPK models and exposure assessments. 

|Parameter|Peroral|Dermal TP|Dermal PCPs|
|---|---|---|---|
|Absorption fraction (%)|100<sup>a</sup>|20<sup>b</sup><br>|60<sup>c</sup>|
|Absorption half-life (h)|0|6<sup>d</sup><br>|0.167<sup>c</sup><br>|
|Uptake period (h)|0.25<sup>e</sup>|24<sup>d</sup>|24<sup>d</sup>|



aReference supporting this value: EU (2008). bReference supporting this value: Toner et al. (2016). cReference supporting this value: Biedermann et al. (2010). dReference supporting this value: Demierre et al. (2012). eReferences supporting this value: Tsukioka et al. (2004), Völkel et al. (2002). Note: PBPK, physiologically based pharmacokinetic; PCPs, personal care products; TP, thermal paper. 

boundaries of the related truncated normal distributions (see explanations to variability distributions) as minimum and maximum. We used coefficients of variation (CV = standard deviation ðSDÞ= arithmetic mean) to describe the relative extent of variability and used a CV of 30%, if we could not derive a value from the underlying data. In the inner variability loop, we randomly varied the model parameters using truncated normal distributions to account for interindividual variability in a physiologically plausible way (95% of the distributions= ± 1:96 times SD). We used either the values drawn from the uncertainty distributions in the outer loop as mean values or, if not applicable, the parametrization from the basic models. We conducted the analysis for serum concentrations of women of childbearing age (18–45 y), because the models have been calibrated with measurements in adult serum for BPA and BPS, and exposure of women of childbearing age is the prerequisite for exposure of vulnerable fetuses (scenario 5 in Table 3). In the following paragraph, the derivation of parameters used in the 2D-MC analysis is described. The parameters used in the uncertainty and variability distributions are shown in Tables S6 and S7, respectively. 

Uncertainty: For the PTS, lowest and highest coefficients calculated with the different QSARs were used; see Tables 6 and S8 (DeJongh et al. 1997; Schmitt 2008; Zhang and Zhang 2006). For BPA, the uncertainty was only quantified for the skin PTS, which had been calculated with a QSAR. 

For BPA metabolism, distributions were used that span from the lowest to the highest values of vmax and Km for the glucuronidation in liver and intestine (see Table S2). Metabolism parameters are dependent on each other and reaction rates increase, when vmax is increased and/or Km decreased. Therefore, random combination of vmax and Km may result in reaction rates outside the range of observation. To avoid unrealistic reaction rates, we introduced a function calculating alternative boundaries for the sampling of vmax after a certain Km has been drawn. These alternative boundaries were recalculated for each inner loop iteration [see model code for the 2D-MC analysis in the Supplemental Material (SM)]. 

For BPF and BPAF, we could not calibrate the PBPK models. For their metabolism parameters, we used distributions spanning from the parameters found in our experiments to the resulting values when taking into account the deviation between measured and calibrated BPS parameters (assuming the same proportional 

Table 4. Physiological parameters (Edginton et al. 2006) and external exposures for bisphenol A (EFSA CEF 2015) used for the internal exposure assessments of bisphenols. 

|||||Ex|ternal Exposure (ng/|kg BW/day)|
|---|---|---|---|---|---|---|
|Age group|Age (y)|Bodyweight (kg)|Height (cm)|Oral|Dermal TP|Dermal PCPs|
|Infants (6 days–3 months)|new-born|3.5|51|615|0.00|9.40|
|Toddlers (1–3 years)|1|10|76|869|0.00|5.50|
|Children (3–10 years)|5|19|109|818|550|4.20|
|Adolescents (10–18 years)|15|53/56<sup>a</sup>|161/167<sup>a</sup>|384|863|4.80|
|Adult women (18–45 years)|30|60|163|389|542|4.00|
|Adult men (18–45 years)|30|73|176|336|542|4.00|



aParameter values were used for females and males, respectively. Note: PCPs, personal care products; TP, thermal paper. 

126(7) July 2018 

Environmental Health Perspectives 

077002-5 

Table 6. PTS for BPA (Doerge et al. 2011; Zhang and Zhang 2006) and BPS, BPF, and BPAF (Zhang and Zhang 2006). 

|Tissue|BPA|BPS<sup>a</sup>|BPF<sup>b</sup>|BPAF|
|---|---|---|---|---|
|Liver|0.730|0.846|0.872|2.44|
|Slowly perfused tissue<sup>c</sup>|2.70|0.881|0.853|2.11|
|<br>Brain|2.80|0.810|0.745|2.04|
|Richly perfused tissue<sup>d</sup>|2.80|0.810|0.745|2.04|
|<br>Fat|5.00|0.435|0.884|5.73|
|Skin|2.15|0.915|1.09|3.26|
|Gonads|2.60|0.843|0.778|1.86|



aCalculated as 14% deprotonated. bCalculated as 40% deprotonated. cPerfusion lower than 0:1 mL=min=g tissue: muscle and skeleton (Edginton et al. 2006; ICRP 2002). dPerfusion higher than 0:1 mL=min=g tissue: heart, kidneys, small and large intestine, pancreas, spleen, and stomach (Edginton et al. 2006; ICRP 2002). Note: Please note that the citation Zhang and Zhang (2006) refers to their second QSAR (equation 6). For BPA, no in vivo PTS was available for the skin compartment. Therefore this PTS was calculated according to Zhang and Zhang (2006). BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; PTS, tissue/serum partition coefficients; QSAR, quantitative structure-activity relationship. 

deviation from the values measured in vitro). We did not quantify uncertainty for the glucuronidation of BPAF in the small intestine, because four measurement points were within the concentration range of our model, so that the kinetics are likely to be less uncertain. 

For the peroral uptake of BPF and BPAF from the small intestine to the liver and their urinary excretion rates, the values from the calibrated BPA and BPS models were used as boundaries, to take into account possible deviations after model calibration. 

For the hepatic sulfation kinetics of BPS, BPF, and BPAF, the vmax of BPA sulfation was multiplied with a correction factor sampled from a distribution. The first boundaries of the correction factor distributions were the ratios between the hepatic glucuronidation rate of BPA and of the other analogs at environmentally relevant substrate concentrations. The second boundaries were the respective reciprocal values. This way, we wanted to mirror hepatic sulfation rates that are proportional or inversely proportional to the glucuronidation rates. For BPF and BPAF, we determined these ratios both with the original glucuronidation kinetics from our in vitro experiments and with the kinetics adjusted to the findings for BPS from in vivo data from Oh et al. (2018). We then used the outermost ratios as boundaries. 

For the fractions of BPA and BPS subject to EHR, we used ranges of 20% around the EHR values that led to the best fit to the biomonitoring data, i.e., modes of 0–20% for BPA and 57– 77% for BPS. For BPF and BPAF, we used wider ranges and varied the EHR rates of unconjugated substances and glucuronides in the uncertainty loops (for BPA and BPS, we varied them only in the variability loops). 

Different studies investigated the microsomal protein content in the liver (Barter et al. 2007; Pelkonen et al. 1973; Schoene et al. 1972) and the small intestine (Paine et al. 1997; Zhang et al. 1999), and we set up distributions accordingly. 

Different values have been reported for the extent of dermal absorption and its half-life (Biedermann et al. 2010; Demierre et al. 2012; Toner et al. 2016; Zalko et al. 2011). For thermal paper, we considered only studies in which BPA was dissolved in water or in sweat simulants, whereas for PCPs, we considered all studies available regardless of the solvent used. 

Variability: We used normal distributions if not indicated otherwise. The age was sampled from a uniform distribution across the defined age group range (18–45). We used height distributions for adults with the respective SDs (CV of 6%) to represent the Central European population (Motmans 2005). For the body mass index (BMI), we used a log-normal distribution based on a CV of 20%, because a right-skewed BMI- 

distribution had been found for the Belgian adult population (Lebacq 2015). 

Furthermore, we used a CV of 23% for the cardiac output (Squara et al. 2007), 32% for the PTS (Doerge et al. 2011), and 27% for the organ blood flows (Brown et al. 1997). We used a CV of 25% for the tissue volumes (Henderson et al. 1981), which we also used for the volume of distribution in the small intestine (educated guess). To maintain mass balance and to ensure that the sampled physiological parameters are physiologically plausible, we readjusted the sum of the randomly sampled organ blood flows and tissue volumes in a fractional manner. For this, we calculated the deviations of the total sampled blood flows and tissue volumes from the required sums, respectively. We then corrected for the deviated amount in proportion to the respective mean fractional blood flows and tissue volumes. 

Kuester and Sipes (2007) investigated interindividual differences in hepatic glucuronidation, and we derived CVs of 29% for the Km and 36% for the vmax from their findings. We also used these values for Km and vmax of the other metabolism pathways, as there were no ranges available for hepatic sulfation, and only pooled microsomes had been used in the studies investigating gut glucuronidation. For the Ksi, we derived a CV of 33% from the results of our experiments on gut and hepatic glucuronidation. However, this CV does not fully reflect interindividual variability, but rather a mixture of variability and measurement uncertainty, because we used pooled microsomes. 

We used CVs of 40% and 6% for the microsomal protein content in the small intestine (Paine et al. 1997; Zhang et al. 1999) and the liver (Barter et al. 2007; Pelkonen et al. 1973; Schoene et al. 1972), respectively. For the gastric emptying time, we derived a CV of 27% from a study measuring gastric emptying rates with varying peroral doses (Oberle et al. 1990). The CV for the peroral uptake from the small intestine to the liver was set to 39% (Yu et al. 1996). 

We used CVs of 31% for the dermal absorption fractions (Toner et al. 2016) and 30% for the dermal absorption half-lives (educated guess). We did not vary the peroral absorption fraction of 100%, which is recommended for use in regulatory risk assessments [EU (European Union) 2008], as this would only lower the model estimates, and we did not want to trigger underestimation in the variability assessment. CVs of 30% were used for the uptake of BPA-g and BPA-s from the enterocytes into the liver, the urinary excretion of BPA, BPA-g, and BPA-s, and the EHR conversion rates from unconjugated and glucuronized substances (educated guess). 

### Model Evaluation – Comparison with Biomonitoring Data 

To evaluate the model, we sought to compare it with biomonitoring data from literature that were independent of the data the basic models were calibrated with. Studies could be used only if they reported concentrations and time-points of exposure, as well as time-dependent and conclusive internal concentration profiles. Such data to date are available only for BPA: Teeguarden et al. (2015) recruited ten healthy male adults and provided them with tomato soup that contained 30 lg deuterated BPA/kg BW. Within the 24-h study period, venous blood samples were drawn, and all voided urine was collected. In our PBPK model, we used the volunteers’ individual physiological parameters and BWspecific single peroral exposures. 

Hormann et al. (2014) let volunteers wet their hands with hand sanitizer before they held thermal receipt paper containing BPA. Subsequently, the subjects ate 10 French fries with the contaminated hands, resulting in both dermal and peroral exposure to BPA. We compared the individual systemic serum profiles of BPA, BPA-g, and BPA-s measured in three volunteers with our 

126(7) July 2018 

Environmental Health Perspectives 

077002-6 

model predictions. For this, we estimated the external peroral and dermal exposure, the extent of dermal absorption, and the dermal absorption half-life according to the study design as described in the following paragraph: 

In one experiment, Hormann et al. (2014) measured the BPA amount transferred to a hand wetted with sanitizer due to holding thermal paper for different lengths of time. After each trial, they thoroughly swiped the hand and measured all BPA transferred to the wipes. In our calculations, we assumed that the highest BPA amount measured can be transferred to the hands and is available for dermal absorption (mdermal1). In the main experiment, three volunteers handled receipts for 4 min with both hands, which were wetted with sanitizer (one receipt per hand). Afterwards, both hands touched 10 French fries each during a total contact time of 4 min. The French fries from one hand were analyzed for their BPA content (moral). The volunteers ate the French fries from the other hand. Afterwards, one hand of each volunteer was thoroughly swiped, and the transferred BPA was analyzed (mdermal2). The other hand stayed contaminated for the rest of the experiment (90 min in total). We based our exposure simulations on one peroral and two dermal doses. The first dermal dose was 2 � mdermal1 from 0–8 min (two hands). The worst-case extent of absorption for the first dermal dose was ðmdermal1 − moral − mdermal2Þ=mdermal1. This share could have been taken up within 8 min, and we calculated the absorption half-life accordingly. 

The second dermal dose was mdermal2 from 8–90 min for one hand. The extent of absorption and the absorption half-life were set to the values of the first dermal dose. The peroral dose was moral from 4–8 min. For the dose calculations, we used the individual measurements Hormann et al. (2014) found for the volunteers and kindly provided to us. We scaled all exposure values according to the BW. Table S9 shows all input parameters applied. 

For BPS, the only available biomonitoring study (as of April 2018) was used for calibration. For BPF and BPAF, no biomonitoring data were available. Therefore, the internal exposures of the BPA substitutes BPS, BPF, and BPAF could not yet be evaluated against independent data. 

### Computing Software 

We performed coding and simulations using the programming language R, version 3.3.2 (see Supplemental Material for the model code and related input Tables C1–C4). 

## Results 

### BPA Model Calibration 

We successfully recalibrated the model of Yang et al. (2015) and added a dermal uptake route (compare Figure S1A with S1B and S1C). Incorporating the EHR pathway into the model as assumed by Yang et al. (2015) improved the BPA-specific model to a small extent (compare Figure S1B and C); however, it did result in a considerably better agreement between measured and modeled concentration–time profiles of BPS-g (compare Figure S3B and S3C). We therefore used EHR in all PBPK models and an EHR share of 10% in the BPA PBPK model, as suggested by Yang et al. (2015), to ensure structural model consistency. We used the following parametrization for the basic model of BPA: Coughlin et al. (2012) for hepatic glucuronidation, Trdan Lušin et al. (2012) for intestinal glucuronidation, and Zhang et al. (1999) for the microsomal protein content in the small intestine (see Table 7). 

Tables 7, 8, and S1 show the model parameters used for BPA, which were partly chemical or age group-specific. Table 6 shows the related PTS. 

### BPS, BPF, and BPAF Model Parametrization and Calibration 

Regarding the QSAR selection to calculate the PTS for BPS, BPF, and BPAF, Table S3 compares the PTS for BPA determined experimentally (Doerge et al. 2011) and with different QSARs (DeJongh et al. 1997; Schmitt 2008; Zhang and Zhang 2006). Varying the PTS between richly perfused tissue and serum led to the highest changes of the residual sum of squares and Cmax (Table S4). We selected the QSAR (2) by Zhang and Zhang (2006) to calculate the PTS in the basic model, because the use of this QSAR resulted in modeled results close to the experimental values for Prichly perfused tissue=serum, and none of the calculated PTS deviated more than a factor of 2 from the experimental values. The QSAR by Zhang and Zhang (2006) takes into account that substances can be partially deprotonated depending on the pKa value. Although this is rather not an issue for BPA (pKa ffi 10:4) (Bautista-Toledo et al. 2005) and BPAF (pKa ffi 9:2) (SPARC 2011), it is important for BPF and BPS, which are more acidic (pKa ffi 7:6 and 8.2, respectively) (SPARC 2011). The deprotonation lowers the PTS for all tissues in relation to the serum compartment. Table 6 shows the PTS for BPS, BPF, and BPAF. 

Figure 3 compares the glucuronidation kinetics of BPS, BPF, and BPAF investigated in this study with the kinetics of BPA obtained from Coughlin et al. (2012) at both the high substrate conditions evaluated experimentally (Figure 3A) and at lower substrate concentrations, which are more physiologically relevant and could be investigated with the PBPK models (Figure 3B). At high substrate concentrations, the glucuronidation of BPAF was slower than the glucuronidation of BPA, BPS, and BPF, but at lower substrate concentrations, the glucuronidation of BPAF was the most effective, and that of BPS was the least effective of all analogs. 

Unfortunately, no studies were available on the sulfation of BPS, BPF, and BPAF in the liver or the intestine. Therefore, we used the hepatic sulfation of BPA as an approximation for the other analogs in the basic models when comparing internal exposures. To analyze the associated uncertainty, we varied the sulfation in the 2D-MC assessment and studied different sulfation patterns (see section below, “Uncertainty Analysis”). 

When comparing the uncalibrated BPS model with the biomonitoring data (Oh et al. 2018), the concentrations modeled for unconjugated BPS in serum were lower than the corresponding concentrations measured and serum concentrations peaked later in the model than in the measurements (see top row in Figure S3A). We adjusted this with an increase of the peroral uptake rate from the small intestine to the liver. Table S10 shows PBPK model parameters for BPS before and after the calibration (visual fit). For BPS-g, concentrations measured were much lower than concentrations modeled (see bottom row in Figure S3A). Lowering the glucuronidation and increasing the clearance rates in the model led to a better fit, but the modeled concentrations decreased much faster than measured (see Figure S3B). A possible explanation for this delay might be that BPS undergoes EHR, and, indeed, the introduction of EHR into the PBPK model (with a share of 67%) improved the correlation between measured and modeled concentration-time profiles substantially, as depicted in Figure S3C. Unfortunately, no data were available to validate the PBPK models of BPF and BPAF. Due to similarities in molecular weight and chemical structure, we used the BPA model calibration for BPF, and the BPS model calibration for BPAF in the basic models, for parameters related to uptake from small 

126(7) July 2018 

Environmental Health Perspectives 

077002-7 

Table 7. Chemical specific metabolic model parameters for BPA, BPS, BPF, and BPAF. 

|Metabolic parameters|BPA|BPS|BPF|BPAF|All BPs|
|---|---|---|---|---|---|
|Hepatic glucuronidation||||||
|Km (nM) - used in basic model|45,800<sup>a</sup>|446,000<sup>b</sup>|17,900|4,210||
|Km range (nM)<br>|5,300–77,500<sup>c</sup>|||||
|Ksi (nM)<sup>d</sup>||||219,000||
|vmax (nmol=h=g liver)<sup>e </sup>- used in basic model|9,040<sup>a</sup>|7,810<sup>b</sup>|3,600|5,660||
|vmax range (nmol=h=g liver)<br>|1,270–16,300<sup>c</sup>|||||
|Microsomal protein content in the liver (mg protein=g liver)–used in basic model<sup>f</sup>|||||32.0<sup>g</sup><br>|
|Microsomal protein content in the liver range (mg protein=g liver)|||||32.0–38.0<sup>h</sup>|
|Glucuronidation in enterocytes||||||
|Km (nM)–used in basic model|58,400<sup>i</sup><br>|555,000<sup>b</sup>|57,000|1,830||
|Km range (nM)<br>|58,400–80,100<sup>j</sup>|||||
|Ksi (nM)<sup>d</sup>||711,000|605,000|82,200||
|vmax (nmol=h=g bw)<sup>e </sup>- used in basic model|361<sup>i</sup><br>|563|462|107||
|vmax range (nmol=h=g liver)<br>|125–361<sup>j</sup>|||||
|Microsomal protein content in the small intestine (mg protein=kg BW)–used in basic model<sup>f</sup>|||||4.29<sup>k</sup><br>|
|- Microsomal protein content in the small intestine range (mg protein=kg BW)|||||4.29–39.7<sup>l</sup>|
|Hepatic sulfation||||||
|Km (nM)<sup>m</sup>|10,100<sup>n</sup>|NA<sup>o</sup>|NA<sup>o</sup>|NA<sup>o</sup>||
|vmax (nmol=h=g liver)<sup>e, m</sup>|149<sup>n</sup>|NA<sup>o</sup>|NA<sup>o</sup>|NA<sup>o</sup>||



aReference supporting this value: Coughlin et al. (2012). bVisually fitted for BPS: The parameter was adjusted within the bounds of the truncated normal distribution used to describe variability (see Methods, Uncertainty Analysis), to decrease the distance between measured and modeled concentrations. As a result, the upper and lower bounds were used for Km and vmax parameters respectively. cReferences supporting this value: Coughlin et al. (2012); Kurebayashi et al. (2010); Trdan Lušin et al. (2012); Elsby et al. (2001); Kuester and Sipes (2007); Mazur et al. (2010); Street et al. (2017). 

> dKsi parameters are only needed for substrate-inhibition kinetics. If the parameter is not supplied, Michaelis-Menten kinetics were used to describe the glucuronidation. 

> eThis parameter was scaled to nmol=h=kg bw0:75 within the model using the individual body weights of the test persons. 

> fThis parameter was not chemical-specific but was used to calculate vmax from experiments. gReference supporting this value: Barter et al. (2007). hReferences supporting this value: Barter et al. (2007), Pelkonen et al. (1973), Schoene et al. (1972). iReference supporting this value: Trdan Lušin et al. (2012). jReferences supporting this value: Trdan Lušin et al. (2012), Mazur et al. (2010). kReference supporting this value: Zhang et al. (1999). lReferences supporting this value: Zhang et al. (1999), Paine et al. (1997). mExperimental values for hepatic sulfation of BPS, BPF, and BPAF were not available. nReference supporting this value: Kurebayashi et al. (2010). oTo the best of our knowledge, there are no current studies reporting sulfation rates of BPS, BPF, and BPAF, and they were approximated using the values for BPA (Kurebayashi et al. 2010). 

Note: BW, body weight; BP, bisphenol; BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; Km, Michaelis-Menten constant; Ksi, constant of substrate inhibition; NA, data not available; vmax, maximum enzyme velocity. 

intestine to liver, and urinary excretion. EHR was reported to depend on molecular weight (Roberts et al. 2002). As BPF has a lower molecular weight than BPA, and BPAF a higher molecular weight than BPS, we used EHR rates of 0% and 70% for BPF and BPAF, respectively (educated guess). 

Comparison of Model Predictions with Internal Exposure Assessments. Figure 4A shows serum concentrations of unconjugated BPA, BPS, BPF, and BPAF in female and male adults after single peroral and dermal exposures of 500 ng=kg BW respectively, obtained with the basic PBPK models. We observed considerable 

Table 8. Further physiological model parameters as used in the basic PBPK models for BPA, BPS, BPF, and BPAF. 

|Further physiological parameters|BPA|BPS|BPF|BPAF|All BPs|
|---|---|---|---|---|---|
|Gastric emptying (1=h=kg BW<sup>−0:25</sup>)|||||3.50<sup>a</sup><br>|
|Volume of distribution in small intestine (mL)<br>|||||122<sup>b</sup>|
|Oral uptake from small intestine to liver (1=h=kg BW<sup>−0:25</sup>)<br>|2.10<sup>a</sup><br>|5.00<sup>c</sup>|2.10<sup>d</sup><br>|5.00<sup>e</sup>||
|Urinary excretion (1=h=kg BW<sup>0:75</sup>)|0.060<sup>f</sup><br>|0.30<sup>c</sup>|0.060<sup>d</sup>|0.30<sup>e</sup><br>||
|Fraction of glucuronide in liver taken up directly into serum (no EHR)<br>|0.9<sup>f</sup><br>|0.33<sup>c</sup>|1.0<sup>g</sup><br>|0.3<sup>h</sup>||
|EHR unconjugated (1=h=kg BW<sup>−0:25</sup>)<br>|0.20<sup>f</sup><br>|0.35<sup>c</sup>|0.20<sup>d</sup><br>|0.35<sup>e</sup>||
|EHR as glucuronide (1=h=kg BW<sup>−0:25</sup>)|0.20<sup>f</sup>|2.0<sup>c</sup>|0.20<sup>d</sup>|2.0<sup>e</sup>||
|Glucuronides & Sulfates<br>||||||
|Uptake from enterocytes into the liver (1=h=kg BW<sup>−0:25</sup>)|||||50.0<sup>f,i</sup><br>|
|Volume of distribution (fraction of body weight)<br>|||||0.0435<sup>j</sup>|
|Urinary excretion glucuronide (1=h=kg BW<sup>0:75</sup>)<br>|0.35<sup>f</sup>|1.2<sup>c</sup>|0.35<sup>d</sup>|1.2<sup>e</sup>||
|Urinary excretion sulfate (1=h=kg BW<sup>0:75</sup>)|||||0.030<sup>f,i</sup>|



aReference supporting this value: Kortejärvi et al. (2007). bReference supporting this value: Gertz et al (2011). 

cVisually fitted for BPS: The parameter was adjusted to decrease the distance between measured and modeled concentrations. dNo data was available to calibrate the BPF model, and we used the BPA model calibration due to similarities in molecular weight and chemical structure. eNo data was available to calibrate the BPAF model, and we used the BPS model calibration due to similarities in molecular weight and chemical structure. fReference supporting this value: Yang et al. (2015). Their parametrization still led to good correspondence between measurements and model. gWe used an EHR rate of 0% for BPF as result of an educated guess due to BPF having a lower molecular weight than BPA. hWe used an EHR rate of 70% for BPAF as result of an educated guess due to BPAF having a higher molecular weight than BPS. iThe BPA parametrization was used for all analogs. jSet equal to the plasma volume of 0:0435 L=kg for adult humans because the metabolites were assumed to be distributed with the systemic circulation. Reference supporting this value: ICRP (2002). 

Note: BW, body weight; BP, bisphenol; BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; EHR, enterohepatic recirculation. 

126(7) July 2018 

Environmental Health Perspectives 

077002-8 



<!-- Start of picture text -->
A<br>Small intestine Liver<br>●<br>● ● ●<br>●<br>●<br>● ● ●<br>●<br>●<br>●<br>●<br>●<br>● ●<br>0 200 600 1000 1400 0 200 400 600 800 1000<br>B<br>0 1 2 3 0 0.004 0.008 0.012<br>cx (μmol/L) cx (μmol/L)<br>x = { __ BPA       BPS   - - - ● __   BPF       BPAF   - - - }<br>25<br>20 30000<br>15<br>10<br> (μmol/h)vx<br>5 1000020000<br>0 0<br>5 30<br>4<br>20<br>3<br>(μmol/h)vx  2<br>10<br>1<br>0 0<br><!-- End of picture text -->

Figure 3. Glucuronidation kinetics of BPA (Coughlin et al. 2012) and BPS, BPF, and BPAF (this study) in the small intestine and in the liver of an average adult (body weight = 70 kg) as used in the basic model. The first row (A) shows the kinetics at concentration ranges evaluated experimentally in the current study (BPS, BPF, and BPAF) and by Coughlin et al. (2012) (BPA), the second row (B) focuses on the kinetics at environmentally relevant concentrations (EFSA CEF 2015). Solid circles show measured mean values and whiskers show the measurement ranges for BPS, BPF, and BPAF (n = 3). Please note that in the line graph on the bottom right the curves of BPA and BPF overlap. Note: BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; cx, concentration of bisphenol x; vx, reaction velocity of bisphenol x. 

internal exposure differences between the four BPs and the two uptake routes, with BPS leading to the highest Cmax for both exposure routes. BPAF showed the lowest Cmax for both routes with comparatively higher concentrations after dermal exposure, e.g., the Cmax in serum of female adults were 1:79 pM and 7:66 pM after peroral and dermal external exposure, respectively. Estimated gonadal concentrations after the same exposures are shown in Figure 4B. We observed that the highest internal maximal concentrations were reached with BPS after peroral exposure and with BPA after dermal exposure. Figures S4–S7 illustrate age-dependent differences of internal exposures. After equal peroral exposure per kg BW, the Cmax was the highest for infants, followed by toddlers, children, adolescents, and adults. After dermal exposure, the order was almost reversed, with adults obtaining the highest Cmax. 

To illustrate possible consequences of future BPA replacements, we modeled internal exposures by assuming 100% replacement of BPA by each analog, respectively (see Table 4 for external exposures). Figure 5 shows the effects of the different peroral and dermal exposures on the concentration–time profiles for the unconjugated BPs. As shown in Table 4, infants, toddlers, and children were primarily exposed via the peroral route, with children being considerably exposed also via the dermal route. For infants and toddlers, the first peaks in serum and gonads were nearly as high as the corresponding highest peaks; e.g., for BPF in serum of female infants, the first Cmax of 60 pM (t = 46 min) was 99% of the highest Cmax at 37 h. BP concentrations in serum and gonads of children, adolescents, and adults increased over a longer time period, and for all BPs but BPS, the first peaks were 

considerably lower than the corresponding highest peaks (e.g., for BPF in serum of female adolescents, the first Cmax of 11 pM (t = 46 min) was only 28% of the highest Cmax at 85 h). The concentration curves for dermally applied BPs plateaued within the modeled time period (see Figure 5). 

For BPAF, even in children, dermal exposure contributed most to internal concentrations of unconjugated BPAF, although the external dermal exposure was lower than the external peroral exposure (Table 4). This can be seen in the steady-state phase of the BPAF profiles (Figure 5): In serum, for example, the peaks resulting from peroral exposure (e.g., 8:7 pM at t = 73 h) contributed only 33% to the total concentration, because of the substantial background concentration from dermal exposure (5:8 pM at t = 72 h). 

Table 9 shows the maximum Cmax and AUC obtained with exposure scenario 4 and the associated exposed age group and sex. In serum and gonads, the highest Cmax was estimated to occur in female toddlers (BPA, BPS, and BPF) and male adolescents (BPAF). By contrast, the highest AUC was estimated to occur in male adolescents (BPA, BPF, and BPAF) and male children (BPS). When comparing the different BP analogs, BPS exposure resulted in the highest concentrations in serum and gonads. 

### Uncertainty Analysis 

In the qualitative evaluation of parameter uncertainty, we found that parameters related to metabolism kinetics, enzyme concentrations, 

126(7) July 2018 

Environmental Health Perspectives 

077002-9 



<!-- Start of picture text -->
A Serum B Gonads<br>BPA<br>oral dermal oral dermal<br>BPS<br>BPF<br>BPAF<br>0 24 48 0 24 48 0 24 48 0 24 48<br>time (h) time (h) time (h) time (h)<br>Females solid lines  |  Males dotted lines<br>0<br>−2<br>x<br>−4<br>  c-BP (10    nM)<br>−6<br><!-- End of picture text -->

Figure 4. Modeled concentration profiles of unconjugated BPA, BPS, BPF, and BPAF obtained with the basic PBPK models in serum (A) and gonads (B) for adults (18–45 y) after 500 ng=kg bodyweight single peroral and dermal exposures (t = 0 h), respectively [rough average of peroral and dermal high BPA exposure estimates for adults by the EFSA CEF (2015)]; see Table 5 for uptake parameters. Females are represented by solid lines; males are represented by dotted lines. Note: BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; c-BP, bisphenol concentration; PBPK, physiologically based pharmacokinetic. 

partitioning, EHR, and dermal exposure were subject to relatively high uncertainty (see Table S5). Figure 6 shows the cumulative density functions (CDFs) for AUC and Cmax of unconjugated BPs in serum of women of childbearing age in the 2D-MC analysis, and Table 10 shows the associated summary statistics. In general, 90% of the predicted variability fell within less than one order of magnitude. 

A comparison of the CDFs of the basic models with the ones of the different percentiles from the uncertainty iterations revealed that the basic model predicted comparatively high concentrations of unconjugated BPs in serum. BPAF generally showed the lowest and BPS the highest values for AUC and Cmax (see Table 10). Internal concentrations were rather similar for BPA and BPF. There was only little overlap of the BPAF-CDFs with CDFs of other analogs, whereas there was some overlap of the BPA- and BPF-CDFs with the BPS-CDFs. 

### Model Evaluation—Comparison to Biomonitoring Data 

The adapted and recalibrated PBPK model for BPA was compared to two BPA biomonitoring studies, see Table S9 for input parameters applied (Hormann et al. 2014; Teeguarden et al. 2015). Table 11 compares measured and predicted pharmacokinetic parameters for unconjugated BPA, BPA-g, and BPA-s. Regarding the study by Teeguarden et al. (2015), the predicted average values for Cmax were 1.3 to 3 times and for AUC 1.4 to 1.6 times higher than the measured values. The average timing of maximum concentration obtained with our model was similar (BPA-s, BPA-g) or lower (BPA) than measured. When comparing the ranges of measured and predicted values, all predicted ranges for the AUCs were within the ranges of measurements. Regarding the study by Hormann et al. (2014), Figure S8 additionally illustrates the differences between measured and modeled individual serum profiles of BPA, BPA-g, and BPA-s in three volunteers. Measured serum concentrations of unconjugated BPA were different for the two women and the man, with considerably higher measured values for the women (Cmax of 5.86, 5.03, and 0:42 ng=mL for the two women and the man respectively, shown in Figure S8). The course of the concentration–time curves of BPA-g and BPA-s did not vary considerably among the three subjects. Using the parameters derived from the study protocol, our model corresponded well with the concentrations of unconjugated BPA measured in the two women, but it overestimated the 

unconjugated BPA concentrations for the man and the BPA-g and BPA-s time curves of all subjects. 

## Discussion 

### Model Calibration and Parametrization 

When readjusting the BPA PBPK model with different parameter sets, we achieved good agreements when we assumed that no EHR was occurring, but also for 10% of BPA undergoing EHR (see Figure S1B and S1C). Multiple studies have measured parameters related to hepatic and intestinal glucuronidation, and there was a large range of reported values for Km and vmax, respectively (see Table S2). This variability could have been caused by individual-based differences in glucuronidation activities, which also influence the performance of pooled microsomes (Kuester and Sipes 2007; Street et al. 2017), or by differences in experimental techniques and equipment. 

The calibration of the BPS PBPK model with the biomonitoring data by Oh et al. (2018) revealed that BPS is likely to undergo EHR, which is also supported by their observation of a half-life 2.7 times longer than the half-life of BPA. For other glucuronized compounds, such as the medications lorazepam and retigabine, biliary excretion and EHR have been reported (Herman et al. 1989; Hiller et al. 1999). The likelihood of chemicals to undergo EHR was found to correlate with the molecular weight of the metabolite, and a threshold of 500 to 600 g=mol is estimated for humans (Roberts et al. 2002). The molecular weight of BPS-g is higher than that of BPA-g (426 vs. 404 g=mol), which supports the assumption that the occurrence of EHR depends on molecular weight. On this basis, EHR might be even more likely for BPAF-g ( 512 g=mol) and the least likely for BPF-g ( 376 g=mol). However, molecular weight may not be the only relevant parameter for EHR, because it has been observed that, e.g., estradiol and estron undergo EHR to a different extent, although the two molecules’ molecular weights differ by only 2 g=mol (Roberts et al. 2002). With an EHR pathway, unconjugated and glucuronized BPs stay longer in the human body, partly in conjugation-deconjugation cycles, with associated enhanced effects on endocrine receptors. Therefore, the occurrence and extent of EHR in the pharmacokinetics of BPs need further investigation. 

Regarding the parametrization of BPS, BPF, and BPAF, we expanded the knowledge on their glucuronidation in the liver and 

126(7) July 2018 

Environmental Health Perspectives 

077002-10 



<!-- Start of picture text -->
Serum Gonads<br>0 12 24 36 48 60 72 84 96 0 12 24 36 48 60 72 84 96<br>0 12 24 36 48 60 72 84 96 0 12 24 36 48 60 72 84 96<br>0 12 24 36 48 60 72 84 96 0 12 24 36 48 60 72 84 96<br>0 12 24 36 48 60 72 84 96 0 12 24 36 48 60 72 84 96<br>time (h)                        time (h)<br>- - Infants      Toddlers      Children      fem. Ado.    __ . . . __ - -  male Ado.      fem. Adults    __ - -  male Adults<br>15<br>-2 4<br>. 10<br>2<br>5<br>c-BPA (nM  10   )<br>0 0<br>50 40<br>-2 40<br>30<br>. 30<br>20<br>20<br>c-BPS (nM  10   )<br>10<br>10<br>0 0<br>6<br>6<br>-2<br>. 4<br>4<br>c-BPF (nM  10   ) 2<br>2<br>0 0<br>1.5 3<br>-2<br>. 1 2<br>c-BPAF (nM  10   ) 0.5 1<br>0 0<br><!-- End of picture text -->

Figure 5. Modeled concentration profiles of unconjugated BPA, BPS, BPF, and BPAF obtained with the basic PBPK models in serum and gonads for infants (6 d–3 months), toddlers (1–3 y), children (3–10 y), adolescents (10–18 y), and adults (18–45 y) during four-day-long concurrent peroral and dermal exposures to route and age group-specific high BPA exposure estimates [EFSA CEF (2015)], see Table 4), which were divided into three and two daily doses (tdosing peroral = 0 h, 6 h, 12 h, 24h, 30h, 36 h, 48 h, 54 h, 60 h, 72 h, 78 h, 84 h; tdosing dermal = 0 h, 12 h, 24 h, 36 h, 48 h, 60 h, 72 h, 84 h); see Table 5 for uptake parameters. Females are represented by solid lines; males are represented by dotted lines. Note: BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; c, concentration; PBPK, physiologically based pharmacokinetic. 

the small intestine. Additionally, our results suggest that the reaction rates depend on the concentration range considered and that, in humans, far lower concentration ranges exist than those that are normally investigated in in vitro studies (Figure 3). As Michaelis-Menten and substrate inhibition kinetics are approximations based on measured data, and in most cases, there were more measurement points at higher concentrations, one should note that the extrapolations toward the lower concentration ranges might not be as good as extrapolations toward higher 

concentrations. This discrepancy was seen during the calibration of the BPS PBPK model with the biomonitoring data by Oh et al. (2018), where we had to adjust the parameters related to the glucuronidation kinetics within the ranges of the respective variability distributions. However, the different extent of metabolism of BPA and BPS was well represented. For future kinetic studies, we therefore encourage metabolic tests that focus on the concentration range expected after environmentally relevant exposure to lower the uncertainty related to extrapolation. 

126(7) July 2018 

Environmental Health Perspectives 

077002-11 

Table 9. Highest values for Cmax and daily AUC of unconjugated BPA, BPS, BPF, and BPAF in serum and gonads and associated exposed age groups and sex obtained with the basic PBPK models after peroral and dermal exposures as estimated by the EFSA CEF (2015) for BPA in the high exposure scenario. 

|Cmax or AUC|BPA|BPS|BPF|BPAF|
|---|---|---|---|---|
|max. Cmax serum (pM)|52.4<sup>a</sup>|451<sup>a</sup>|67.7<sup>a</sup>|14.9<sup>b</sup><br>|
|max. Cmax gonads (pM)|135<sup>a</sup><br>|380<sup>a</sup>|52.6<sup>a</sup><br>|27.7<sup>b</sup><br>|
|max. AUC serum (nM*h per day)|0.759<sup>b</sup><br>|3.32<sup>c</sup>|0.818<sup>b</sup><br>|0.350<sup>b</sup><br>|
|max. AUC gonads (nM*h per day)|1.97<sup>b</sup>|2.80<sup>c</sup>|0.636<sup>b</sup>|0.651<sup>b</sup>|



aCorresponds to female toddlers (ages 1–3 years). bCorresponds to male adolescents (ages 10–18 years). cCorresponds to male child (ages 3–10 years). Note: AUC, area under the curve; BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; Cmax, maximum concentration. 

The development of PBPK models for the BP analogs described here focused on embedding new glucuronidation parameters for BPS, BPF, and BPAF. Multiple pharmacokinetic studies on BPA conducted in vivo identified BPA-g as the main metabolite, and the fraction of BPA-s formed was small: In one study, BPA-s represented only 3% of the total excreted BPA (Thayer et al. 2015) and in another study 0.5–4.8% of metabolites present in plasma after peroral exposure of neonatal mice (Draganov et al. 2015). Also, the contributions from other verified BPA metabolites, such as hydroxylated BPA, BPA-bis-sulfate, and the mixed sulfate/glucuronide bisconjugatearerelativelyminor, andtheirformationkinetics arepartly unclear (Gramec Skledar and Peterlin Maši�c 2016; Thayer et al. 2015). Furthermore, for other compounds such as some pharmaceuticals, the largest share of phase 2 metabolism in human cells was shown to be through glucuronidation (Hewitt et al. 2001). Nevertheless, a limitation of the models is that we did not have experimental values for metabolism pathways other than glucuronidation for BPS, BPF, and BPAF, e.g., hepatic sulfation. We used the sulfation kinetics of BPA as a surrogate in the basic models for the analogs, which allowed us to focus on internal concentration differences caused by the different extents of glucuronidation that had been measured for the different BPs. In the 2D-MC analysis, we used ranges of possible sulfation kinetics taking into account that hepatic sulfation rates could be proportional or inversely proportional to hepatic glucuronidation rates. These assumptions seemed to be most reasonable with regard to the data available. Also, just like Yang et al., we were confronted with the lack of data on intestinal sulfation for BPs. In the absence of any reference point, we could not incorporate intestinal sulfation into our models. However, Figure 3 

suggests that glucuronidation rates in the liver are considerably higher than in the small intestine. At the same time, in the basic BPA model, the vmax of hepatic sulfation was about 60 times lower than that of hepatic glucuronidation. These findings suggest that intestinal sulfation is probably no key pathway for BP metabolism. Regarding varying extents of hepatic sulfation, the results of the 2D-MC analysis (Figure 6 and Table 10) suggest that internal concentrations were by far the lowest for BPAF and by far the highest for BPS, e.g., for the Cmax, the P5 of BPS uncertainty was still higher than the P95 of BPAF uncertainty for all variability percentiles. This difference suggests that parameters varied in the uncertainty loop, such as hepatic sulfation, will probably not cause major shifts in internal concentrations of unconjugated BPs. 

However, the metabolism of other BPs does not necessarily need to follow the patterns we saw when comparing hepatic glucuronidation and sulfation for BPA. A pilot study on BPF metabolism with three subjects showed subject-specific differences, with glucuronidation being the only metabolism pathway for two subjects, and BPF-s being the major metabolite (75%) for the third subject (the oldest volunteer with 82 y) (Dumont et al. 2011). In this context, we want to point out again that we could not calibrate the PBPK models for BPF and BPAF, and the conjugation with sulfate for BPS with appropriate in vivo data. Future studies may therefore focus on (a) the acquisition of in vivo toxicokinetic data for BPS, BPF, and BPAF (explicitly differentiating between glucuronidation and sulfation), e.g., with controlled biomonitoring and/or animal studies, and (b) the sulfation kinetics of all BP analogs. 

### Model Evaluation – Comparison to Biomonitoring Data 

The model evaluation with the biomonitoring study by Teeguarden et al. (2015) showed that predicted average values for Cmax and AUC were 1.3 to 3 times higher than measured (Table 11). Important differences between the studies by Thayer et al. (2015), which was used for calibrating the PBPK model, and Teeguarden et al. (2015) were the dosed amounts, dosing vehicles, and fasting conditions used. In relative terms, the study by Thayer et al. (2015) led to higher concentrations of unconjugated BPA than the study by Teeguarden et al. (2015). Dosing vehicles (cookie vs. soup) could have an influence on the uptake of BPA (Yang et al. 2015). Also, the breakfast before the BPA dosing (Teeguarden et al. 2015) could have influenced the peroral uptake in comparison with the BPA dosing after a fasting period (Thayer et al. 2015). 



<!-- Start of picture text -->
0.02 0.10 0.5 1 2 5 0.001 0.005 0.02 0.1 0.5<br>daily AUC (nM  h per day). Cmax (nM)<br>BPA   BPS   BPF   BPAF<br>__ Variability of basic model         P50 uncertainty          P5 & P95 uncertainty_ _ . . . .<br>1<br>0.8<br>0.6<br>0.4<br>Probability<br>0.2<br>0<br><!-- End of picture text -->

Figure 6. Cumulative density functions for the AUC (in steady state) and Cmax of serum concentrations of women (18–45 y) for unconjugated BPA, BPS, BPF, and BPAF in the two-dimensional Monte Carlo Analysis (Tables 3 and 5 show dosing and uptake parameters). Shown are the variabilities of the basic models, and of the P5, P50, and P95 of the uncertainty iterations. Note: AUC, area under the curve; BP, bisphenol; BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; Cmax, maximal concentration; P, percentile. 

126(7) July 2018 

Environmental Health Perspectives 

077002-12 

Table 10. Values for AUC and Cmax predicted for the unconjugated bisphenols in serum of females of childbearing age in the two-dimensional Monte Carlo analysis (n = 1,000 � 1,000) after peroral and dermal exposures as estimated by the EFSA CEF (2015) for BPA in the high-exposure scenario. 

||AUC|(nM*h|per day i|n steady|state)||Cm|ax (pM|)||
|---|---|---|---|---|---|---|---|---|---|---|
|Uncertainty|Mean|SD|5%|50%|95%|Mean|SD|5%|50%|95%|
|BPA|||||||||||
|basic model|0.622|0.247|0.309|0.57|1.09|31.4|12.3|16.2|29.2|53.6|
|5%|0.201|0.0764|0.101|0.187|0.351|11.6|4.96|5.59|10.6|21.8|
|50%|0.481|0.182|0.252|0.451|0.812|24.1|9.54|12.7|22.6|41.3|
|95%|0.998|0.372|0.484|0.947|1.70|46.5|17.4|23.0|43.7|79.7|
|BPS|||||||||||
|basic model|2.15|0.739|1.18|2.03|3.53|172|56.9|95.8|165|276|
|5%|0.295|0.103|0.155|0.279|0.484|20.1|9.29|9.24|18.1|37.6|
|50%|0.602|0.216|0.328|0.569|1.00|38.0|15.1|20.3|35.4|64.6|
|95%|1.39|0.510|0.764|1.28|2.37|87.0|31.0|47.4|82.0|147|
|BPF|||||||||||
|basic model|0.651|0.255|0.311|0.61|1.11|34.0|12.8|16.9|32.0|58.5|
|5%|0.216|0.0784|0.109|0.205|0.363|10.6|3.39|5.79|10.3|16.7|
|50%|0.469|0.172|0.240|0.449|0.769|22.9|8.16|11.1|21.9|37.6|
|95%|0.825|0.297|0.422|0.782|1.37|41.1|14.9|22.1|38.4|69.9|
|BPAF|||||||||||
|basic model|0.285|0.116|0.133|0.261|0.498|12.2|4.81|5.86|11.3|21.0|
|5%|0.0822|0.030|0.0422|0.0783|0.136|3.79|1.50|1.88|3.52|6.54|
|50%|0.203|0.0721|0.108|0.191|0.34|8.86|3.47|4.19|8.24|15.0|
|95%|0.352|0.138|0.157|0.328|0.606|15.1|6.16|6.90|14.1|26.9|



Note: AUC, area under the curve; BPA, bisphenol A; BPAF, bisphenol AF; BPF, bisphenol F; BPS, bisphenol S; Cmax, maximum concentration; SD, standard deviation. 

The comparison with biomonitoring data investigated by Hormann et al. (2014) showed that the basic model could predict BPA serum concentrations of the two female subjects, but neither the BPA serum concentrations of the male subject nor concentrations of BPA-g and BPA-s for all three subjects. This only partial match might be due to our model not including all aspects necessary for this case. One possible explanation could be a lower extent of glucuronidation for the two female subjects than modeled, as important enzymes for glucuronidation can be expressed polymorphically (Hanioka et al. 2008; Skledar et al. 2015). Another possible explanation might be that the excretion of glucuronide and sulfate is subject to high variability and was more effective in the study by Hormann et al. (2014). This would be in line with the fast elimination of BPS-g observed by Oh et al. (2018), but not in line with other BPA biomonitoring studies (Teeguarden et al. 2015; Thayer et al. 2015; Völkel et al. 2002). An increase of the EHR percentage would rather not improve the match between model predictions and measurements, as measurements were lower than modeled concentrations if the deviation were substantial. Raising the EHR percentage would increase the residence time of BPA and BPA-g and would lead to even higher AUCs of modeled concentrations. Finally, with only three subjects in the scenario modeled, the sample size is 

too small to conclude on rationales, and further studies on human volunteers are needed to examine reasons behind the observed differences. 

### Internal Exposure Assessments 

Our results suggest that dermal exposure could be of high importance with respect to endocrine disrupting effects of BPs, because both BP uptake and excretion occurred later after dermal than after peroral exposure, and concentrations of unconjugated BPs in serum and tissues were elevated over a longer time period. This pattern was also observed by Mielke et al. (2011), who modeled BPA concentration–time profiles in blood, liver, and kidney after dermal, peroral, and aggregate dermal and peroral exposures. The prolonged rise of the internal unconjugated BP concentration–time curves due to dermal exposure might considerably influence the AUC, which represents the total exposure over time and is a good biomarker for chronic effects. Our results also suggest that replacing BPA byits structural analogs couldresult in similar pharmacokinetic patterns, with higher estimated serum concentrations predicted for some BPs. Gonadal BPA concentrations were mostly higher than those of other analogs, due to BPA having the highest PTS gonads/ serum of all BPs in our models. The concentrations in gonads were mostly modeled based on QSAR-derived partitioning coefficients, so that they are more uncertain than the serum levels. However, they are particularly relevant for risk assessment and practically unmeasurable in humans, so that pharmacokinetic models currently represent the only possibility to predict them. 

Serum concentration differences after peroral exposure can probably be directly attributed to the differences in hepatic and intestinal glucuronidation rates among the analogs. After dermal exposure, intestinal glucuronidation most likely does not play a role, and BPs are present in the serum prior to hepatic glucuronidation. Therefore, the PTS skin/serum and serum/liver become more influential. The curve shapes of the concentration-time profiles after peroral and dermal exposure differ largely because of the different extent of metabolism and the differences between dermal and peroral absorption half-lives. As seen in the basic model results for BPAF (Table 9), the highest Cmax and AUC in serum and gonads were observed in male adolescents. Adolescents obtained the highest external dermal exposures (Table 4), which suggests that this exposure route is especially important for BPAF exposure. This could be caused by the comparatively high lipophilicity of BPAF (logPow of about 2.8 to 4.8; Choi and Lee 2017), resulting in slow partitioning from liver to blood, which enhances the residence time in the metabolizing liver. In addition, the glucuronidation rate was higher for BPAF than for the other BPs in the concentration ranges observed in the liver and the intestine (Figure 3). Contrarily, for BPS, peroral exposure represented the predominant exposure route even for adolescents and adults. BPS is more hydrophilic (logPow of about 

Table 11. Comparison of measured and predicted pharmacokinetic parameters for 10 adults after peroral ingestion of 30 lg d6-BPA/kg bodyweight in soup (Teeguarden et al. 2015) and for 3 adults after handling BPA-containing receipts and eating French fries subsequently (Hormann et al. 2014). 

||BPA, me|an (range)|BPA-g, m|ean (range)|BPA-s, me|an (range)|
|---|---|---|---|---|---|---|
|Study/ parameter|M|P|M|P|M|P|
|Teeguarden et al. (2015)|||||||
|Cmax (nM)|0.43 (0.3–0.7)|1.31 (0.877–1.66)|286 (173–386)|610 (580–648)|18 (10.4–29.9)|22.9 (16.6–27.9)|
|tmax (h)|1.6 (0.5–2.2)|0.72 (0.667–0.767)|1.2 (0.8–2.2)|0.937 (0.933–0.967)|2.2 (1.2–5.2)|2.03 (2.00–2.03)|
|AUC (nM*h per day)|2.5 (1.4–5.7)|4.15 (2.91–5.15)|680 (570.8–1,210)|1,111 (1,050–1,210)|131 (54.9–298)|179 (117–179)|
|Hormann et al. (2014)|||||||
|Cmax (nM)|16.5 (1.85–25.7)|29.8 (23.4–35.8)|6.48 (5.04–8.28)|163 (118–207)|4.22 (3.72–4.62)|39.3 (30.1–47.7)|
|tmax (h)|0.583 (0.25–1.0)|0.367 (0.333–0.400)|1.17 (1–1.5)|0.744 (0.733–0.833)|0.833 (0–1.5)|2.23 (2.00–2.60)|
|AUC (nM*h for 1.5 h)|15.5 (0.986–23.2)|27.1 (24.1–29.9)|6.66 (5.52–8.34)|170 (127–211)|3.61 (2.60–4.52)|33.1 (22.7–43.1)|



Note: Mean stands for the arithmetic mean. AUC, area under the curve; BPA, bisphenol A; Cmax, maximum concentration; d6, deuterated; g, glucuronide; M, measured; P, predicted; s, sulfate; tmax, timing of maximum concentration. 

126(7) July 2018 

Environmental Health Perspectives 

077002-13 

1.7–2.1; Choi and Lee 2017) and was glucuronized with the lowest rate of all BPs in the concentration ranges present in the intestine and the liver. The low glucuronidation rates might be an important reason for the high internal concentrations of unconjugated BPS, which have also been observed in the biomonitoring study by Oh et al. (2018). In this respect, the results of our kinetic experiments are in good agreement with the pharmacokinetics observed in humans. Measured concentrations of unconjugated BPS were higher and measured concentrations of BPS-g were lower than modeled, which implies that in vivo BPS glucuronidation rates might be even lower than found in vitro. 

Exposure differences between age groups in our model simulations were mostly caused by the exposure patterns and anatomical differences of the different age groups and genders (Tables 4 and S1). However, one should keep in mind that the glucuronidation kinetics were assessed with adult hepatocytes, and the PBPK models for BPA and BPS were calibrated with measurements in adult body fluids. Therefore, the exposure differences might increase if age-group-specific metabolism parameters and biomonitoring data were available. 

For assessing the risk of BP analogs, potencies of their effects on endocrine receptors need to be taken into account as well, and they have already been investigated with various assays. A study investigating all compounds of interest in the MCF-7 Estrogen Luciferase Reporter Assay on estrogen receptor binding found that BPAF has a 13 times higher estrogenic potency than BPA (EC50 of 0.05 vs. 0:63 lM), whereas BPF and BPS showed a bit more than half of the potency of BPA (EC50 of 1.0 and 1:1 lM) (Kitamura et al. 2005). Other studies showed comparable tendencies (Fic et al. 2014; Skledar et al. 2016). Although BPAF showed the lowest serum concentrations, it could therefore still be of the highest risk regarding estrogenic activity. In a back-of-the-envelope calculation, we determined margins of exposure (MOE) for the different analogs according to MOE = EC50=Cmax with EC50 being the halfmaximal effect concentration in the assay on estrogen receptor binding (Kitamura et al. 2005) and Cmax being the highest blood or gonadal concentration obtained in the basic PBPK model [Table 9, external exposures for all BPs were assumed to be represented by the upper estimate for external BPA exposure estimated by the EFSA CEF (2015)]. The calculated MOE was the lowest for BPS in serum and for BPAF in gonads with 2,440 and 1,810, respectively, in comparison with BPA-MOEs of 12,000 and 4,670 in serum and gonads, respectively. All those MOEs are well above 100, which is considered a conservative margin (EFSA CEF 2015). However, one should note that this calculation is based on estrogenic potencies from one in vitro assay, and risk estimations should be further refined when additional studies on the BP analogs become available. Regarding the results of the 2D-MC analysis (Table 10, same external exposure estimates), the MOE in serum of females of childbearing age was the lowest for BPAF, with 1,860 when regarding the P95/P95. The consideration of serum concentrations of pregnant women is of special importance, because it was shown that BPA can cross the placental barrier (Mørck et al. 2010). One third of fetal plasma levels investigated by Schönfelder et al. (2002) were higher than the corresponding maternal plasma levels, reaching concentrations up to 7 times higher than the concentrations in corresponding maternal plasma. This might be due to the comparatively low glucuronidation and high deglucuronidation capacity in fetal compartments (Lucier et al. 1977). With this worst-case estimation and internal exposures from the 2D-MC analysis, the MOE between Cmax in fetal serum and EC50 could reach values of 266, 1,070, 1,130, and 2,040 for BPAF, BPS, BPA, and BPF, respectively. For BPA, numerous studies on endocrine disrupting effects were conducted, and some of them found effects at considerably lower 

doses (Judy et al. 1999; Walsh et al. 2005) in comparison with the study by Kitamura et al. (2005). Walsh et al. (2005) found an EC50 of 0:10 nM for an increase of calcium ion concentration in human breast-cancer cell lines. This effect concentration could lead to an MOE of 1.25 when regarding the Cmax of BPA (P95/ P95) in serum of females. Assuming worst-case accumulations in the fetus, this would mean an MOE of 0.179 in fetal serum; hence, no safety margin would exist. Such relations are equally possible for other analogs such as BPAF, which has shown higher effects than BPA in many studies (Chen et al. 2016). 

In summary, on the basis of our PBPK models we conclude that a complete replacement of BPA with BPS might lead to elevated BP concentrations in serum and a replacement with BPS or BPAF might lead to increased estrogenic activities and lowered MOEs compared to BPA. 

## Conclusions 

Our data suggest that the replacement of BPA with structural analogs may not lower the risk regarding endocrine disruption. With the same peroral and dermal exposures for all BP analogs, our model predicted that BPS exposure would result in the highest internal concentrations of unconjugated BPs in both serum and gonads. Taking into account estrogenic agonistic potencies as well, exposure to BPAF and BPS might be the most critical. The contribution of dermal and peroral exposure to the total internal exposure to unconjugated BPs varied among the analogs, with peroral exposure being the most relevant route for BPS and dermal exposure for BPAF. For a better understanding of the pharmacokinetic behavior of BP analogs, experiments on their hepatic and intestinal sulfation and their tissue-to-serum partitioning, and the acquisition of additional in vivo toxicokinetic data for model calibration and validation would be helpful. 

## Acknowledgments 

We thank X. Yang for fruitful discussions about her published PBPK model and for helping us to find the reason for the modeling discrepancies. We also thank F. vom Saal and J. Taylor for kindly providing the measurement data related to the publication by Hormann et al. (2014). Furthermore, we thank H. Mielke, F. Partosch, and R. Pirow for explanations and help regarding the PBPK model developed by Mielke et al. (2011) and V. Kumar for helpful discussions about PBPK modeling of BPA in general. 

Our research project received funding from the European Union Horizon 2020 Framework Program under Grant Agreement 633172 (European Test and Risk Assessment Strategies for Mixtures, EuroMix) and from the Slovenian Research Agency (Grant P1-0208). This publication reflects only the authors’ views, and the European community is not liable for any use made of the information contained therein. 

## References 

- Barter ZE, Bayliss MK, Beaune PH, Boobis AR, Carlile DJ, Edwards RJ, et al. 2007. Scaling factors for the extrapolation of in vivo metabolic drug clearance from in vitro data: reaching a consensus on values of human micro-somal protein and hepatocellularity per gram of liver. Curr Drug Metab 8(1):33–45, PMID: 17266522, https://doi.org/10.2174/138920007779315053. 

- Bautista-Toledo I, Ferro-García MA, Rivera-Utrilla J, Moreno-Castilla C, Vegas Fernández FJ. 2005. Bisphenol A removal from water by activated carbon. effects of carbon characteristics and solution chemistry. Environ Sci Technol 39(16):6246–6250, PMID: 16173588, https://doi.org/10.1021/es0481169. 

- Biedermann S, Tschudin P, Grob K. 2010. Transfer of bisphenol A from thermal printer paper to the skin. Anal Bioanal Chem 398(1):571–576, PMID: 20623271, https://doi.org/10.1007/s00216-010-3936-9. 

Boucher JG, Boudreau A, Ahmed S, Atlas E. 2015. In vitro effects of bisphenol A β- D-Glucuronide (BPA-G) on adipogenesis in human and murine preadipocytes. Environ Health Perspect 123(12):1287–1293, PMID: 26018136. 

126(7) July 2018 

Environmental Health Perspectives 

077002-14 

- Brown RP, Delp MD, Lindstedt SL, Rhomberg LR, Beliles RP. 1997. Physiological parameter values for physiologically based pharmacokinetic models. Toxicol Ind Health 13(4):407–484, PMID: 9249929, https://doi.org/10.1177/074823379701300401. 

- Calafat AM, Ye X, Wong L-Y, Reidy JA, Needham LL. 2008. Exposure of the U.S. population to bisphenol A and 4-tertiary-Octylphenol: 2003-2004 test. Environ Health Perspect 116(1):39–44, PMID: 18197297, https://doi.org/10.1289/ehp.10753. 

- Chen D, Kannan K, Tan H, Zheng Z, Feng Y-L, Wu Y, et al. 2016. Bisphenol analogues other than BPA: environmental occurrence, human exposure, and toxicity—a review. Environ Sci Technol 50(11):5438–5453, PMID: 27143250, https://doi.org/10.1021/acs.est.5b05387. 

- Choi YJ, Lee LS. 2017. Partitioning behavior of bisphenol alternatives BPS and BPAF compared to BPA. Environ Sci Technol 51(7):3725–3732, PMID: 28274112, https://doi.org/10.1021/acs.est.6b05902. 

- Coughlin JL, Thomas PE, Buckley B. 2012. Inhibition of genistein glucuronidation by bisphenol A in human and rat liver microsomes. Drug Metab Dispos 40(3):481– 485, PMID: 22146138, https://doi.org/10.1124/dmd.111.042366. 

- Covaci A, Hond ED, Geens T, Govarts E, Koppen G, Frederiksen H, et al. 2015. Urinary BPA measurements in children and mothers from six European member states: overall results and determinants of exposure. Environ Res 141:77– 85, PMID: 25440295, https://doi.org/10.1016/j.envres.2014.08.008. 

- DeJongh J, Verhaar HJM, Hermens JLM. 1997. A quantitative property-property relationship (QPPR) approach to estimate in vitro tissue-blood partition coefficients of organic chemicals in rats and humans. Arch Toxicol 72(1):17–25, PMID: 9458186, https://doi.org/10.1007/s002040050463. 

- Demierre A-L, Peter R, Oberli A, Bourqui-Pittet M. 2012. Dermal penetration of bisphenol A in human skin contributes marginally to total exposure. Toxicol Lett 213(3):305–308, PMID: 22796587, https://doi.org/10.1016/j.toxlet.2012.07. 001. 

- Doerge DR, Twaddle NC, Vanlandingham M, Brown RP, Fisher JW. 2011. Distribution of bisphenol A into tissues of adult, neonatal, and fetal Sprague–Dawley rats. Toxicol Appl Pharmacol 255(3):261–270, PMID: 21820460, https://doi.org/10.1016/j. taap.2011.07.009. 

- Draganov DI, Markham DA, Beyer D, Waechter JM, Dimond SS, Budinsky RA, et al. 2015. Extensive metabolism and route-dependent pharmacokinetics of bisphenol A (BPA) in neonatal mice following oral or subcutaneous administration. Toxicology 333:168–178., PMID: 25929835, https://doi.org/10.1016/j.tox.2015.04. 012. 

- Dumont C, Perdu E, Sousa G, de Debrauwer L, Rahmani R, Cravedi J-P, et al. 2011. Bis(hydroxyphenyl)methane—bisphenol F—metabolism by the HepG2 human hepatoma cell line and cryopreserved human hepatocytes. Drug Chem Toxicol 34(4):445–453, PMID: 21770713, https://doi.org/10.3109/01480545.2011.585651. 

- EC (European Commission). 2011a. Commission Directive 2011/8/EU of 28 January 2011 amending Directive 2002/72/EC as regards the restriction of use of Bisphenol A in plastic infant feeding bottles. 

- EC. 2011b. Commission Regulation (EU) No 10/2011 of 14 January 2011 on Plastic Materials and Articles Intended to Come into Contact with Food. 

- Edginton AN, Schmitt W, Willmann S. 2006. Development and evaluation of a generic physiologically based pharmacokinetic model for children. Clin Pharmacokinet 45(10):1013–1034, PMID: 16984214, https://doi.org/10.2165/ 00003088-200645100-00005. 

- EFSA CEF (European Food Safety Authority Panel on Food Contact Materials, Enzymes, Flavourings and Processing Aids). 2015. Scientific opinion on the risks to public health related to the presence of bisphenol A (BPA) in foodstuffs. EFSA Journal 13(1):3978, https://doi.org/10.2903/j.efsa.2015.3978. 

- EFSA Scientific Committee. 2016. Guidance on Uncertainty in EFSA Scientific Assessment - Revised Draft for Internal Testing. 

- Elsby R, Maggs JL, Ashby J, Park BK. 2001. Comparison of the modulatory effects of human and rat liver microsomal metabolism on the estrogenicity of bisphenol A: implications for extrapolation to humans. J Pharmacol Exp Ther 297(1):103–113, PMID: 11259533. 

- EU (European Union). 2008. Updated European Risk Assessment Report 4,4’isopropylidenediphenol (Bisphenol-A). 

- U.S. FDA. 2013. FDA Regulations No Longer Authorize the Use of BPA in Infant Formula Packaging Based on Abandonment; Decision Not Based on Safety. http://www.fda.gov/Food/NewsEvents/ConstituentUpdates/ucm360147.htm [accessed 14 June, 2018]. 

- U.S. FDA (U.S. Food and Drug Administration). 2014. Bisphenol A (BPA): Use in Food Contact Application. http://www.fda.gov/Food/IngredientsPackagingLabeling/ FoodAdditivesIngredients/ucm064437.htm [accessed 14 June, 2018]. 

- Fic A, Žegura B, Gramec D, Maši�c LP. 2014. Estrogenic and androgenic activities of TBBA and TBMEPH, metabolites of novel brominated flame retardants, and selected bisphenols, using the XenoScreen XL YES/YAS assay. Chemosphere 112:362–369, PMID: 25048928, https://doi.org/10.1016/j.chemosphere.2014.04.080. 

- French National Assembly and Senate. 2010. LOI n° 2010-729 du 30 juin 2010 tendant à suspendre la commercialisation de tout conditionnement comportant du bisphénol A et destiné à recevoir des produits alimentaires. 

- Garcia-Hidalgo E, von Goetz N, Siegrist M, Hungerbühler K. 2017. Use-patterns of personal care and household cleaning products in Switzerland. Food Chem Toxicol 99:24–39, PMID: 27818321, https://doi.org/10.1016/j.fct.2016.10.030. 

- Gertz M, Houston JB, Galetin A. 2011. Physiologically-based pharmacokinetic modeling of intestinal first-pass metabolism of CYP3A substrates with high intestinal extraction. Drug Metab Dispos 39(9):1633, https://doi.org/10.1124/dmd.111. 039248. 

- Ginsberg G, Rice DC. 2009. Does rapid metabolism ensure negligible risk from bisphenol A? Environ Health Perspect 117(11):1639–1643, PMID: 20049111, https://doi.org/10.1289/ehp.0901010. 

- Goldinger DM, Demierre A-L, Zoller O, Rupp H, Reinhard H, Magnin R, et al. 2015. Endocrine activity of alternatives to BPA found in thermal paper in Switzerland. Regul Toxicol Pharmacol 71(3):453–462, PMID: 25579646, https://doi.org/10.1016/j. yrtph.2015.01.002. 

- Gramec Skledar D, Peterlin Maši�c L. 2016. Bisphenol A and its analogs: do their metabolites have endocrine activity? Environ Toxicol Pharmacol 47:182–199, PMID: 27771500, https://doi.org/10.1016/j.etap.2016.09.014. 

- Hanioka N, Naito T, Narimatsu S. 2008. Human UDP-glucuronosyltransferase isoforms involved in bisphenol A glucuronidation. Chemosphere 74(1):33–36, PMID: 18990428, https://doi.org/10.1016/j.chemosphere.2008.09.053. 

- Henderson JM, Heymsfield SB, Horowitz J, Kutner MH. 1981. Measurement of liver and spleen volume by computed tomography. Assessment of reproducibility and changes found following a selective distal splenorenal shunt. Radiology 141(2):525–527, PMID: 6974875, https://doi.org/10.1148/radiology. 141.2.6974875. 

- Herman RJ, Van Pham JD, Szakacs CBN. 1989. Disposition of lorazepam in human beings: enterohepatic recirculation and first-pass effect. Clin Pharmacol Ther 46(1):18–25, PMID: 2743706, https://doi.org/10.1038/clpt.1989.101. 

- Hewitt NJ, Bühring K-U, Dasenbrock J, Haunschild J, Ladstetter B, Utesch D. 2001. Studies comparing in vivo:in vitro metabolism of three pharmaceutical compounds in rat, dog, monkey, and human using cryopreserved hepatocytes, microsomes, and collagen gel immobilized hepatocyte cultures. Drug Metab Dispos 29(7):1042–1050, PMID: 11408372. 

- Hiller A, Nguyen N, Strassburg CP, Li Q, Jainta H, Pechstein B, et al. 1999. Retigabine N-glucuronidation and its potential role in enterohepatic circulation. Drug Metab Dispos Biol Dispos 27(5):605–612, PMID: 10220490. 

- Hoffman FO, Hammonds JS. 1994. Propagation of uncertainty in risk assessments: the need to distinguish between uncertainty due to lack of knowledge and uncertainty due to variability. Risk Anal 14(5):707–712, PMID: 7800861, https://doi.org/10. 1111/j.1539-6924.1994.tb00281.x. 

- Hormann AM, Saal FS, vom Nagel SC, Stahlhut RW, Moyer CL, Ellersieck MR, et al. 2014. Holding thermal receipt paper and eating food after using hand sanitizer results in high serum bioactive and urine total levels of bisphenol A (BPA). PLOS ONE 9(10):e110509, PMID: 25337790, https://doi.org/10.1371/journal.pone. 0110509. 

- ICRP (International Commission on Radiological Protection). 2002. Basic anatomical and physiological data for use in radiological protection: reference values. A report of age- and gender-related differences in the anatomical and physiological characteristics of reference individuals. ICRP Publication 89. Ann ICRP 32:1– 277, PMID: 14506981, https://doi.org/10.1016/S0146-6453(03)00002-2. 

- Ito K, Houston JB. 2005. Prediction of human drug clearance from in vitro and preclinical data using physiologically based and empirical approaches. Pharm Res 22(1):103–112, PMID: 15771236, https://doi.org/10.1007/s11095-004-9015-1. 

- Judy BM, Nagel SC, Thayer KA, Saal FSV, Welshons WV. 1999. Low-dose bioactivity of xenoestrogens in animals: fetal exposure to low doses of methoxychlor and other xenoestrogens increases adult prostate size in mice. Toxicol Ind Health 15(1-2):12–25, PMID: 10188188, https://doi.org/10.1177/074823379901500103. 

- Kitamura S, Suzuki T, Sanoh S, Kohta R, Jinno N, Sugihara K, et al. 2005. Comparative study of the endocrine-disrupting activity of bisphenol A and 19 related compounds. Toxicol Sci 84(2):249–259, PMID: 15635150, https://doi.org/ 10.1093/toxsci/kfi074. 

- Kortejärvi H, Urtti A, Yliperttula M. 2007. Pharmacokinetic simulation of biowaiver criteria: the effects of gastric emptying, dissolution, absorption and elimination rates. Eur J Pharm Sci 30(2):155–166, PMID: 17187967, https://doi.org/10.1016/j. ejps.2006.10.011. 

- Kuester RK, Sipes IG. 2007. Prediction of metabolic clearance of bisphenol A (4,4<sup>0</sup> - Dihydroxy-2,2-diphenylpropane) using cryopreserved human hepatocytes. Drug Metab Dispos 35(10):1910–1915, PMID: 17646283, https://doi.org/10.1124/dmd.107. 014787. 

- Kurebayashi H, Okudaira K, Ohno Y. 2010. Species difference of metabolic clearance of bisphenol A using cryopreserved hepatocytes from rats, monkeys and humans. Toxicol Lett 198(2):210–215, PMID: 20599483, https://doi.org/10.1016/j. toxlet.2010.06.017. 

- Lebacq T. 2015. Anthropométrie (IMC, tour de taille et ratio tour de taille/taille). In: Enquête de consommation alimentaire 2014–2015. Rapport 1 [in French]. Brussels, Belgium:WIV-ISP. 

126(7) July 2018 

Environmental Health Perspectives 

077002-15 

Li M, Yang Y, Yang Y, Yin J, Zhang J, Feng Y, et al. 2013. Biotransformation of bisphenol AF to its major glucuronide metabolite reduces estrogenic activity. PLOS ONE 8(12):e83170, PMID: 24349450, https://doi.org/10.1371/journal.pone.0083170. 

- Liao C, Kannan K. 2013. Concentrations and profiles of bisphenol A and other bisphenol analogues in foodstuffs from the United States and their implications for human exposure. J Agric Food Chem 61(19):4655–4662, PMID: 23614805, https://doi.org/10.1021/jf400445n. 

- Liao C, Kannan K. 2011. Widespread occurrence of bisphenol A in paper and paper products: implications for human exposure. Environ Sci Technol 45(21):9372– 9379, PMID: 21939283, https://doi.org/10.1021/es202507f. 

- Liao C, Liu F, Guo Y, Moon H-B, Nakata H, Wu Q, et al. 2012. Occurrence of eight bisphenol analogues in indoor dust from the United States and several Asian countries: implications for human exposure. Environ Sci Technol 46(16):9138– 9145, PMID: 22784190, https://doi.org/10.1021/es302004w. 

- Liao C, Liu F, Kannan K. 2012. Bisphenol S, a new bisphenol analogue, in paper products and currency bills and its association with bisphenol A residues. Environ Sci Technol 46(12):6515–6522, PMID: 22591511, https://doi.org/10.1021/ es300876n. 

- Lucier GW, Sonawane BR, McDaniel OS. 1977. Glucuronidation and deglucuronidation reactions in hepatic and extrahepatic tissues during perinatal development. Drug Metab Dispos 5(3):279–287, PMID: 17527. 

- Matthews JB, Twomey K, Zacharewski TR. 2001. In vitro and in vivo interactions of bisphenol A and its metabolite, bisphenol A Glucuronide, with estrogen receptors α and β. Chem Res Toxicol 14(2):149–157, PMID: 11258963, https://doi.org/ 10.1021/tx0001833. 

- Mazur CS, Kenneke JF, Hess-Wilson JK, Lipscomb JC. 2010. Differences between human and rat intestinal and hepatic bisphenol A glucuronidation and the influence of alamethicin on in vitro kinetic measurements. Drug Metab Dispos 38(12):2232–2238, PMID: 20736320, https://doi.org/10.1124/dmd.110.034819. 

- Mielke H, Gundert-Remy U. 2009. Bisphenol A levels in blood depend on age and exposure. Toxicol Lett 190(1):32–40, PMID: 19560527, https://doi.org/10.1016/j. toxlet.2009.06.861. 

- Mielke H, Partosch F, Gundert-Remy U. 2011. The contribution of dermal exposure to the internal exposure of bisphenol A in man. Toxicol Lett 204(2-3):190–198, PMID: 21571050, https://doi.org/10.1016/j.toxlet.2011.04.032. 

- Mørck TJ, Sorda G, Bechi N, Rasmussen BS, Nielsen JB, Ietta F, et al. 2010. Placental transport and in vitro effects of Bisphenol A. Reprod Toxicol 30(1):131–137, PMID: 20214975, https://doi.org/10.1016/j.reprotox.2010.02.007. 

- Motmans R. 2005. DINBelg. DINBelg 2005. http://www.dinbelg.be/ [accessed 20 May 2017]. 

- Nicklas TA, Baranowski T, Cullen KW, Berenson G. 2001. Eating patterns, dietary quality and obesity. J Am Coll Nutr 20(6):599–608, PMID: 11771675, https://doi.org/ 10.1080/07315724.2001.10719064. 

- Oberle RL, Chen T-S, Lloyd C, Barnett JL, Owyang C, Meyer J, et al. 1990. The influence of the interdigestive migrating myoelectric complex on the gastric emptying of liquids. Gastroenterology 99(5):1275–1282, PMID: 2210236, https://doi.org/10. 1016/0016-5085(90)91150-5. 

- Oh J, Choi JW, Ahn Y-A, Kim S. 2018. Pharmacokinetics of bisphenol S in humans after single oral administration. Environ Int 112:127–133, PMID: 29272776, https://doi.org/10.1016/j.envint.2017.11.020. 

- Paigen K. 1989. Mammalian β-Glucuronidase: genetics, molecular biology, and cell biology. In: Progress in Nucleic Acid Research and Molecular Biology (W.E. Cohn and K. Moldave, eds). Vol. 37. New York, NY:Academic Press. 155–205. 

- Paine MF, Khalighi M, Fisher JM, Shen DD, Kunze KL, Marsh CL, et al. 1997. Characterization of interintestinal and intraintestinal variations in human CYP3A-dependent metabolism. J Pharmacol Exp Ther 283(3):1552–1562, PMID: 9400033. 

- Pelkonen O, Kaltiala EH, Larmi TKI, Kärki NT. 1973. Comparison of activities of drug-metabolizing enzymes in human fetal and adult livers. Clin Pharmacol Ther 14(5):840–846, PMID: 4147122, https://doi.org/10.1002/cpt1973145840. 

- Reed MJ, Purohit A, Woo LWL, Newman SP, Potter BVL. 2005. Steroid sulfatase: molecular biology, regulation, and inhibition. Endocr Rev 26(2):171–202, PMID: 15561802, https://doi.org/10.1210/er.2004-0003. 

- Roberts MS, Magnusson BM, Burczynski FJ, Weiss M. 2002. Enterohepatic circulation. Clin Pharmacokinet 41(10):751–790, PMID: 12162761, https://doi.org/10. 2165/00003088-200241100-00005. 

- Rocha BA, Azevedo LF, Gallimberti M, Campiglia AD, Barbosa F. 2015. High levels of bisphenol A and bisphenol S in Brazilian thermal paper receipts and estimation of daily exposure. J Toxicol Environ Health Part A 78(18):1181–1188, PMID: 26407846, https://doi.org/10.1080/15287394.2015.1083519. 

- Rochester JR, Bolden AL. 2015. Bisphenol S and F: a systematic review and comparison of the hormonal activity of bisphenol A substitutes. Environ Health Perspect 123(7):643–650, PMID: 25775505, https://doi.org/10.1289/ehp.1408989. 

- Rubin BS. 2011. Bisphenol A: an endocrine disruptor with widespread exposure and multiple effects. J Steroid Biochem Mol Biol 127(1–2):27–34, PMID: 21605673, https://doi.org/10.1016/j.jsbmb.2011.05.002. 

- Schmitt W. 2008. General approach for the calculation of tissue to plasma partition coefficients. Toxicol In Vitro 22(2):457–467, PMID: 17981004, https://doi.org/10. 1016/j.tiv.2007.09.010. 

- Schoene B, Fleischmann RA, Remmer H, Oldershausen HF. v. 1972. Determination of drug metabolizing enzymes in needle biopsies of human liver. Eur J Clin Pharmacol 4(2):65–73, PMID: 4144102, https://doi.org/10.1007/BF00562499. 

- Schönfelder G, Wittfoht W, Hopp H, Talsness CE, Paul M, Chahoud I. 2002. Parent bisphenol A accumulation in the human maternal-fetal-placental unit. Environ Health Perspect 110(11):A703–A707, PMID: 12417499. 

- Sheiner LB, Beal SL. 1981. Some suggestions for measuring predictive performance. J Pharmacokinet Biopharm 9(4):503–512, PMID: 7310648, https://doi.org/ 10.1007/BF01060893. 

- Skledar DG, Schmidt J, Fic A, Klop�ci�c I, Trontelj J, Dolenc MS, et al. 2016. Influence of metabolism on endocrine activities of bisphenol S. Chemosphere 157:152–159, PMID: 27213244, https://doi.org/10.1016/j.chemosphere.2016.05. 027. 

- Skledar DG, Troberg J, Lavdas J, Maši�c LP, Finel M. 2015. Differences in the glucuronidation of bisphenols F and S between two homologous human UGT enzymes, 1A9 and 1A10. Xenobiotica 45(6):511–519, PMID: 25547628, https://doi.org/10.3109/ 00498254.2014.999140. 

- Snyder RW, Maness SC, Gaido KW, Welsch F, Sumner SCJ, Fennell TR. 2000. Metabolism and disposition of bisphenol A in female rats. Toxicol Appl Pharmacol 168(3):225–234, PMID: 11042095, https://doi.org/10.1006/taap.2000. 9051. 

- SPARC. 2011. pKa/property server. http://archemcalc.com/sparc/ [accessed 5 July 2017]. 

- Squara P, Denjean D, Estagnasie P, Brusset A, Dib JC, Dubois C. 2007. Noninvasive cardiac output monitoring (NICOM): a clinical validation. Intensive Care Med 33(7):1191–1194, PMID: 17458538, https://doi.org/10.1007/s00134-007-0640-0. 

- Stossi F, Bolt MJ, Ashcroft FJ, Lamerdin JE, Melnick JS, Powell RT, et al. 2014. Defining estrogenic mechanisms of bisphenol A analogs through high throughput microscopy-based contextual assays. Chem Biol 21(6):743–753, PMID: 24856822, https://doi.org/10.1016/j.chembiol.2014.03.013. 

- Street CM, Zhu Z, Finel M, Court MH. 2017. Bisphenol-A glucuronidation in human liver and breast: identification of UDP-glucuronosyltransferases (UGTs) and influence of genetic polymorphisms. Xenobiotica 47(1):1–10, PMID: 26999266, https://doi.org/10.3109/00498254.2016.1156784. 

- Teeguarden JG, Twaddle NC, Churchwell MI, Yang X, Fisher JW, Seryak LM, et al. 2015. 24-hour human urine and serum profiles of bisphenol A: evidence against sublingual absorption following ingestion in soup. Toxicol Appl Pharmacol 288(2):131–142, PMID: 25620055, https://doi.org/10.1016/j.taap.2015.01.009. 

- Teeguarden JG, Waechter JM, Clewell HJ, Covington TR, Barton HA. 2005. Evaluation of oral and intravenous route pharmacokinetics, plasma protein binding, and uterine tissue dose metrics of bisphenol A: a physiologically based pharmacokinetic approach. Toxicol Sci 85(2):823–838, PMID: 15746009, https://doi.org/10.1093/toxsci/kfi135. 

- Thayer KA, Doerge DR, Hunt D, Schurman SH, Twaddle NC, Churchwell MI, et al. 2015. Pharmacokinetics of bisphenol A in humans following a single oral administration. Environ Int 83:107–115, PMID: 26115537, https://doi.org/10.1016/j. envint.2015.06.008. 

- Thayer KA, Taylor KW, Garantziotis S, Schurman SH, Kissling GE, Hunt D, et al. 2016. Bisphenol A, bisphenol S, and 4-Hydroxyphenyl 4-Isoprooxyphenylsulfone (BPSIP) in urine and blood of cashiers. Environ Health Perspect 124(4):437–444. , PMID: 26309242, https://doi.org/10.1289/ehp.1409427. 

- Thomopoulos NT. 2013. Essentials of Monte Carlo Simulation. Springer:New York. 

- Tobacman JK, Hinkhouse M, Khalkhali-Ellis Z. 2002. Steroid sulfatase activity and expression in mammary myoepithelial cells. J Steroid Biochem Mol Biol 81(1):65–68, PMID: 12127043, https://doi.org/10.1016/S0960-0760(02) 00048-1. 

- Toner F, Allan G, Beyer D, Dimond SS, Kocabas NA. 2016. The in vitro percutaneous absorption and metabolism of Bisphenol A (BPA) through fresh human skin. Toxicol Lett 258 (suppl):S180. PMID: 29154941, https://doi.org/10.1016/j. toxlet.2016.06.1669. 

- Trdan Lušin T, Roškar R, Mrhar A. 2012. Evaluation of bisphenol A glucuronidation according to UGT1A1*28 polymorphism by a new LC–MS/MS assay. Toxicology 292(1):33–41, PMID: 22154984, https://doi.org/10.1016/j.tox.2011.11.015. 

- Tsukioka T, Terasawa J, Sato S, Hatayama Y, Makino T, Nakazawa H. 2004. Development of analytical method for determining trace amounts of BPA in urine samples and estimation of exposure to BPA. J Environ Chem 14(1):57–63, https://doi.org/10.5985/jec.14.57. 

- Vandenberg LN, Hauser R, Marcus M, Olea N, Welshons WV. 2007. Human exposure to bisphenol A (BPA). Reprod Toxicol 24(2):139–177, https://doi.org/10. 1016/j.reprotox.2007.07.010. 

- Vogt W. 2014. Evaluation and optimisation of current milrinone prescribing for the treatment and prevention of low cardiac output syndrome in paediatric patients after open heart surgery using a physiology-based pharmacokinetic drug–disease 

126(7) July 2018 

Environmental Health Perspectives 

077002-16 

model. Clin Pharmacokinet 53(1):51–72, PMID: 23839530, https://doi.org/10.1007/ s40262-013-0096-z. 

- Völkel W, Colnot T, Csanády GA, Filser JG, Dekant W. 2002. Metabolism and kinetics of Bisphenol A in humans at low doses following oral administration. Chem Res Toxicol 15(10):1281–1287, PMID: 12387626, https://doi.org/10.1021/tx025548t. 

- von Goetz N, Pirow R, Hart A, Bradley E, Poças F, Arcella D, et al. 2017. Including non-dietary sources into an exposure assessment of the European Food Safety Authority: the challenge of multi-sector chemicals such as Bisphenol A. Regul Toxicol Pharmacol 85:70–78, PMID: 28185845, https://doi.org/10.1016/j.yrtph. 2017.02.004. 

- Walsh DE, Dockery P, Doolan CM. 2005. Estrogen receptor independent rapid nongenomic effects of environmental estrogens on [Ca2+]i in human breast cancer cells. Mol Cell Endocrinol 230(1–2):23–30, https://doi.org/10.1016/j.mce.2004.11.006. 

- Yang X, Doerge DR, Teeguarden JG, Fisher JW. 2015. Development of a physiologically based pharmacokinetic model for assessment of human exposure to 

   - bisphenol A. Toxicol Appl Pharmacol 289(3):442–456, PMID: 26522835, https://doi.org/10.1016/j.taap.2015.10.016. 

- Yu LX, Crison JR, Amidon GL. 1996. Compartmental transit and dispersion model analysis of small intestinal transit flow in humans. Int J Pharm 140(1):111–118, https://doi.org/10.1016/0378-5173(96)04592-9. 

- Zalko D, Jacques C, Duplan H, Bruel S, Perdu E. 2011. Viable skin efficiently absorbs and metabolizes bisphenol A. Chemosphere 82(3):424–430, PMID: 21030062, https://doi.org/10.1016/j.chemosphere.2010.09.058. 

- Zhang H, Zhang Y. 2006. Convenient nonlinear model for predicting the tissue/blood partition coefficients of seven human tissues of neutral, acidic, and basic structurally diverse compounds. J Med Chem 49(19):5815–5829, PMID: 16970406, https://doi.org/10.1021/jm051162e. 

- Zhang Q-Y, Dunbar D, Ostrowska A, Zeisloft S, Yang J, Kaminsky LS. 1999. Characterization of human small intestinal cytochromes P-450. Drug Metab Dispos 27(7):804–809, PMID: 10383924. 

126(7) July 2018 

Environmental Health Perspectives 

077002-17 

