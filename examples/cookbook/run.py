"""Run the cookbook recipes and the review queries over the published graphs, and compare
each result with its CSV in results/.

The graphs are the Turtle files that catalog.ttl lists, read from this clone; each file must
have the SHA-256 that catalog.ttl gives, so a result belongs to the catalogued files. One named
graph per dataset, queried as their union (as the MCP server does). No sign-in content.

Run from the repository root:
    python examples/cookbook/run.py            compare; stops at the first result that differs
    python examples/cookbook/run.py --write    write results/ (after a rebuild of a published graph)
"""
import csv
import hashlib
import io
import sys
from pathlib import Path

from pyoxigraph import NamedNode, QueryResultsFormat, RdfFormat, Store

ROOT = Path(__file__).resolve().parents[2]
COOKBOOK = ROOT / 'examples' / 'cookbook'
RESULTS = COOKBOOK / 'results'
SITE = 'https://kerfors.github.io/cdisc-for-all/'

CATALOG_QUERY = '''
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX spdx: <http://spdx.org/rdf/terms#>
SELECT ?dataset ?url ?sha256 WHERE {
    ?dataset a void:Dataset ; dcat:distribution ?d .
    ?d dcat:mediaType <https://www.iana.org/assignments/media-types/text/turtle> ;
       dcat:downloadURL ?url ;
       spdx:checksum/spdx:checksumValue ?sha256 .
} ORDER BY ?dataset'''


def load():
    catalog = Store()
    catalog.load(path=str(ROOT / 'catalog.ttl'), format=RdfFormat.TURTLE, base_iri=SITE)
    store = Store()
    for row in catalog.query(CATALOG_QUERY):
        url, sha = row['url'].value, row['sha256'].value
        path = ROOT / url[len(SITE):]
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            sys.exit(f'{path.relative_to(ROOT)}: SHA-256 is not the one catalog.ttl lists')
        store.bulk_load(path=str(path), format=RdfFormat.TURTLE, to_graph=NamedNode(row['dataset'].value))
        print(f'loaded {path.relative_to(ROOT)}')
    return store


def main():
    write = sys.argv[1:] == ['--write']
    if sys.argv[1:] and not write:
        sys.exit(__doc__)
    queries = sorted(COOKBOOK.glob('*.rq')) + sorted((ROOT / 'examples').glob('review_*.rq'))
    store = load()
    for q in queries:
        result = store.query(q.read_text(encoding='utf-8'), use_default_graph_as_union=True)
        text = result.serialize(format=QueryResultsFormat.CSV)
        expected = RESULTS / (q.stem + '.csv')
        rows = len(list(csv.reader(io.StringIO(text.decode('utf-8'))))) - 1
        if write:
            expected.write_bytes(text)
            print(f'wrote {expected.relative_to(ROOT)} ({rows} rows)')
        elif expected.read_bytes() != text:
            sys.exit(f'{q.relative_to(ROOT)}: result differs from {expected.relative_to(ROOT)}')
        else:
            print(f'same  {q.relative_to(ROOT)} ({rows} rows)')


if __name__ == '__main__':
    main()
