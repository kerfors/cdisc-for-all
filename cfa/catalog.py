"""The catalogue (DCAT + VoID, catalog.ttl) and the guide for AI agents (llms.txt), both from
what the repository already states: Reference_Versions.json (the pins), the Provenance files
of the base and linked layers, and schema/links.yaml. Nothing is counted or classified here:
the triple counts and hashes are those the Provenance files record."""
import json
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, RDF, RDFS, XSD

from cfa.pins import file_sha256

SITE = 'https://kerfors.github.io/cdisc-for-all/'
REPO = 'https://github.com/kerfors/cdisc-for-all'
CAT = Namespace(SITE + 'catalog#')
VOID = Namespace('http://rdfs.org/ns/void#')
SPDX = Namespace('http://spdx.org/rdf/terms#')
MIT = URIRef('https://opensource.org/licenses/MIT')
# the licence of each source's content, as the README states it; a URI where the publisher gives one
LICENCE = {'ncit-flat': URIRef('https://creativecommons.org/licenses/by/4.0/'),
           'nci-code-cui-map': URIRef('https://creativecommons.org/licenses/by/4.0/'),
           'cosmos': MIT}
RIGHTS = {'sdtm-ct': 'The terms of CDISC and NCI EVS.', 'nsv-registry': 'The terms of CDISC and NCI EVS.',
          'ncit-flat': 'NCI Thesaurus Terms of Use: https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/ThesaurusTermsofUse.htm',
          'nci-code-cui-map': 'NCI Thesaurus Terms of Use: https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/ThesaurusTermsofUse.htm',
          'cosmos': 'MIT licence, Copyright CDISC.',
          'sdtmig': 'cdisc.org sign-in: the graph, its view and its links are built locally and not published.',
          'sdtm-model': 'cdisc.org sign-in: the graph, its view and its links are built locally and not published.'}
MEDIA = {'.ttl': 'text/turtle', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
         '.tsv': 'text/tab-separated-values', '.json': 'application/json', '.html': 'text/html'}
PREFIXES = {'dcat': DCAT, 'dcterms': DCTERMS, 'void': VOID, 'spdx': SPDX, 'cat': CAT, 'rdfs': RDFS}


def _distribution(g, dataset, root, rel, title):
    """A distribution of dataset: the published file rel (relative to the repository root)."""
    path = root / rel
    d = CAT['file/' + rel]
    g.add((dataset, DCAT.distribution, d))
    g.add((d, RDF.type, DCAT.Distribution))
    g.add((d, DCTERMS.title, Literal(title)))
    g.add((d, DCAT.downloadURL, URIRef(SITE + rel.replace(' ', '%20'))))
    g.add((d, DCAT.mediaType, URIRef('https://www.iana.org/assignments/media-types/' + MEDIA[path.suffix])))
    c = BNode()
    g.add((d, SPDX.checksum, c))
    g.add((c, SPDX.algorithm, SPDX.checksumAlgorithm_sha256))
    g.add((c, SPDX.checksumValue, Literal(file_sha256(path), datatype=XSD.hexBinary)))
    return d


