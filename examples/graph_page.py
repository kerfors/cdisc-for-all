"""One HTML page from the result of test_concept_graph.rq: the graph in columns
(Test, Concept, BC, DEC, Values), each edge named by its link, and every triple of a node
on click. A view of the query result for reading; it adds no value to the graph."""
import json
from html import escape
from pathlib import Path
from urllib.parse import unquote

from pyoxigraph import Literal

NS = 'https://kerfors.github.io/cdisc-for-all/'
RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
CT = NS + 'def/sdtm-ct#SDTM%20Terminology'
NCIT = NS + 'def/ncit-flat#Thesaurus'
CUI = NS + 'def/nci-code-cui-map#nci_code_cui_map'
HIER = NS + 'def/cosmos#cdisc_biomedical_concepts_hierarchy_latest'
BC_ROW = NS + 'def/cosmos#cdisc_biomedical_concepts_latest'
DSS = NS + 'def/cosmos#cdisc_sdtm_dataset_specializations_latest'
CT_NCIT = NS + 'link/sdtm-ct/SDTM%20Terminology#Code'
BC_NCIT = NS + 'link/cosmos/cdisc_biomedical_concepts_latest#ncit_code'
DEC_NCIT = NS + 'link/cosmos/cdisc_biomedical_concepts_latest#ncit_dec_code'
NCIT_PARENT = NS + 'link/ncit-flat/Thesaurus#parents'
CUI_NCIT = NS + 'link/nci-code-cui-map/nci_code_cui_map#code'
DSS_DEC = NS + 'link/cosmos/cdisc_sdtm_dataset_specializations_latest#dec_id'
DSS_TERMS = {NS + 'link/cosmos/cdisc_sdtm_dataset_specializations_latest#assigned_term',
             NS + 'rule/cosmos/cdisc_sdtm_dataset_specializations_latest#value_list/sdtm-ct/SDTM%20Terminology'}
DSS_BC = NS + 'link/cosmos/cdisc_sdtm_dataset_specializations_latest#bc_id'
ASSIGNED = NS + 'link/cosmos/cdisc_sdtm_dataset_specializations_latest#assigned_term'
DECS = 'https://www.cdisc.org/cosmos/biomedical_concept_v1.0dataElementConcepts'
GROUP = 'https://www.cdisc.org/cosmos/sdtm_v1.0/SDTMGroup'
VARIABLES = 'https://www.cdisc.org/cosmos/sdtm_v1.0/variables'
LABEL_COLUMNS = ['CDISC Submission Value', 'dec_label', 'bc_short_name', 'short_name', 'display name', 'synonyms', 'code']
SOURCES = {CT: 'SDTM CT', NCIT: 'NCIt', CUI: 'NCIt', HIER: 'COSMoS BC', BC_ROW: 'COSMoS BC', DSS: 'COSMoS DSS'}


def column(p):
    """The published column name of a base property, or the local name of another property."""
    return unquote(p.rsplit('#', 1)[-1] if '#' in p else p.rsplit('/', 1)[-1])


def kind(p, names):
    """Where a property comes from: a published column (base), a link, or COSMoS's own model."""
    if p in names:
        return 'Links'
    if p.startswith(NS + 'def/'):
        return 'Published columns'
    return "COSMoS's own model (linked/cosmos-model.ttl)"


def link_names(links_yaml):
    from cfa.link import load_links
    names = {s['iri']: s['name'] for s in load_links(links_yaml)}
    names[DECS] = 'COSMoS BC model: dataElementConcepts'
    return names


