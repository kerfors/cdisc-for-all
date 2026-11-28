"""The test concept graph: run test_concept_graph.rq for one or more SDTM CT test
C-codes, and write per code the result graph (N-Triples) and a page to read it.

    python examples/test_concept.py C105585
    python examples/test_concept.py C105585 C64433 --out examples/output

Reads the published base graphs, links.ttl, by-rule.ttl and cosmos-model.ttl (no sign-in
content). Stops if a code is not an SDTM CT term. The result shows what is there: the test and
its NCIt concept; the COSMoS BC if one has that concept, and the BC of a Dataset Specialization
whose --TESTCD row assigns the test; their DECs if they have any."""
import argparse
import re
import sys
from pathlib import Path

from pyoxigraph import DefaultGraph, Quad, RdfFormat, Store

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from examples.graph_page import write_page  # noqa: E402

QUERY = REPO_ROOT / 'examples' / 'test_concept_graph.rq'
LINKS = REPO_ROOT / 'schema' / 'links.yaml'
GRAPHS = ['linked/links.ttl', 'linked/by-rule.ttl', 'linked/cosmos-model.ttl']
SIGNIN = {'sdtmig', 'sdtm-model'}
VALUES = re.compile(r'VALUES \?code \{ "C\d+" \}')
CT_CODE = 'https://kerfors.github.io/cdisc-for-all/def/sdtm-ct/SDTM%20Terminology#Code'
CT_CODELIST = 'https://kerfors.github.io/cdisc-for-all/def/sdtm-ct/SDTM%20Terminology#Codelist%20Code'


def load_store():
    """The published base graphs, the published link graphs and the COSMoS model graph."""
    store = Store()
    files = [p for p in sorted((REPO_ROOT / 'base').glob('*/*.ttl')) if p.parent.name not in SIGNIN]
    for f in files + [REPO_ROOT / g for g in GRAPHS]:
        store.bulk_load(path=str(f), format=RdfFormat.TURTLE)
    return store


def query_for(code):
    if not re.fullmatch(r'C\d+', code):
        raise ValueError(f'{code!r} is not a C-code')
    text = QUERY.read_text(encoding='utf-8')
    if len(VALUES.findall(text)) != 1:
        raise ValueError(f'{QUERY.name}: expected one line VALUES ?code {{ "C..." }}')
    return VALUES.sub(f'VALUES ?code {{ "{code}" }}', text)


def test_concept(store, code):
    """The result of the query for one C-code, as a new store."""
    if not bool(store.query(f'ASK {{ ?t <{CT_CODE}> "{code}" }}')):
        raise ValueError(f'{code}: no SDTM CT term has this Code')
    if not bool(store.query(f'ASK {{ ?t <{CT_CODE}> "{code}" ; <{CT_CODELIST}> ?cl }}')):
        raise ValueError(f'{code}: this Code is a codelist, not a term')
    result = Store()
    result.extend(Quad(t.subject, t.predicate, t.object) for t in store.query(query_for(code)))
    return result


def write(result, code, out):
    out.mkdir(parents=True, exist_ok=True)
    nt = out / f'test_concept_{code}.nt'
    result.dump(output=str(nt), format=RdfFormat.N_TRIPLES, from_graph=DefaultGraph())
    page = out / f'test_concept_{code}.html'
    data = write_page(result.quads_for_pattern(None, None, None), page, None, LINKS)
    return nt, page, data['title'], data['level']


def main():
    parser = argparse.ArgumentParser(description='The test concept graph: graph and page per SDTM CT test C-code.')
    parser.add_argument('codes', nargs='+', help='C-code of the test term (the Code column of SDTM CT), e.g. C105585')
    parser.add_argument('--out', type=Path, default=REPO_ROOT / 'examples' / 'output', help='output folder (default examples/output)')
    args = parser.parse_args()
    store = load_store()
    for code in args.codes:
        result = test_concept(store, code)
        nt, page, title, _ = write(result, code, args.out)
        print(f'{code}: {title}, {len(result)} triples -> {page}')


if __name__ == '__main__':
    main()
