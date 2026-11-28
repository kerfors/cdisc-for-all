# Test concept pages — examples

Pages written by `examples/test_concept.py` from the published graphs, one per SDTM CT test C-code: nine lab tests, Weight, and seven tests from the IS, EG, RE, MB and GF domains. Each is one self-contained HTML file: open it in a browser, or on GitHub Pages: https://kerfors.github.io/cdisc-for-all/examples/pages/ Every value on a page is a triple of the graphs; the page adds nothing.

Rebuild them (results equal while the graphs are unchanged):

    python examples/test_concept.py C105585 C64853 C64849 C51948 C63321 C64805 C64813 C45997 C100429 C25208 C181396 C187780 C181394 C117786 C38084 C64850 C181331 --out examples/pages

| Page | Test | Area | What it shows |
|---|---|---|---|
| [test_concept_C105585.html](test_concept_C105585.html) | GLUC / Glucose | Chemistry | BC Glucose Measurement, 7 DECs, 9 Specializations over blood, plasma, serum, serum or plasma, interstitial fluid and urine; GLUCPE, a test with its own NCIt concept under the same BC |
| [test_concept_C64853.html](test_concept_C64853.html) | K / Potassium | Chemistry, electrolyte | BC Potassium Measurement, 3 Specializations (KBLD, KSERPL, KURIN) |
| [test_concept_C64849.html](test_concept_C64849.html) | HBA1C / Hemoglobin A1C | Haematology | BC Hemoglobin A1C Measurement under Hemoglobin Measurement, 1 Specialization (HBA1CBLD) |
| [test_concept_C51948.html](test_concept_C51948.html) | WBC / Leukocytes | Haematology | BC Leukocyte Count under Blood Cell Count, 5 Specializations (WBCBLD, WBCURIN, WBCURINDIP, WBCURINPRES, WBCURINSEDPRES) |
| [test_concept_C63321.html](test_concept_C63321.html) | NEUT / Neutrophils | Haematology | BC Absolute Neutrophil Count and its parents, 1 Specialization (NEUTBLD) |
| [test_concept_C64805.html](test_concept_C64805.html) | INR / Prothrombin Intl. Normalized Ratio | Coagulation | BC International Normalized Ratio of Prothrombin Time under Prothrombin Time, 2 Specializations (INRBLD, INRPPP) |
| [test_concept_C64813.html](test_concept_C64813.html) | TSH / Thyrotropin | Endocrinology | BC Thyrotropin Measurement under Peptide Hormone Measurement, 2 Specializations (TSHBLD, TSHSERPL) |
| [test_concept_C45997.html](test_concept_C45997.html) | PH / pH | Urinalysis | BC pH under Physical Property, 1 Specialization (PHURIN) |
| [test_concept_C100429.html](test_concept_C100429.html) | A1AGLP / Alpha-1 Acid Glycoprotein | Chemistry | No COSMoS BC has its NCIt concept: the test terms and the concept only |
| [test_concept_C25208.html](test_concept_C25208.html) | WEIGHT / Weight | Vital signs | BC Weight (its NCIt concept, no DECs) and, from the test row, its child BC Body Weight with 3 DECs and 1 Specialization (WEIGHT) |
| [test_concept_C181396.html](test_concept_C181396.html) | MBNAB / Neutralizing Microbial-induced Antibody | Immunogenicity (IS) | No COSMoS BC has its NCIt concept and no Specialization assigns it: the test terms and the concept only |
| [test_concept_C187780.html](test_concept_C187780.html) | MBAB / Microbial-induced Antibody | Immunogenicity (IS) | BC Microbial-induced Antibody Measurement (its NCIt concept, no DECs); no Specialization assigns the test |
| [test_concept_C181394.html](test_concept_C181394.html) | MBIGGAB / Microbial-induced IgG Antibody | Immunogenicity (IS) | BC Microbial-induced IgG Antibody Measurement under Microbial-induced Antibody Measurement, 11 DECs, 63 Specializations, one per organism (ISBDAGNT) |
| [test_concept_C117786.html](test_concept_C117786.html) | QTCFAG / QTcF Interval, Aggregate | ECG (EG) | BC Aggregate QTCF Interval under ECG Measurement, 9 DECs, 1 Specialization (QTCFAG) |
| [test_concept_C38084.html](test_concept_C38084.html) | FEV1 / Forced Expiratory Volume in 1 Second | Respiratory (RE) | BC Forced Expiratory Volume in 1 Second under Pulmonary Function Test, 3 DECs, 1 Specialization (FEV1_RE) |
| [test_concept_C64850.html](test_concept_C64850.html) | HBSAG / Hepatitis B Virus Surface Antigen | Microbiology (MB) | BC Hepatitis B Virus Surface Antigen Measurement under Virus-Based Immunology Test, 6 DECs, 2 Specializations (HBSAGSERPL, HBSAGSERPLPRES) |
| [test_concept_C181331.html](test_concept_C181331.html) | SNV / Single Nucleotide Variation | Genomics (GF) | BC Single Nucleotide Variation Assessment under Genetic Variation Analysis, 20 DECs, 6 Specializations |
| [link_map.html](link_map.html) | (all links) | Standards | The source tables and every link between them as stated in schema/links.yaml, with the Link_Check rows of each link; written by `python examples/link_map.py --out examples/pages/link_map.html` |