def catalog(root, specs):
    """The catalogue graph. root: the repository root; specs: cfa.link.load_links(...)."""
    root = Path(root)
    pins = json.loads((root / 'Reference_Versions.json').read_text(encoding='utf-8'))
    linked = json.loads((root / 'linked' / 'Provenance.json').read_text(encoding='utf-8'))
    model = json.loads((root / 'linked' / 'Provenance_COSMoS_Model.json').read_text(encoding='utf-8'))
    g = Graph()
    cat = CAT['catalog']
    g.add((cat, RDF.type, DCAT.Catalog))
    g.add((cat, DCTERMS.title, Literal('cdisc-for-all')))
    g.add((cat, DCTERMS.description, Literal('CDISC and NCIt content as published, linked: the base graphs (one per source, '
                                             'as published), the link graphs, the COSMoS model graph, Link_Check and the SSSOM mapping set.')))
    g.add((cat, DCTERMS.license, MIT))
    g.add((cat, DCAT.landingPage, URIRef(SITE)))
    g.add((cat, RDFS.seeAlso, URIRef(REPO)))
    graphs = {}
    for src, pin in pins.items():
        ds = URIRef(SITE + 'graph/' + src)
        graphs[src] = ds
        g.add((cat, DCAT.dataset, ds))
        for t in (DCAT.Dataset, VOID.Dataset):
            g.add((ds, RDF.type, t))
        g.add((ds, DCTERMS.title, Literal(f"{pin['title']} (base graph)")))
        g.add((ds, DCTERMS.publisher, Literal(pin['publisher'])))
        g.add((ds, URIRef(str(DCAT) + 'version'), Literal(pin['version'])))
        if pin.get('url') or pin.get('repository'):
            g.add((ds, DCTERMS.source, URIRef(pin.get('url') or pin['repository'])))
        g.add((ds, DCTERMS.rights, Literal(RIGHTS[src])))
        if src in LICENCE:
            g.add((ds, DCTERMS.license, LICENCE[src]))
        prov = root / 'base' / src / 'Provenance.json'
        ttl = root / 'base' / src / f'{src}.ttl'
        if not prov.exists() or not ttl.exists() or pin['access'] != 'public':
            g.add((ds, DCTERMS.accessRights, Literal('Not published: ' + RIGHTS[src])))
            continue
        p = json.loads(prov.read_text(encoding='utf-8'))
        if p['graph'] != str(ds):
            raise ValueError(f"{src}: Provenance graph {p['graph']} is not {ds}")
        g.add((ds, VOID.triples, Literal(p['triples'])))
        d = _distribution(g, ds, root, f'base/{src}/{src}.ttl', 'the base graph (Turtle)')
        g.add((ds, VOID.dataDump, URIRef(SITE + f'base/{src}/{src}.ttl')))
        for x in sorted((root / 'base' / src).glob('*.xlsx')):
            _distribution(g, ds, root, f'base/{src}/{x.name}', 'Excel view of the base graph')
    for part, info in sorted(linked['link_graphs'].items()):
        if part.endswith('-signin'):
            continue
        ds = URIRef(info['graph'])
        g.add((cat, DCAT.dataset, ds))
        for t in (DCAT.Dataset, VOID.Dataset):
            g.add((ds, RDF.type, t))
        g.add((ds, DCTERMS.title, Literal('Link graph: ' + ('published-key links' if part == 'links' else 'links by rule'))))
        g.add((ds, DCTERMS.license, MIT))
        g.add((ds, VOID.triples, Literal(info['triples'])))
        _distribution(g, ds, root, f"linked/{info['file']}", 'the link graph (Turtle)')
        g.add((ds, VOID.dataDump, URIRef(SITE + f"linked/{info['file']}")))
        g.add((ds, RDFS.comment, Literal('The links to and from the sign-in sources are in a -signin file, built locally and not published.')))
    ds = URIRef(model['graph'])
    g.add((cat, DCAT.dataset, ds))
    for t in (DCAT.Dataset, VOID.Dataset):
        g.add((ds, RDF.type, t))
    g.add((ds, DCTERMS.title, Literal("COSMoS model graph: the COSMoS export in COSMoS's authored model")))
    g.add((ds, DCTERMS.license, MIT))
    g.add((ds, VOID.triples, Literal(model['triples'])))
    _distribution(g, ds, root, f"linked/{model['file']}", 'the COSMoS model graph (Turtle)')
    g.add((ds, VOID.dataDump, URIRef(SITE + f"linked/{model['file']}")))
    voc = URIRef(SITE + 'graph/vocabulary')
    g.add((cat, DCAT.dataset, voc))
    for t in (DCAT.Dataset, VOID.Dataset):
        g.add((voc, RDF.type, t))
    g.add((voc, DCTERMS.title, Literal('Vocabulary: the classes and properties the graphs use, in RDFS, restated from the LinkML schema')))
    g.add((voc, DCTERMS.license, MIT))
    _distribution(g, voc, root, 'schema/vocabulary.ttl', 'the vocabulary (Turtle)')
    g.add((voc, VOID.dataDump, URIRef(SITE + 'schema/vocabulary.ttl')))
    rep = CAT['link-check']
    g.add((cat, DCAT.dataset, rep))
    g.add((rep, RDF.type, DCAT.Dataset))
    g.add((rep, DCTERMS.title, Literal('Link_Check: every reference in the published content that does not resolve, '
                                       'and every link to a row that carries a marker its source publishes, such as COSMoS "[RETIRED]"')))
    g.add((rep, DCTERMS.license, MIT))
    _distribution(g, rep, root, 'linked/Link_Check.xlsx', 'Link_Check (Excel)')
    g.add((rep, RDFS.comment, Literal('The rows of the links that start from or end at a row of a sign-in source are in Link_Check-signin, built locally and not published.')))
    mapping = CAT['sssom']
    g.add((cat, DCAT.dataset, mapping))
    g.add((mapping, RDF.type, DCAT.Dataset))
    g.add((mapping, DCTERMS.title, Literal('SSSOM mapping set of the links by a rule that matches a general name')))
    g.add((mapping, DCTERMS.license, MIT))
    for part, info in sorted(linked['sssom'].items()):
        if not part.endswith('-signin'):
            _distribution(g, mapping, root, f"linked/{info['file']}", 'SSSOM TSV')
    for s in specs:
        ls = CAT['linkset/' + s['name'].replace(' ', '_')]
        part = URIRef(SITE + 'graph/' + ('links' if s['kind'] == 'published key' else 'by-rule'))
        g.add((ls, RDF.type, VOID.Linkset))
        g.add((part, VOID.subset, ls))
        g.add((ls, DCTERMS.title, Literal(s['name'])))
        g.add((ls, DCTERMS.description, Literal(s['description'])))
        g.add((ls, VOID.linkPredicate, URIRef(s['iri'])))
        g.add((ls, VOID.subjectsTarget, graphs[s['domain_source']]))
        g.add((ls, VOID.objectsTarget, graphs[s['range_source']]))
        g.add((ls, DCTERMS.type, Literal(s['kind'])))
        if s['rule']:
            g.add((ls, RDFS.comment, Literal('Rule: ' + s['rule'])))
        if {s['domain_source'], s['range_source']} & {'sdtmig', 'sdtm-model'}:
            g.add((ls, DCTERMS.accessRights, Literal('Built locally, not published: it starts from or ends at a sign-in source.')))
    return g