def page_data(triples, links_yaml, group_dec):
    """Nodes (with every triple), the drawn nodes per column, the edges, from the result triples."""
    names = link_names(links_yaml)
    out, types = {}, {}
    for t in triples:
        s, p, o = t.subject.value, t.predicate.value, t.object
        if p == RDF_TYPE:
            types.setdefault(s, set()).add(o.value)
        out.setdefault(s, []).append((p, o.value, isinstance(o, Literal)))
    base_type = {n: next((x for x in ts if x in SOURCES), None) for n, ts in types.items()}

    def value(n, col):
        return next((v.split('|')[0] for p, v, lit in out.get(n, []) if lit and column(p) == col), None)

    def label(n):
        text = next((v for c in LABEL_COLUMNS if (v := value(n, c))), column(n))
        return f'{column(n)} {text}' if base_type.get(n) == NCIT and text != column(n) else text

    def objects(n, pred):
        return [v for p, v, lit in out.get(n, []) if p == pred and not lit]

    # the test terms: the terms of the start concept (no Dataset Specialization row binds them to a DEC),
    # and the terms that the BC's Specializations assign on their test rows (rows with the BC link)
    dec_bound = {t for r, ty in base_type.items() if ty == DSS and objects(r, DSS_DEC) for x in DSS_TERMS for t in objects(r, x)}
    test_rows = [r for r, ty in base_type.items() if ty == DSS and objects(r, DSS_BC)]
    spec_tests = sorted({t for r in test_rows for t in objects(r, ASSIGNED)})
    bc_concepts = {c for n, t in base_type.items() if t == BC_ROW for c in objects(n, BC_NCIT)}
    start_concepts = {c for n, t in base_type.items() if t == CT and n not in dec_bound for c in objects(n, CT_NCIT)}
    concepts = sorted(start_concepts & bc_concepts if bc_concepts else start_concepts)  # without a BC: only the start terms are there
    concept_tests = sorted(n for n, t in base_type.items() if t == CT and n not in dec_bound and set(objects(n, CT_NCIT)) & set(concepts))
    tests = concept_tests + sorted((t for t in spec_tests if t not in concept_tests), key=lambda n: label(n))
    bc_all = sorted((n for n, t in base_type.items() if t == BC_ROW and set(objects(n, BC_NCIT)) & set(concepts)),
                    key=lambda n: label(n))
    bc_rows = [n for n in bc_all if value(n, 'dec_id')]
    bc_only = [n for n in bc_all if not value(n, 'dec_id')]  # a BC row with an empty dec_id: a BC without DECs
    hier = [n for n, t in base_type.items() if t == HIER]
    hier = sorted(hier, key=lambda n: (any(n in objects(h, NS + 'link/cosmos/cdisc_biomedical_concepts_hierarchy_latest#parent_bc_id') for h in hier), label(n)), reverse=True) + bc_only
    bound, values, group = {}, [], {}
    for r, t in base_type.items():
        if t != DSS:
            continue
        for dec in objects(r, DSS_DEC):
            for x in DSS_TERMS:
                for term in objects(r, x):
                    bound.setdefault((dec, term), []).append(r)
    for dec in bc_rows:
        for term in sorted({t for d, t in bound if d == dec}, key=lambda n: (value(n, 'Codelist Name') or '', label(n))):
            if term not in values:
                values.append(term)
                group[term] = dec
    # one box per test: the test terms with the same NCIt concept (for GLUC: GLUC and Glucose) share a box
    box = {t: 'test:' + (objects(t, CT_NCIT) or [t])[0] for t in tests}
    boxes = list(dict.fromkeys(box[t] for t in tests))
    members = {b: sorted((t for t in tests if box[t] == b), key=lambda t: (value(t, 'Codelist Name') or '', label(t))) for b in boxes}
    columns = [('Test', 'SDTM CT, per NCIt concept', boxes), ('Concept', 'the shared NCIt concept', concepts),
               ('BC', 'COSMoS Biomedical Concepts', hier), ('DEC', 'its Data Element Concepts (BC rows)', bc_rows),
               ('Values', 'bound CT terms, per DEC', values)]
    edges = []
    for b in boxes:
        edges += [(b, c, names[CT_NCIT], []) for c in sorted({c for t in members[b] for c in objects(t, CT_NCIT)}) if c in concepts]
    via = {}
    for r in test_rows:
        for t in objects(r, ASSIGNED):
            for h in objects(r, DSS_BC):
                if t not in concept_tests:  # drawn through the shared NCIt concept; the Specialization route only where that is missing
                    via.setdefault((box[t], h), []).append(r)
    for (t, h), rows in sorted(via.items()):
        edges.append((t, h, 'via Specialization test rows (links: ' + names[ASSIGNED] + ', ' + names[DSS_BC] + ')', sorted(rows)))
    for n in bc_all:
        edges += [(n, c, names[BC_NCIT], []) for c in objects(n, BC_NCIT)]
    for h in hier:
        edges += [(h, d, names[DECS], []) for d in objects(h, DECS) if d in bc_rows]
        edges += [(h, x, names[p], []) for p, x, lit in out[h] if not lit and p in names and x in hier]
    for (dec, term), rows in sorted(bound.items()):
        edges.append((dec, term, 'via Dataset Specialization rows (links: ' + ', '.join(sorted({names[DSS_DEC]} | {names[x] for x in DSS_TERMS})) + ')', sorted(rows)))

    def ancestors(c):
        seen, todo = [], [c]
        while todo:
            for p in objects(todo.pop(), NCIT_PARENT):
                if p not in seen:
                    seen.append(p)
                    todo.append(p)
        return seen

    nodes = {}
    for n, triples_n in out.items():
        info = {'label': label(n), 'source': SOURCES.get(base_type.get(n), 'COSMoS model'), 'types': sorted(types.get(n, [])),
                'triples': [[names.get(p, column(p)), v, lit, kind(p, names)] for p, v, lit in triples_n if p != RDF_TYPE]}
        if base_type.get(n) == NCIT:
            info['ancestors'] = [[a, label(a)] for a in ancestors(n)]
            info['cui'] = [label(c) for c, t in base_type.items() if t == CUI and n in objects(c, CUI_NCIT)]
        nodes[n] = info
    for b in boxes:
        nodes[b] = {'label': ' / '.join(dict.fromkeys(label(t) for t in members[b])), 'source': 'SDTM CT', 'types': [], 'triples': [],
                    'members': [[t, label(t), value(t, 'Codelist Name') or ''] for t in members[b]]}
    for n in nodes:
        for row in nodes[n]['triples']:
            if not row[2] and row[1] in nodes:
                row.append(nodes[row[1]]['label'])
    dec_table = []
    for dec in bc_rows:
        terms = [label(t) for d, t in bound if d == dec]
        dec_table.append([label(dec), value(dec, 'dec_id') or '', value(dec, 'data_type') or '',
                          next((v for p, v, lit in out[dec] if column(p) == 'example_set'), ''), '; '.join(sorted(terms))])
    specializations = []
    for g in sorted((n for n, ts in types.items() if GROUP in ts), key=lambda n: value(n, 'datasetSpecializationId') or ''):
        rows = set(objects(g, VARIABLES))
        pairs = sorted({(d, t) for (d, t), rs in bound.items() if rows & set(rs)})
        by = sorted(label(t) for d, t in pairs if value(d, 'dec_id') == group_dec)
        specializations.append({'id': g, 'vlm_group_id': value(g, 'datasetSpecializationId'), 'short_name': value(g, 'shortName'),
                                'rows': sorted(rows), 'pairs': [[d, t] for d, t in pairs], 'group': ' / '.join(by)})
    group_label = next((label(d) for d in bc_rows if value(d, 'dec_id') == group_dec), group_dec)
    level = 'BC and DECs' if bc_rows else 'BC, no DECs' if bc_all else 'test and concept, no BC'
    return {'level': level, 'columns': [[a, b, c] for a, b, c in columns], 'edges': edges, 'nodes': nodes, 'decs': dec_table,
            'groups': group, 'specializations': specializations, 'group_label': group_label}


def write_page(triples, path, title, links_yaml, group_dec='C70713'):
    """title: the page title; None gives "The test <first test box>: concept, BC and DECs" (or
    ": concept and BC", ": concept", by what is there).
    group_dec: the DEC whose bound terms group the Specialization chips (default C70713,
    Biospecimen Type); a Specialization that binds no term to it is shown under "none bound"."""
    data = page_data(triples, links_yaml, group_dec)
    if title is None:
        shown = {'BC and DECs': 'concept, BC and DECs', 'BC, no DECs': 'concept and BC', 'test and concept, no BC': 'concept'}[data['level']]
        title = f"The test {data['nodes'][data['columns'][0][2][0]]['label']}: {shown}"
    data['title'] = title
    template = (Path(__file__).parent / 'graph_page.html').read_text(encoding='utf-8')
    html = template.replace('__TITLE__', escape(title)).replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    Path(path).write_text(html, encoding='utf-8')
    return data
