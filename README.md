# cdisc-for-all

CDISC and NCIt content as published, fully linked: an RDF base with Excel views — for AI and for humans.

The CDISC standards and the NCI Thesaurus are published as separate files, in different formats, linked by codes and names. This repository reads them as they are, keeps every published value unchanged, and makes the links between them explicit and checkable. Nothing of ours is added: no classification, no interpretation, no counts.

Fully linked wherever the published content resolves; every place it does not is listed in Link_Check. Within the scope below; links to and from the sign-in sources (SDTMIG, SDTMIG Appendix D, SDTM Model) are built locally, not published.

**Status (2026-11-27):** the base graphs of all eight sources are built (SDTMIG, SDTMIG Appendix D and SDTM Model locally only); the linked layer has the published-key links, the links by rule (the general-name ones also as an SSSOM mapping set), the COSMoS model graph and Link_Check. `examples/` shows one use for study design: the test concept graph of a lab test. Changes are logged in [CHANGES.md](CHANGES.md).

## Where to start

| You are | Start here | What you get |
|---|---|---|
| Study designer, clinical scientist | [Start page](https://kerfors.github.io/cdisc-for-all/) | One page per lab test: the test, its NCIt concept, the COSMoS BC, its DECs, the Specializations and the CT terms they bind |
| Standards or metadata specialist | [Link map](https://kerfors.github.io/cdisc-for-all/examples/pages/link_map.html) | Every link between the source tables as stated, with its Link_Check rows |
| Developer | [`examples/Getting_Started.ipynb`](examples/Getting_Started.ipynb) | The published graphs in Oxigraph, no clone, and Glucose one hop at a time |
| AI assistant (MCP) | [`mcp/cdisc_for_all_mcp.py`](mcp/cdisc_for_all_mcp.py) | The published graphs behind four tools: find a test, its test concept graph, describe an IRI, read-only SPARQL |
| AI agent | [`llms.txt`](llms.txt), [`catalog.ttl`](catalog.ttl), [`schema/vocabulary.ttl`](schema/vocabulary.ttl) | What is here and the rules to keep; DCAT + VoID with every file, licence, checksum and linkset; what each class and property means |
| Anyone rebuilding | [Layout](#layout) and the notebooks in `base/` and `linked/` | The build, source by source |

Details of each are under [Using it](#using-it-the-test-concept-graph).

## Two layers

- **base** — one reader per source. It writes the source as an RDF graph in the shape the source publishes: one class per table, one property per published column, one node per row, every non-empty cell as a literal with its text unchanged. Its only selection is the scope (below). Each graph comes with an Excel view of the same table, generated from the graph.
- **linked** — reads only the base graphs, plus pinned rule documents (COSMoS's own LinkML model). It makes the links between the sources, restates the COSMoS export in COSMoS's authored model, and reports every reference that does not resolve in Link_Check. Only published content, nothing derived: every value comes from a base graph unchanged, a link rests on a published key or on a stated rule, and a view only reshapes published facts losslessly.

Beside the two layers, and generated from them or from the schema: the vocabulary of every class and property (`schema/vocabulary.ttl`), the catalogue of every graph and file (`catalog.ttl`, with `llms.txt` as its guide), and the ways to use the graphs (`examples/`: the test concept graph, review queries, notebooks and pages; `mcp/`: a server for AI assistants). There are no files made for one consumer, such as an Excel file per observation class: a consumer queries the graphs, or reads the Excel view of a base graph.

## The rules

1. A value is as its source publishes it: no rewording, no filtering, no choosing. Source column names are kept.
2. Rows are complete: nothing is left out because we judge it irrelevant.
3. A link is a published key. Where a link rests on a naming rule, it is marked "by rule" and the rule is stated. Published-key links and by-rule links are kept in separate named graphs. The links whose rule matches a general name are also given as an SSSOM mapping set, with the part of the rule that matched on each row.
4. Broken links stay broken. They are reported in Link_Check, not repaired. A link to a row that carries a marker its source publishes is kept and reported in Link_Check too: COSMoS marks a retired BC with "[RETIRED]" at the end of its bc_short_name, and every Dataset Specialization row linked to such a BC is listed (the marker is COSMoS's, not ours; the rows and the link stay).
5. Nothing of ours: no position, no classification, no count, no flag.

Content and shape are different things. A view that shows the same published facts in another shape (the inverse of a published link) is allowed when it is lossless, adds no value of ours, and states its rule.

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
| SDTMIG v3.4 Appendix D, CDISC Variable-naming Fragments (the table in the SDTMIG v3.4 PDF) | CDISC | cdisc.org sign-in |
| SDTM v2.0 variable table | CDISC | cdisc.org sign-in |

**Scope.** SDTM CT and NCIt are not carried in full: SDTM CT is carried for the codelists COSMoS refers to or SDTMIG v3.4 binds, with all their terms; NCIt for the concepts of those codelists and terms, the COSMoS concepts and the SDTM Model variable concepts, with all their ancestors. COSMoS is carried as its latest export only (the `_latest` files of `export/`), not the archived packages.

**What depends on the sign-in sources.** Three published files are shaped by the SDTMIG or SDTM Model graphs: the scope of `sdtm-ct.ttl` (it includes the codelists SDTMIG v3.4 binds); the links by rule to the NSV Registry in `by-rule.ttl` (made only where a row has no SDTMIG or SDTM Model link); and, through those links, which rows `Link_Check.xlsx` lists for them. Without a cdisc.org sign-in these files cannot be rebuilt exactly; the published files are as built, with their inputs and hashes in Provenance.

## Identifiers

IRIs are in the namespace `https://kerfors.github.io/cdisc-for-all/` and are made by rule from the published table, column and key (percent-encoded). They are identifiers for this repository's own use: not dereferenceable (the namespace is also the GitHub Pages address of this repository, which serves the files of main as they are; no IRI under def/, id/, link/ or rule/ is a file there), and stable only within a pin. NCIt concepts keep NCI's own IRIs. This is not a general RDF representation of the CDISC standards.

## Using it: the test concept graph

`examples/test_concept.py` takes the C-code of an SDTM CT test term and writes the test concept graph (a SPARQL CONSTRUCT over the graphs, `examples/test_concept_graph.rq`) and a page to read it: the test terms and their NCIt concept; the COSMoS BC if one has that concept; its Data Element Concepts, the CT terms Dataset Specializations bind to them, and the Specializations, if it has any. Every triple is a triple of the graphs.

    python3 -m venv ~/venvs/cdisc-for-all
    ~/venvs/cdisc-for-all/bin/pip install -r requirements.txt
    ~/venvs/cdisc-for-all/bin/python examples/test_concept.py C105585 C64853

`test_concept.py` needs the full `requirements.txt` (it writes the page with the link specs, which use linkml); the getting-started notebook below needs only pyoxigraph and pandas.

Start page, for study designers: [https://kerfors.github.io/cdisc-for-all/](https://kerfors.github.io/cdisc-for-all/) (`index.html`). Pages for nine lab tests, to open in a browser: [https://kerfors.github.io/cdisc-for-all/examples/pages/](https://kerfors.github.io/cdisc-for-all/examples/pages/) (source in [`examples/pages/`](examples/pages/README.md)). `examples/Example_Lab_Test_Graphs.ipynb` does the same in a notebook.

The link map, for standards specialists: every link between the source tables as stated in `schema/links.yaml` (key columns, rule) with its Link_Check rows, [https://kerfors.github.io/cdisc-for-all/examples/pages/link_map.html](https://kerfors.github.io/cdisc-for-all/examples/pages/link_map.html), written by `python examples/link_map.py --out examples/pages/link_map.html`.

Review queries, for standards specialists: SPARQL SELECTs that ask a question of the published content across sources, over the same graphs as the test concept graph. Their answers are not published content: a row is a place to look, not a finding of this repository. [`examples/review_testcd_vs_bc.rq`](examples/review_testcd_vs_bc.rq): the Dataset Specializations whose test code has another NCIt concept than their BC, and how NCIt relates the two. [`examples/review_unit_same_bc_specimen.rq`](examples/review_unit_same_bc_specimen.rq): pairs of Dataset Specializations with the same BC and the same specimen whose standard units differ. Each names the links it follows and the result for the current pins.

For AI agents and other machines: [`llms.txt`](llms.txt) (what is here, the rules to keep, every file and link) and [`catalog.ttl`](catalog.ttl) (DCAT + VoID: every graph and file with licence, version, triple count and SHA-256, and one linkset per link), both written by `linked/Make_Catalog.ipynb`. What each class and property means: [`schema/vocabulary.ttl`](schema/vocabulary.ttl), plain RDFS restated from the LinkML schema: every table as a class, every column as a property labelled with its published column name, every link with its tables, description and rule. Written by `checks/00_Schema.ipynb`; Make_Catalog checks that every class and predicate of the graphs is declared in it.

For developers: [`examples/Getting_Started.ipynb`](examples/Getting_Started.ipynb) needs no clone and no build. It reads `catalog.ttl` from the Pages site, downloads the graphs it lists (checked against their SHA-256), loads them into Oxigraph, one named graph each, and follows Glucose one hop at a time, from the SDTM CT term to its NCIt concept, the COSMoS BC and its DECs, the Dataset Specializations and the CT terms they bind, naming the link each hop follows.

For AI assistants: [`mcp/cdisc_for_all_mcp.py`](mcp/cdisc_for_all_mcp.py) is a local MCP server (stdio). Like the getting-started notebook it reads `catalog.ttl` from the Pages site, downloads the published graphs once to `~/cdisc-for-all-data/` (SHA-256 checked) and loads them into Oxigraph; only published content, no sign-in source. Tools: `find_test` (text to SDTM CT term C-codes), `test_concept` (the test concept graph of a C-code), `describe` (every triple of one IRI, in and out), `sparql` (read-only). Resources: `llms.txt`, `catalog.ttl`, `schema/vocabulary.ttl`, `schema/links.yaml`. In Claude Desktop, with [uv](https://docs.astral.sh/uv/) installed, add it under `mcpServers` in the configuration file (on a Mac `~/Library/Application Support/Claude/claude_desktop_config.json`) and restart Claude Desktop. Claude Desktop does not see the Terminal's PATH, so give uv's full path, as `which uv` shows it (with Homebrew on a Mac: `/opt/homebrew/bin/uv`):

    {"mcpServers": {"cdisc-for-all": {"command": "/opt/homebrew/bin/uv", "args": ["run", "https://kerfors.github.io/cdisc-for-all/mcp/cdisc_for_all_mcp.py"]}}}

Without uv, in a venv with `pip install mcp==2.3.0 pyoxigraph==0.5.13`, the command is the venv's `python` and the argument the path of the downloaded script. The first tool call downloads and loads the graphs (about 115 MB, once).

## Layout

```
schema/          the LinkML schema (one module per source, links, the COSMoS model mapping), the generated SHACL and CSVW, and the vocabulary graph (vocabulary.ttl)
cfa/             the shared helper: reading, writing, IRIs, hashes, Schema sheets, Provenance
base/<source>/   reader notebook, downloads/ (not in git), the graph (.ttl), its Excel view, Provenance
linked/          Make_Links, Make_COSMoS_Model and Make_Catalog notebooks, the link graphs, the SSSOM mapping set of the general-name links, the COSMoS model graph, Link_Check (-signin files local, not in git)
llms.txt, catalog.ttl   the entry point for AI agents and the DCAT + VoID catalogue (written by Make_Catalog)
checks/          the schema check and the CSVW cross-check (rdf-tabular)
mcp/             the MCP server for AI assistants (one script)
examples/        a SPARQL CONSTRUCT query over the graphs (the test concept graph), test_concept.py to run it per test C-code, two review queries (SPARQL SELECT), an example notebook, a getting-started notebook for developers (published graphs, no clone), example pages for nine lab tests (pages/)
```

## Planned

Not built yet, in no fixed order:

- **SPARQL cookbook**: the two review queries in `examples/` are a first piece. Short, tested queries for common questions, each naming the links it follows; it opens with a prefix block and patterns for the percent-encoded IRIs (`VALUES`, `BIND(IRI(...))`), which cannot all be written as prefixed names.
- **Dereferenceable IRIs**: today `def/`, `id/`, `link/` and `rule/` are identifiers only. Options: w3id redirects to generated pages, or the vocabulary graph served at `def/`.
- **Test concept graph**: also follow child BCs and the test rows of the Specializations (for example WEIGHT, assigned under the child BC Body Weight).
- **SSSOM** for the other links by rule.
- **Release check**: read the source files again and compare (see [How it is checked](#how-it-is-checked)).

Questions and comments: [GitHub issues](https://github.com/kerfors/cdisc-for-all/issues).

## Content and licences

The code, the schema and the documentation written for this repository are under the MIT licence ([LICENSE](LICENSE)). The content generated from the sources stays under the terms of its publishers:

- NCI Thesaurus: Creative Commons Attribution 4.0 International (CC BY 4.0), [NCI Thesaurus Terms of Use](https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/ThesaurusTermsofUse.htm). The NCIt content here is derived from the NCI Thesaurus, produced by NCI Enterprise Vocabulary Services; "NCI Thesaurus" is a trademark of the National Cancer Institute.
- COSMoS: MIT licence, Copyright CDISC ([cdisc-org/COSMoS](https://github.com/cdisc-org/COSMoS)).
- SDTM Controlled Terminology and the Non-Standard Variable Registry: the terms of CDISC and NCI EVS.
- SDTMIG and SDTM Model variable tables, and SDTMIG Appendix D: downloaded with a cdisc.org sign-in. The files, their graphs and views, the links to and from their rows and the Link_Check rows of those links (the `-signin` files of `linked/`) are not in this repository; each user downloads the files and builds these locally.
