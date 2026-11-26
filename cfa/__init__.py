"""cfa: the shared helper of cdisc-for-all.

- pins:       the source files and their pins (Reference_Versions.json); stop if a file differs
- read:       source and view tables as text (xlsx with _xHHHH_ decoded, CSV RFC 4180, TSV without quoting)
- rule:       IRIs, the CSVW table description generated from the LinkML schema, and the
              CSVW minimal-mode conversion of a table to its base graph
- graph:      the longturtle writer, canonical N-Triples and the graph hash
- view:       the Excel view (every cell text), the text hash, the Schema sheet
- provenance: Provenance.json of a base graph
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / 'schema'
NS = 'https://kerfors.github.io/cdisc-for-all/'
