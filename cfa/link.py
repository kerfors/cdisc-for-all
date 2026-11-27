"""The links between base rows, from schema/links.yaml.

Each slot of links.yaml is one link property. make_links() builds its triples from the base
graphs: a row whose key value(s) equal the target columns of exactly one target row gets
one triple, row -> target row (a key with an empty column gets none). link_shapes()
generates one SHACL-SPARQL shape per link (severity sh:Info): a row with a value in the link
column and no link (or, for a column of several keys, fewer links than keys) is a result.
The validation report is Link_Check.

The shapes select their focus nodes with a SHACL-AF SPARQL target (the same query with the
class added), so only candidate rows are validated; pySHACL needs advanced=True. A shape
with sh:targetClass gives the same results, about 100 times slower on these graphs.

The link IRI is {ns}link/{source}/{table}#{column} (published key) or
{ns}rule/{source}/{table}#{column} (by rule), column = the base column the link rests on.
"""

import json

from linkml_runtime.utils.schemaview import SchemaView
from rdflib import RDF, Graph, Literal, Namespace, URIRef

from cfa import NS
from cfa.rule import class_iri, pct, property_iri

SH = Namespace('http://www.w3.org/ns/shacl#')
KINDS = {'published key': 'link', 'by rule': 'rule'}


def link_graph_iri(kind):
    return f'{NS}graph/{"links" if kind == "published key" else "by-rule"}'


def _class_source(sv, table):
    uri = sv.get_class(table).class_uri
    prefix = f'{NS}def/'
    if not uri.startswith(prefix) or '#' not in uri:
        raise ValueError(f'{table}: class_uri {uri} is not a base class IRI')
    source, frag = uri[len(prefix):].split('#', 1)
    if frag != pct(table):
        raise ValueError(f'{table}: class_uri {uri} does not end in the table name')
    return source


def load_links(path):
    """The link specs of links.yaml, checked: kind, columns in the domain, target columns in
    the range, slot_uri = the rule IRI, a rule stated for a link by rule."""
    sv = SchemaView(str(path))
    specs = []
    for name in sv.schema.slots:
        slot = sv.get_slot(name)
        ann = {k: v.value for k, v in (slot.annotations or {}).items()}
        kind = ann['link']
        if kind not in KINDS:
            raise ValueError(f'{name}: link {kind!r} is not one of {list(KINDS)}')
        if (kind == 'by rule') != ('rule' in ann):
            raise ValueError(f'{name}: a rule is stated for, and only for, a link by rule')
        cols = json.loads(ann['columns'])
        target = json.loads(ann['target'])
        target_empty = json.loads(ann.get('target_empty', '[]'))
        sep = ann.get('separator')
        if len(cols) != len(target):
            raise ValueError(f'{name}: columns and target differ in length')
        if sep is not None and len(cols) != 1:
            raise ValueError(f'{name}: a separator needs exactly one column')
        if bool(slot.multivalued) != (sep is not None):
            raise ValueError(f'{name}: multivalued if and only if a separator is given')
        dom, rng = slot.domain, slot.range
        dsrc, rsrc = _class_source(sv, dom), _class_source(sv, rng)
        for c in cols:
            if c not in sv.get_class(dom).attributes:
                raise ValueError(f'{name}: {c!r} is not a column of {dom}')
        for c in target + target_empty:
            if c not in sv.get_class(rng).attributes:
                raise ValueError(f'{name}: {c!r} is not a column of {rng}')
        iri = f'{NS}{KINDS[kind]}/{dsrc}/{pct(dom)}#{pct(cols[-1])}'
        if slot.slot_uri != iri:
            raise ValueError(f'{name}: slot_uri {slot.slot_uri} is not {iri}')
        specs.append({
            'name': name, 'iri': iri, 'kind': kind, 'rule': ann.get('rule'),
            'description': slot.description,
            'domain': dom, 'domain_source': dsrc, 'range': rng, 'range_source': rsrc,
            'columns': cols, 'target': target, 'target_empty': target_empty, 'separator': sep,
            'domain_class': class_iri(dsrc, dom), 'range_class': class_iri(rsrc, rng),
            'column_iris': [property_iri(dsrc, dom, c) for c in cols],
            'target_iris': [property_iri(rsrc, rng, c) for c in target],
            'target_empty_iris': [property_iri(rsrc, rng, c) for c in target_empty],
            'shape': f'{NS}shape/{pct(name)}',
        })
    iris = [s['iri'] for s in specs]
    if len(set(iris)) != len(iris):
        raise ValueError('two links with the same IRI')
    return specs


def _values(g, node, props):
    out = []
    for p in props:
        vs = list(g.objects(node, URIRef(p)))
        if len(vs) > 1:
            raise ValueError(f'{node}: more than one value for {p}')
        out.append(str(vs[0]) if vs else '')
    return out


def _tokens(value, sep):
    return [t.strip(' ') for t in value.split(sep)]