def llms_txt(root, specs, g):
    """The guide for AI agents, in the llms.txt layout (title, summary, sections of links)."""
    root = Path(root)
    pins = json.loads((root / 'Reference_Versions.json').read_text(encoding='utf-8'))
    out = ['# cdisc-for-all', '',
           '> CDISC and NCIt content as published, linked: one RDF graph per source in the shape the source publishes, '
           'the links between the sources as RDF, and a report (Link_Check) of every reference that does not resolve. '
           'For study design: what is defined about a lab test, and why.', '',
           'Rules an agent should keep: every literal is a cell of the source as published (column names kept); a link rests on a '
           'published key or on a stated rule (links by rule are in their own graph); broken references are reported in Link_Check, '
           'not repaired; nothing is added: no classification, no counts, no interpretation. Do not present an inference as published content.', '',
           f'IRIs: `{SITE}def/<source>/<table>#<column>` (a published column), `{SITE}id/<source>/<table>/<key>` (a row), '
           f'`{SITE}link/...` (a link on a published key), `{SITE}rule/...` (a link by rule). They are identifiers, not dereferenceable, and stable only within a pin; this is not a general RDF representation of the CDISC standards. '
           'NCIt concepts keep NCI\'s own IRIs (http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C...).', '',
           f'What each class and property means: [vocabulary.ttl]({SITE}schema/vocabulary.ttl) (RDFS, from the LinkML schema: '
           'every table as a class, every column as a property labelled with its published column name, every link with its description and rule).', '',
           f'Machine-readable description of all of this: [catalog.ttl]({SITE}catalog.ttl) (DCAT + VoID: files, licences, checksums, linksets).', '',
           '## Base graphs (one per source, as published)', '']
    for src, pin in pins.items():
        ttl = root / 'base' / src / f'{src}.ttl'
        if pin['access'] == 'public' and ttl.exists():
            out.append(f"- [{src}.ttl]({SITE}base/{src}/{src}.ttl): {pin['title']}, {pin['version']} ({pin['publisher']}). {RIGHTS[src]}")
        else:
            out.append(f"- {src}: {pin['title']}, {pin['version']} ({pin['publisher']}). Not published: {RIGHTS[src]}")
    out += ['', '## Linked layer', '',
            f'- [links.ttl]({SITE}linked/links.ttl): links on published keys.',
            f'- [by-rule.ttl]({SITE}linked/by-rule.ttl): links by a stated rule.',
            f"- [cosmos-model.ttl]({SITE}linked/cosmos-model.ttl): the COSMoS export restated in COSMoS's authored model (COSMoS's own IRIs).",
            f'- [by-rule.sssom.tsv]({SITE}linked/by-rule.sssom.tsv): the links by a rule that matches a general name, as SSSOM.',
            f'- [Link_Check.xlsx]({SITE}linked/Link_Check.xlsx): every reference that does not resolve, and every link to a row with a published marker such as "[RETIRED]". The rows of the links that touch a sign-in source are in a local Link_Check-signin, not published.',
            f'- [links.yaml]({REPO}/blob/main/schema/links.yaml): every link as stated (key columns, target columns, rule).', '',
            '## The links (predicate: from table -> to table)', '']
    for s in specs:
        note = ' Built locally (sign-in source).' if {s['domain_source'], s['range_source']} & {'sdtmig', 'sdtm-model'} else ''
        rule = f" Rule: {s['rule']}" if s['rule'] else ''
        out.append(f"- `{s['iri']}` ({s['kind']}): {s['domain']} -> {s['range']}. {s['description']}{rule}{note}")
    out += ['', '## Using it', '',
            f'- [Start page]({SITE}) and [example pages]({SITE}examples/pages/): the test concept graph of nine lab tests; [link map]({SITE}examples/pages/link_map.html).',
            f'- [test_concept_graph.rq]({REPO}/blob/main/examples/test_concept_graph.rq): a SPARQL CONSTRUCT from an SDTM CT test C-code to its NCIt concept, the COSMoS BC, its Data Element Concepts, the bound CT terms and the Specializations. Load the base graphs, links.ttl, by-rule.ttl and cosmos-model.ttl into one store (the examples use Oxigraph).',
            f'- [test_concept.py]({REPO}/blob/main/examples/test_concept.py): runs it per C-code: `python examples/test_concept.py C105585` (needs the full requirements.txt).',
            f'- [cdisc_for_all_mcp.py]({SITE}mcp/cdisc_for_all_mcp.py): a local MCP server (stdio) over the published graphs: find_test, test_concept, describe, sparql (read-only); run with `uv run {SITE}mcp/cdisc_for_all_mcp.py`.',
            f'- [Getting_Started.ipynb]({REPO}/blob/main/examples/Getting_Started.ipynb): reads catalog.ttl, loads the published graphs into Oxigraph (one named graph each, SHA-256 checked) and follows one test hop by hop, naming each link.', '',
            '## Optional', '',
            f'- [README]({REPO}#readme): rules, sources, pins, licences.',
            f'- [CHANGES]({REPO}/blob/main/CHANGES.md): every step and decision.', '']
    return '\n'.join(out)
