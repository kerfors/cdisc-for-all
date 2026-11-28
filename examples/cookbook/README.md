# SPARQL cookbook

Short SPARQL SELECT queries over the published graphs, one plain question each, for the upstream view: what is defined about a test, and why, before any data is captured. Each recipe is one `.rq` file that runs on its own, names the links it follows, and has its result for the current pins in [`results/`](results/), as run. A result is the answer to a query over the published content, not published content itself.

The graphs: the base graphs (`base/<source>/<source>.ttl`), the link graphs (`linked/links.ttl`, `linked/by-rule.ttl`), the COSMoS model graph (`linked/cosmos-model.ttl`) and the vocabulary (`schema/vocabulary.ttl`), queried as one union. These are the Turtle files that [`catalog.ttl`](../../catalog.ttl) lists. No sign-in content (SDTMIG, SDTM Model, SDTMIG Appendix D) is used.

## Recipes

Each recipe has one parameter set in its `VALUES` line, with the example given here.

| | Question | Example | Links followed |
|---|---|---|---|
| [01](01_find_test.rq) | Find a test by code or name | "glucose" | none |
| [02](02_bc_for_test.rq) | Is there a Biomedical Concept for this test? | C105585 | sdtm-ct to NCIt; cosmos biomedical concept to NCIt |
| [03](03_bc_hierarchy.rq) | Where does the BC sit in the hierarchy? | C63321 | cosmos hierarchy to parent |
| [04](04_bc_data_element_concepts.rq) | What does the BC define (its Data Element Concepts)? | C105585 | (COSMoS BC model) |
| [05](05_dataset_specializations_of_bc.rq) | How is the BC specialised for SDTM (its Dataset Specializations)? | C105585 | (COSMoS SDTM model) |
| [06](06_specialization_variables.rq) | What does a Dataset Specialization specify? | GLUCSERPL | none |
| [07](07_permitted_values.rq) | What values are permitted for a variable? | GLUCSERPL, LBORRESU | cosmos value list to term (by rule) |
| [08](08_specialization_relationships.rq) | Which relationships does a Dataset Specialization state? | GLUCSERPL | cosmos object to variable (by rule) |
| [09](09_non_standard_variables.rq) | Which non-standard variables do the Dataset Specializations use? | none | cosmos variable to NSV Registry (by rule) |
| [10](10_codelist_terms.rq) | What are the terms of a codelist? | C78734 | sdtm-ct term to codelist |
| [11](11_codelists_of_concept.rq) | Which codelists hold this concept? | C25613 | none |
| [12](12_ncit_concept.rq) | What does NCIt say about a concept? | C105585 | ncit concept to parent; code-CUI map to NCIt |

The review queries, for standards specialists, are in `examples/` and run with the recipes: [`review_testcd_vs_bc.rq`](../review_testcd_vs_bc.rq) (Dataset Specializations whose test code has another NCIt concept than their BC) and [`review_unit_same_bc_specimen.rq`](../review_unit_same_bc_specimen.rq) (same BC and specimen, different standard units). Their results are in `results/` too.

The links are described in [`schema/links.yaml`](../../schema/links.yaml) and drawn in the [link map](https://kerfors.github.io/cdisc-for-all/examples/pages/link_map.html).

## Patterns

**Prefixes.** Every recipe opens with the same block:

```sparql
PREFIX ct:    <https://kerfors.github.io/cdisc-for-all/def/sdtm-ct/SDTM%20Terminology#>
PREFIX ctl:   <https://kerfors.github.io/cdisc-for-all/link/sdtm-ct/SDTM%20Terminology#>
PREFIX nci:   <https://kerfors.github.io/cdisc-for-all/def/ncit-flat/Thesaurus#>
PREFIX ncil:  <https://kerfors.github.io/cdisc-for-all/link/ncit-flat/Thesaurus#>
PREFIX bc:    <https://kerfors.github.io/cdisc-for-all/def/cosmos/cdisc_biomedical_concepts_latest#>
PREFIX bcl:   <https://kerfors.github.io/cdisc-for-all/link/cosmos/cdisc_biomedical_concepts_latest#>
PREFIX bch:   <https://kerfors.github.io/cdisc-for-all/def/cosmos/cdisc_biomedical_concepts_hierarchy_latest#>
PREFIX bchl:  <https://kerfors.github.io/cdisc-for-all/link/cosmos/cdisc_biomedical_concepts_hierarchy_latest#>
PREFIX ds:    <https://kerfors.github.io/cdisc-for-all/def/cosmos/cdisc_sdtm_dataset_specializations_latest#>
PREFIX dsl:   <https://kerfors.github.io/cdisc-for-all/link/cosmos/cdisc_sdtm_dataset_specializations_latest#>
PREFIX dsr:   <https://kerfors.github.io/cdisc-for-all/rule/cosmos/cdisc_sdtm_dataset_specializations_latest#>
PREFIX cui:   <https://kerfors.github.io/cdisc-for-all/def/nci-code-cui-map/nci_code_cui_map#>
PREFIX cuil:  <https://kerfors.github.io/cdisc-for-all/link/nci-code-cui-map/nci_code_cui_map#>
PREFIX nsv:   <https://kerfors.github.io/cdisc-for-all/def/nsv-registry/Approved%20NSVs-alpha#>
PREFIX cbc:   <https://www.cdisc.org/cosmos/biomedical_concept_v1.0>
PREFIX csdtm: <https://www.cdisc.org/cosmos/sdtm_v1.0/>
```

`def/` holds the published columns, `link/` the links on published keys, `rule/` the links by rule. `cbc:` and `csdtm:` are COSMoS's own model IRIs (the BC prefix runs into the local name, as COSMoS publishes it).

**Percent-encoded column names.** A column name with spaces or brackets is percent-encoded in its IRI, and SPARQL allows `%hh` in a prefixed name: `ct:CDISC%20Submission%20Value`, `ct:Codelist%20Extensible%20%28Yes%2FNo%29`.

**A "/" in the local name.** The by-rule links name the target table after a "/": escape it with a backslash, `dsr:value_list\/sdtm-ct\/SDTM%20Terminology` (recipe 07), or write the full IRI in `<...>`.

**Row IRIs.** A row's IRI is made by rule from the table and its key (README, Identifiers). To start from a row, build its IRI with `BIND(IRI(CONCAT(...)))` (recipe 10: a codelist row, whose empty Codelist Code gives an empty segment, `...SDTM%20Terminology//C78734`), or find it by a column value (most recipes).

**Parameters.** One `VALUES` line per recipe; a pair of parameters is `VALUES (?a ?b) { ("x" "y") }` (recipe 07).

**Values as published.** A multi-value cell is one literal (`value_list` "mg/dL;g/L;mmol/L"); the COSMoS model graph has one triple per part (`csdtm:valueList`). Empty cells have no triple, so optional columns are in `OPTIONAL`.

## Running the recipes

- In the MCP server ([`mcp/`](../../mcp/)): paste a recipe into the `sparql` tool.
- In any SPARQL store: load the Turtle files above into one store and query their union.
- All at once, from a clone, with pyoxigraph (`requirements.txt`): `python examples/cookbook/run.py` runs every recipe and review query over the files `catalog.ttl` lists (each SHA-256 checked) and stops at the first result that differs from its CSV in `results/`. After a rebuild that changes a published graph, `python examples/cookbook/run.py --write` writes the new results.
