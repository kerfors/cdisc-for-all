# Test concept pages — examples

Pages written by `examples/test_concept.py` from the published graphs, one per SDTM CT lab test C-code. Each is one self-contained HTML file: open it in a browser, or on GitHub Pages: https://kerfors.github.io/cdisc-for-all/examples/pages/ Every value on a page is a triple of the graphs; the page adds nothing.

Rebuild them (results equal while the graphs are unchanged):

    python examples/test_concept.py C105585 C64853 C64849 C51948 C63321 C64805 C64813 C45997 C100429 --out examples/pages

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
| [link_map.html](link_map.html) | (all links) | Standards | The source tables and every link between them as stated in schema/links.yaml, with the Link_Check rows of each link; written by `python examples/link_map.py --out examples/pages/link_map.html` |
