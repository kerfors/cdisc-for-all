# cdisc-for-all

CDISC and NCIt content as published, fully linked: an RDF base with Excel views — for AI and for humans.

The CDISC standards and the NCI Thesaurus are published as separate files, in different formats, linked by codes and names. This repository reads them as they are, keeps every published value unchanged, and makes the links between them explicit and checkable. Nothing of ours is added: no classification, no interpretation, no counts.

**Status:** started 2026-11-26. Nothing is built yet; this commit sets the scope, the pins and the rules.

## Two layers

- **base** — one reader per source. It writes the source as an RDF graph in the shape the source publishes: one class per table, one property per published column, one node per row, every non-empty cell as a literal with its text unchanged. Its only selection is the scope (below). Each graph comes with an Excel view of the same table, generated from the graph.
- **linked** — reads only the base graphs, plus pinned rule documents (COSMoS's own LinkML model). It makes the links between the sources, restates the COSMoS export in COSMoS's authored model, and reports every reference that does not resolve in Link_Check. Only published content, nothing derived: every value comes from a base graph unchanged, a link rests on a published key or on a stated rule, and a view only reshapes published facts losslessly.

## The rules

1. A value is as its source publishes it: no rewording, no filtering, no choosing. Source column names are kept.
2. Rows are complete: nothing is left out because we judge it irrelevant.
3. A link is a published key. Where a link rests on a naming rule, it is marked "by rule" and the rule is stated. Published-key links and by-rule links are kept in separate named graphs.
4. Broken links stay broken. They are reported in Link_Check, not repaired.
5. Nothing of ours: no position, no classification, no count, no flag.

Content and shape are different things. A view that shows the same published facts in another shape (a pivot, the inverse of a published link) is allowed when it is lossless, adds no value of ours, and states its rule.

## How it is checked

- One LinkML schema describes the base graphs and the links. SHACL shapes are generated from it: structural shapes must pass; link shapes report every reference that does not resolve, and that report is Link_Check.
- Each graph has a content hash: SHA-256 of its canonical N-Triples (RDFC-1.0; the graphs have no blank nodes). Each Excel sheet has a text hash of the sheet read back as text.
- A base graph is lossless when its Excel view, sorted by key, has the same text hash as the source table read as text.
- The release check reads the source files again and compares.

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

IRIs are in the namespace `https://kerfors.github.io/cdisc-for-all/` and are made by rule from the published table, column and key (percent-encoded). They are identifiers for this repository's own use: not dereferenceable, and stable only within a pin. NCIt concepts keep NCI's own IRIs. This is not a general RDF representation of the CDISC standards.

## Layout

```
schema/          the LinkML schema (one module per source, links, the COSMoS model mapping) and the generated SHACL
cfa/             the shared helper: reading, writing, IRIs, hashes, Schema sheets, Provenance
base/<source>/   reader notebook, downloads/ (not in git), the graph (.ttl), its Excel view, Provenance
linked/          the link graphs, the COSMoS model graph, Link_Check
checks/          the schema check and the release check
examples/        SPARQL CONSTRUCT queries over the graphs, with an example notebook (results not in git)
```

## Content and licences

The code, the schema and the documentation written for this repository are under the MIT licence ([LICENSE](LICENSE)). The content generated from the sources stays under the terms of its publishers:

- NCI Thesaurus: Creative Commons Attribution 4.0 International (CC BY 4.0), [NCI Thesaurus Terms of Use](https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/ThesaurusTermsofUse.htm). The NCIt content here is derived from the NCI Thesaurus, produced by NCI Enterprise Vocabulary Services; "NCI Thesaurus" is a trademark of the National Cancer Institute.
- COSMoS: MIT licence, Copyright CDISC ([cdisc-org/COSMoS](https://github.com/cdisc-org/COSMoS)).
- SDTM Controlled Terminology and the Non-Standard Variable Registry: the terms of CDISC and NCI EVS.
- SDTMIG and SDTM Model variable tables: downloaded with a cdisc.org sign-in. The files, and the graphs and views that would reproduce them whole, are not in this repository; each user downloads them. What the linked files take from them is published.