def make_links(g, spec):
    """The triples of one link over the base graphs g. Stops if a key matches more than one
    target row, or a column of several keys repeats a key."""
    index = {}
    for t in g.subjects(RDF.type, URIRef(spec['range_class'])):
        if any(_values(g, t, spec['target_empty_iris'])):
            continue
        key = tuple(_values(g, t, spec['target_iris']))
        if key in index:
            raise ValueError(f'{spec["name"]}: target key {key} matches {index[key]} and {t}')
        index[key] = t
    out = Graph()
    p = URIRef(spec['iri'])
    for s in g.subjects(RDF.type, URIRef(spec['domain_class'])):
        vals = _values(g, s, spec['column_iris'])
        if '' in vals:
            continue
        if spec['separator'] is not None:
            toks = _tokens(vals[0], spec['separator'])
            if len(set(toks)) != len(toks):
                raise ValueError(f'{s}: a key repeats in {vals[0]!r}')
            keys = [(t,) for t in toks]
        else:
            keys = [tuple(vals)]
        for k in keys:
            if k in index:
                out.add((s, p, index[k]))
    return out


def _sparql(spec, this='$this', cls=None):
    col = spec['column_iris'][-1]
    link = spec['iri']
    head = f'SELECT {this} ?value WHERE {{ ' + (f'{this} a <{cls}> . ' if cls else '')
    if spec['separator'] is None:
        return head + f'{this} <{col}> ?value . FILTER NOT EXISTS {{ {this} <{link}> ?t }} }}'
    sep = json.dumps(spec['separator'])
    return (head + f'{this} <{col}> ?value . OPTIONAL {{ {this} <{link}> ?t }} }} '
            f'GROUP BY {this} ?value '
            f'HAVING (COUNT(DISTINCT ?t) < (STRLEN(?value) - STRLEN(REPLACE(?value, {sep}, "", "q"))) / STRLEN({sep}) + 1)')


def link_shapes(specs):
    """One SHACL-SPARQL node shape per link, severity sh:Info, focus nodes by a SPARQL target."""
    g = Graph()
    g.bind('sh', SH)
    for spec in specs:
        shape = URIRef(spec['shape'])
        con = URIRef(spec['shape'] + '-sparql')
        target = URIRef(spec['shape'] + '-target')
        g.add((shape, RDF.type, SH.NodeShape))
        g.add((shape, SH.target, target))
        g.add((shape, SH.severity, SH.Info))
        g.add((target, RDF.type, SH.SPARQLTarget))
        g.add((target, SH.select, Literal(_sparql(spec, '?this', spec['domain_class']))))
        g.add((shape, SH.sparql, con))
        g.add((con, RDF.type, SH.SPARQLConstraint))
        g.add((con, SH.message, Literal(f'{spec["name"]}: no {spec["kind"]} link for the value')))
        g.add((con, SH.select, Literal(_sparql(spec))))
    return g


def unresolved(g, spec, node, value):
    """The keys of a link column value on a node that have no link (for the Link_Check view):
    the value split at the separator, minus the target keys the node links to."""
    if spec['separator'] is None:
        return [value]
    linked = {_values(g, t, spec['target_iris'])[0] for t in g.objects(node, URIRef(spec['iri']))}
    return [t for t in _tokens(value, spec['separator']) if t not in linked]


LINK_CHECK_COLUMNS = ['Link', 'Kind', 'Table', 'Row', 'Column', 'Value', 'Not resolved', 'Target table']
LINKS_SHEET_COLUMNS = ['Link', 'Property', 'Kind', 'Rule', 'Table', 'Columns', 'Separator',
                       'Target table', 'Target columns', 'Target columns empty', 'Description']


def link_check_frame(report, g, specs):
    """Link_Check as a table, from the SHACL validation report: one row per result (a row of a
    base table and the value of its link column that does not resolve, in full or in part).
    Stops on a result that is not sh:Info or not from a link shape."""
    import pandas as pd
    by_shape = {URIRef(s['shape'] + '-sparql'): s for s in specs}
    by_node_shape = {URIRef(s['shape']): s for s in specs}
    rows = []
    for r in report.subjects(RDF.type, SH.ValidationResult):
        if report.value(r, SH.resultSeverity) != SH.Info:
            raise ValueError(f'{r}: a result that is not sh:Info')
        spec = by_node_shape.get(report.value(r, SH.sourceShape)) or by_shape.get(report.value(r, SH.sourceShape))
        if spec is None:
            raise ValueError(f'{r}: not from a link shape')
        node = report.value(r, SH.focusNode)
        value = str(report.value(r, SH.value))
        rows.append([spec['name'], spec['kind'], spec['domain'], str(node), spec['columns'][-1], value,
                     ' '.join(unresolved(g, spec, node, value)) if spec['separator'] else '',
                     spec['range']])
    df = pd.DataFrame(rows, columns=LINK_CHECK_COLUMNS, dtype=str)
    return df.sort_values(['Link', 'Row', 'Value'], kind='stable').reset_index(drop=True)


def links_sheet(specs):
    """The links contract as a sheet (from links.yaml): one row per link."""
    import pandas as pd
    rows = [[s['name'], s['iri'], s['kind'], s['rule'] or '', s['domain'], json.dumps(s['columns'], ensure_ascii=False),
             s['separator'] or '', s['range'], json.dumps(s['target'], ensure_ascii=False),
             json.dumps(s['target_empty'], ensure_ascii=False) if s['target_empty'] else '', s['description'] or '']
            for s in specs]
    return pd.DataFrame(rows, columns=LINKS_SHEET_COLUMNS, dtype=str)
