# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp==2.3.0", "pyoxigraph==0.5.13"]
# ///
"""cdisc-for-all as an MCP server (stdio), for an AI assistant.

Reads catalog.ttl from the GitHub Pages site, downloads the published graphs it lists (the vocabulary
included) to
~/cdisc-for-all-data/ (again only when a SHA-256 differs; a file whose SHA-256 is not the
catalogue's stops the server) and loads them into Oxigraph, one named graph per dataset. Only
published content: the sign-in sources (SDTMIG, SDTM Model) and their links are not in it.

Tools: find_test, test_concept, describe, sparql. Resources: llms.txt, catalog.ttl,
schema/vocabulary.ttl, schema/links.yaml. Every answer is triples or cells of the graphs,
as published; nothing is added.

Run:  uv run https://kerfors.github.io/cdisc-for-all/mcp/cdisc_for_all_mcp.py
or, in a venv with mcp==2.3.0 and pyoxigraph==0.5.13:  python cdisc_for_all_mcp.py
"""
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pyoxigraph import NamedNode, QueryBoolean, QuerySolutions, RdfFormat, Store

SITE = 'https://kerfors.github.io/cdisc-for-all/'
DATA = Path.home() / 'cdisc-for-all-data'
CT = 'https://kerfors.github.io/cdisc-for-all/def/sdtm-ct/SDTM%20Terminology#'
MAX_ROWS = 500

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


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


_store = None


def store():
    """The published graphs in one store, loaded on first use."""
    global _store
    if _store is not None:
        return _store
    DATA.mkdir(exist_ok=True)
    catalog = Store()
    catalog.load(fetch(SITE + 'catalog.ttl'), format=RdfFormat.TURTLE, base_iri=SITE)
    s = Store()
    for row in catalog.query(CATALOG_QUERY):
        url, sha = row['url'].value, row['sha256'].value
        path = DATA / url[len(SITE):].replace('/', '__')
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            path.write_bytes(fetch(url))
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ToolError(f'{url}: SHA-256 is not the one catalog.ttl lists')
        s.bulk_load(path=str(path), format=RdfFormat.TURTLE, to_graph=NamedNode(row['dataset'].value))
        print(f'loaded {url[len(SITE):]}', file=sys.stderr)
    _store = s
    return s


def query(text):
    return store().query(text, use_default_graph_as_union=True)


def table(result):
    """A SELECT result as tab-separated text: header, then one row per solution (at most MAX_ROWS)."""
    names = [v.value for v in result.variables]
    lines = ['\t'.join(names)]
    for i, sol in enumerate(result):
        if i == MAX_ROWS:
            lines.append(f'(stopped at {MAX_ROWS} rows)')
            break
        lines.append('\t'.join('' if sol[n] is None else sol[n].value for n in names))
    return '\n'.join(lines)


def ntriples(triples):
    out = [f'{t.subject} {t.predicate} {t.object} .' for t in triples]
    return '\n'.join(sorted(out))


server = MCPServer(
    name='cdisc-for-all',
    instructions=('CDISC and NCIt content as published, linked (https://kerfors.github.io/cdisc-for-all/). '
                  'Every value is a cell as its source publishes it; links rest on a published key or a stated rule; '
                  'what does not resolve is reported in Link_Check, not repaired. Do not present an inference as published content. '
                  'Read the resource llms.txt first. The first tool call downloads and loads the graphs (about 115 MB, once).'),
)


