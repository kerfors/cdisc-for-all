# cdisc-for-all

CDISC and NCIt content as published, fully linked: an RDF base with Excel views — for AI and for humans.

The CDISC standards and the NCI Thesaurus are published as separate files, in different formats, linked by codes and names. This repository reads them as they are, keeps every published value unchanged, and makes the links between them explicit and checkable. Nothing of ours is added: no classification, no interpretation, no counts.

Fully linked wherever the published content resolves; every place it does not is listed in Link_Check. Within the scope below; links to and from the sign-in sources (SDTMIG, SDTM Model) are built locally, not published.

**Status (2026-11-27):** the base graphs of all seven sources are built (SDTMIG and SDTM Model locally only); the linked layer has the published-key links, the links by rule (the general-name ones also as an SSSOM mapping set), the COSMoS model graph and Link_Check. `examples/` shows one use for study design: the test concept graph of a lab test. Changes are logged in [CHANGES.md](CHANGES.md).

## Two layers

- **base** — one reader per source. It writes the source as an RDF graph in the shape the source publishes: one class per table, one property per published column, one node per row, every non-empty cell as a literal with its text unchanged. Its only selection is the scope (below). Each graph comes with an Excel view of the same table, generated from the graph.
- **linked** — reads only the base graphs, plus pinned rule documents (COSMoS's own LinkML model). It makes the links between the sources, restates the COSMoS export in COSMoS's authored model, and reports every reference that does not resolve in Link_Check. Only published content, nothing derived: every value comes from a base graph unchanged, a link rests on a published key or on a stated rule, and a view only reshapes published facts losslessly.

## The rules

1. A value is as its source publishes it: no rewording, no filtering, no choosing. Source column names are kept.
2. Rows are complete: nothing is left out because we judge it irrelevant.
3. A link is a published key. Where a link rests on a naming rule, it is marked "by rule" and the rule is stated. Published-key links and by-rule links are kept in separate named graphs. The links whose rule matches a general name are also given as an SSSOM mapping set, with the part of the rule that matched on each row.
4. Broken links stay broken. They are reported in Link_Check, not repaired. A link to a row that carries a marker its source publishes is kept and reported in Link_Check too: COSMoS marks a retired BC with "[RETIRED]" at the end of its bc_short_name, and every Dataset Specialization row linked to such a BC is listed (the marker is COSMoS's, not ours; the rows and the link stay).
5. Nothing of ours: no position, no classification, no count, no flag.

Content and shape are different things. A view that shows the same published facts in another shape (a pivot, the inverse of a published link) is allowed when it is lossless, adds no value of ours, and states its rule.

## How it is checked

- One LinkML schema describes the base graphs and the links. SHACL shapes are generated from it: structural shapes must pass; link shapes report every reference that does not resolve, and that report is Link_Check.
- Each graph has a content hash: SHA-256 of its canonical N-Triples (RDFC-1.0; the graphs have no blank nodes). Each Excel sheet has a text hash of the sheet read back as text.
- A base graph is lossless when its Excel view, sorted by key, has the same text hash as the source table read as text.
- Each base graph is cross-checked against rdf-tabular, the reference CSVW implementation, converting the published files: the same graph. A release check that reads the source files again and compares is planned, not built.

## Sources

Every pin is in [`Reference_Versions.json`](Reference_Versions.json): version, file, and SHA-256. A reader stops if a source file differs from its pin.

| Source | Publisher | Access |
|---|---|---|
| COSMoS Biomedical Concepts and SDTM Dataset Specializations (latest export, Package 19) | CDISC | public (github.com/cdisc-org/COSMoS, `export/`) |
| SDTM Controlled Terminology 2026-09-25 | CDISC, via NCI EVS | public |
| NCI Thesaurus, FLAT file, release 26.09d (built 2026-09-29) | NCI EVS | public |
| NCIt code to CUI map (no release; pinned by date and SHA-256) | NCI EVS | public |
| Approved Non-Standard Variable Registry 2026-04-03 | CDISC | public |
| SDTMIG v3.4 variable table | CDISC | cdisc.org sign-in |
| SDTM v2.0 variable table | CDISC | cdisc.org sign-in |

**Scope.** SDTM CT and NCIt are not carried in full: SDTM CT is carried for the codelists COSMoS refers to or SDTMIG v3.4 binds, with all their terms; NCIt for the concepts of those codelists and terms, the COSMoS concepts and the SDTM Model variable concepts, with all their ancestors. COSMoS is carried as its latest export only (the `_latest` files of `export/`), not the archived packages.

## Identifiers

IRIs are in the namespace `https://kerfors.github.io/cdisc-for-all/` and are made by rule from the published table, column and key (percent-encoded). They are identifiers for this repository's own use: not dereferenceable (the namespace is also the GitHub Pages address of this repository, which serves the files of main as they are; no IRI under def/, id/, link/ or rule/ is a file there), and stable only within a pin. NCIt concepts keep NCI's own IRIs. This is not a general RDF representation of the CDISC standards.

## Using it: the test concept graph

`examples/test_concept.py` takes the C-code of an SDTM CT test term and writes the test concept graph (a SPARQL CONSTRUCT over the graphs, `examples/test_concept_graph.rq`) and a page to read it: the test terms and their NCIt concept; the COSMoS BC if one has that concept; its Data Element Concepts, the CT terms Dataset Specializations bind to them, and the Specializations, if it has any. Every triple is a triple of the graphs.

    python3 -m venv ~/venvs/cdisc-for-all
    ~/venvs/cdisc-for-all/bin/pip install -r requirements.txt
    ~/venvs/cdisc-for-all/bin/python examples/test_concept.py C105585 C64853

Start page, for study designers: [https://kerfors.github.io/cdisc-for-all/](https://kerfors.github.io/cdisc-for-all/) (`index.html`). Pages for nine lab tests, to open in a browser: [https://kerfors.github.io/cdisc-for-all/examples/pages/](https://kerfors.github.io/cdisc-for-all/examples/pages/) (source in [`examples/pages/`](examples/pages/README.md)). `examples/Example_Lab_Test_Graphs.ipynb` does the same in a notebook.

The link map, for standards specialists: every link between the source tables as stated in `schema/links.yaml` (key columns, rule) with its Link_Check rows, [https://kerfors.github.io/cdisc-for-all/examples/pages/link_map.html](https://kerfors.github.io/cdisc-for-all/examples/pages/link_map.html), written by `python examples/link_map.py --out examples/pages/link_map.html`.

For AI agents and other machines: [`llms.txt`](llms.txt) (what is here, the rules to keep, every file and link) and [`catalog.ttl`](catalog.ttl) (DCAT + VoID: every graph and file with licence, version, triple count and SHA-256, and one linkset per link), both written by `linked/Make_Catalog.ipynb`.

## Layout

```
schema/          the LinkML schema (one module per source, links, the COSMoS model mapping) and the generated SHACL
cfa/             the shared helper: reading, writing, IRIs, hashes, Schema sheets, Provenance
base/<source>/   reader notebook, downloads/ (not in git), the graph (.ttl), its Excel view, Provenance
linked/          Make_Links, Make_COSMoS_Model and Make_Catalog notebooks, the link graphs, the SSSOM mapping set of the general-name links, the COSMoS model graph, Link_Check (-signin files local, not in git)
llms.txt, catalog.ttl   the entry point for AI agents and the DCAT + VoID catalogue (written by Make_Catalog)
checks/          the schema check and the CSVW cross-check (rdf-tabular)
examples/        a SPARQL CONSTRUCT query over the graphs (the test concept graph), test_concept.py to run it per test C-code, an example notebook, example pages for nine lab tests (pages/)
```

## Content and licences

The code, the schema and the documentation written for this repository are under the MIT licence ([LICENSE](LICENSE)). The content generated from the sources stays under the terms of its publishers:

- NCI Thesaurus: Creative Commons Attribution 4.0 International (CC BY 4.0), [NCI Thesaurus Terms of Use](https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/ThesaurusTermsofUse.htm). The NCIt content here is derived from the NCI Thesaurus, produced by NCI Enterprise Vocabulary Services; "NCI Thesaurus" is a trademark of the National Cancer Institute.
- COSMoS: MIT licence, Copyright CDISC ([cdisc-org/COSMoS](https://github.com/cdisc-org/COSMoS)).
- SDTM Controlled Terminology and the Non-Standard Variable Registry: the terms of CDISC and NCI EVS.
- SDTMIG and SDTM Model variable tables: downloaded with a cdisc.org sign-in. The files, their graphs and views, and the links to and from their rows (the `-signin` files of `linked/`) are not in this repository; each user downloads the files and builds these locally.