@server.tool()
def find_test(text: str) -> str:
    """SDTM CT term rows whose CDISC Submission Value, CDISC Synonym(s) or NCI Preferred Term contains
    the text (case-insensitive), with their Code and codelist. Test terms are in codelists such as
    Laboratory Test Code / Laboratory Test Name. Use a Code with test_concept."""
    needle = text.replace('\\', '\\\\').replace('"', '\\"')
    return table(query(f'''
SELECT ?code ?codelist_name ?submission_value ?nci_preferred_term ?row WHERE {{
    ?row <{CT}Code> ?code ; <{CT}Codelist%20Code> ?cl ; <{CT}Codelist%20Name> ?codelist_name ;
         <{CT}CDISC%20Submission%20Value> ?submission_value .
    OPTIONAL {{ ?row <{CT}NCI%20Preferred%20Term> ?nci_preferred_term }}
    OPTIONAL {{ ?row <{CT}CDISC%20Synonym%28s%29> ?syn }}
    FILTER(CONTAINS(LCASE(?submission_value), LCASE("{needle}")) || CONTAINS(LCASE(COALESCE(?syn, "")), LCASE("{needle}"))
           || CONTAINS(LCASE(COALESCE(?nci_preferred_term, "")), LCASE("{needle}")))
}} ORDER BY ?codelist_name ?submission_value'''))


@server.tool()
def test_concept(code: str) -> str:
    """The test concept graph of an SDTM CT test term, by its C-code (e.g. C105585, Glucose): the test
    terms and their NCIt concept with ancestors; the COSMoS BC with that concept, and the BC of a Dataset
    Specialization whose --TESTCD row assigns the test, with their parents and Data Element Concepts; the CT terms Dataset Specializations bind to them; the Specializations. N-Triples,
    every triple as in the graphs (examples/test_concept_graph.rq)."""
    if not re.fullmatch(r'C\d+', code):
        raise ToolError(f'{code!r} is not a C-code')
    if not bool(query(f'ASK {{ ?t <{CT}Code> "{code}" ; <{CT}Codelist%20Code> ?cl }}')):
        raise ToolError(f'{code}: no SDTM CT term row has this Code')
    rq = fetch(SITE + 'examples/test_concept_graph.rq').decode('utf-8')
    rq, n = re.subn(r'VALUES \?code \{ "C\d+" \}', f'VALUES ?code {{ "{code}" }}', rq)
    if n != 1:
        raise ToolError('test_concept_graph.rq: expected one line VALUES ?code { "C..." }')
    return ntriples(query(rq))


@server.tool()
def describe(iri: str) -> str:
    """Every triple with the IRI as subject, and every triple with it as object (at most 500 each),
    as N-Triples. A row IRI gives its cells and links; a class or property IRI its label, domain,
    range and, for a link, description and rule (the vocabulary graph is loaded too)."""
    node = NamedNode(iri)
    out = query(f'CONSTRUCT {{ <{node.value}> ?p ?o }} WHERE {{ <{node.value}> ?p ?o }} LIMIT {MAX_ROWS}')
    inc = query(f'CONSTRUCT {{ ?s ?p <{node.value}> }} WHERE {{ ?s ?p <{node.value}> }} LIMIT {MAX_ROWS}')
    return ntriples(out) + '\n\n# incoming\n' + ntriples(inc)


@server.tool()
def sparql(query_text: str) -> str:
    """A read-only SPARQL query (SELECT, ASK, CONSTRUCT or DESCRIBE) over the union of the published
    graphs; each graph is also a named graph (its dataset IRI in catalog.ttl). SELECT returns
    tab-separated rows (at most 500), CONSTRUCT/DESCRIBE N-Triples. Prefixes and IRIs: llms.txt."""
    try:
        result = query(query_text)
    except SyntaxError as e:
        raise ToolError(f'SPARQL syntax: {e}') from e
    if isinstance(result, QueryBoolean):
        return str(bool(result)).lower()
    if isinstance(result, QuerySolutions):
        return table(result)
    return ntriples(result)


def _resource(path, mime):
    def read():
        return fetch(SITE + path).decode('utf-8')
    server.resource(SITE + path, name=path, mime_type=mime)(read)


for _path, _mime in [('llms.txt', 'text/plain'), ('catalog.ttl', 'text/turtle'),
                     ('schema/vocabulary.ttl', 'text/turtle'), ('schema/links.yaml', 'text/yaml')]:
    _resource(_path, _mime)


if __name__ == '__main__':
    server.run()
