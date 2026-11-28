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
{ns}rule/{source}/{table}#{column}/{target source}/{target table} (by rule), column = the base
column the link rests on. A link by rule names its target in the IRI, since several rules may
rest on the same column.

A link by rule may also have: requires (columns that must have a value for the link to apply),
unless (earlier links: the link applies only to a row that has none of them), match_empty (key
columns whose empty value matches an empty target column), targets "all"
(link every matching target row; a row with more targets than keys is reported as well), and
rule_function (a function of RULE_FUNCTIONS that gives, from the row's column values, the
target keys to try in order; the first key that matches is used), ends_with (the link applies
only to a row whose link column value ends with this text), target_separator (the last target
column holds several keys, split at this text, surrounding spaces removed), and unmatched
"not reported" with unmatched_rule (a row without a link is not a result, for a link that
matches names rather than resolving a reference; the reason stated).
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
        requires = json.loads(ann.get('requires', '[]'))
        match_empty = json.loads(ann.get('match_empty', '[]'))
        unless = json.loads(ann.get('unless', '[]'))
        targets = ann.get('targets', 'one')
        func = ann.get('rule_function')
        ends_with = ann.get('ends_with')
        target_sep = ann.get('target_separator')
        unmatched = ann.get('unmatched', 'reported')
        if unmatched not in ('reported', 'not reported') or (unmatched == 'not reported') != ('unmatched_rule' in ann):
            raise ValueError(f'{name}: unmatched is reported or not reported; not reported is stated in unmatched_rule')
        flag = json.loads(ann['flag']) if 'flag' in ann else None
        if (flag is None) != ('flag_rule' not in ann) or (flag is not None and set(flag) != {'column', 'ends_with'}):
            raise ValueError(f'{name}: flag is {{"column", "ends_with"}}, stated in flag_rule, both or neither')
        if targets not in ('one', 'all'):
            raise ValueError(f'{name}: targets {targets!r} is not one or all')
        if func is not None:
            if kind != 'by rule' or func not in RULE_FUNCTIONS:
                raise ValueError(f'{name}: rule_function {func!r} is not a rule function (by rule only)')
            if sep is not None:
                raise ValueError(f'{name}: a rule_function takes no separator')
        elif len(cols) != len(target):
            raise ValueError(f'{name}: columns and target differ in length')
        if (requires or unless or match_empty or targets != 'one' or ends_with or target_sep
                or unmatched != 'reported') and kind != 'by rule':
            raise ValueError(f'{name}: requires, unless, match_empty, targets, ends_with, target_separator '
                             'and unmatched are for a link by rule')
        if any(c not in cols[:-1] for c in match_empty):
            raise ValueError(f'{name}: match_empty names a key column other than the last')
        earlier = {x['name']: x for x in specs}
        for u in unless:
            if u not in earlier:
                raise ValueError(f'{name}: unless {u!r} is not an earlier link')
        if bool(slot.multivalued) != (sep is not None):
            raise ValueError(f'{name}: multivalued if and only if a separator is given')
        dom, rng = slot.domain, slot.range
        dsrc, rsrc = _class_source(sv, dom), _class_source(sv, rng)
        for c in cols + requires:
            if c not in sv.get_class(dom).attributes:
                raise ValueError(f'{name}: {c!r} is not a column of {dom}')
        for c in target + target_empty + ([flag['column']] if flag else []):
            if c not in sv.get_class(rng).attributes:
                raise ValueError(f'{name}: {c!r} is not a column of {rng}')
        iri = f'{NS}{KINDS[kind]}/{dsrc}/{pct(dom)}#{pct(cols[-1])}'
        if kind == 'by rule':
            iri += f'/{rsrc}/{pct(rng)}'
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
            'requires': requires, 'requires_iris': [property_iri(dsrc, dom, c) for c in requires],
            'unless': unless, 'unless_iris': [earlier[u]['iri'] for u in unless],
            'targets': targets, 'rule_function': func, 'match_empty': match_empty,
            'flag': flag, 'flag_rule': ann.get('flag_rule'),
            'ends_with': ends_with, 'target_separator': target_sep,
            'unmatched': unmatched, 'unmatched_rule': ann.get('unmatched_rule'),
            'flag_iri': property_iri(rsrc, rng, flag['column']) if flag else None,
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


def make_links(g, spec, made=None, matched=None):
    """The triples of one link over the base graphs g; made = the links made so far (for
    unless). Stops if a key matches more than one target row (unless targets is all), or a
    column of several keys repeats a key. For a link by a rule function, matched (a dict), if
    given, gets per triple (row, target) the row's column values and the target key that matched."""
    index = {}
    for t in g.subjects(RDF.type, URIRef(spec['range_class'])):
        if any(_values(g, t, spec['target_empty_iris'])):
            continue
        key = tuple(_values(g, t, spec['target_iris']))
        if spec['target_separator'] is None:
            tkeys = [key]
        else:
            tkeys = [key[:-1] + (x,) for x in _tokens(key[-1], spec['target_separator'])]
        for k in tkeys:
            if k in index and spec['targets'] == 'one':
                raise ValueError(f'{spec["name"]}: target key {k} matches {index[k]} and {t}')
            index.setdefault(k, []).append(t)
    func = RULE_FUNCTIONS[spec['rule_function']](g) if spec['rule_function'] else None
    out = Graph()
    p = URIRef(spec['iri'])
    for s in g.subjects(RDF.type, URIRef(spec['domain_class'])):
        vals = _values(g, s, spec['column_iris'])
        if vals[-1] == '' or '' in _values(g, s, spec['requires_iris']):
            continue
        if spec['ends_with'] is not None and not vals[-1].endswith(spec['ends_with']):
            continue
        if any((s, URIRef(u), None) in made for u in spec['unless_iris']):
            continue
        if func is not None:
            keys = [k for k in func(vals) if k in index][:1]
            if matched is not None and keys:
                for t in index[keys[0]]:
                    matched[(s, t)] = (vals, keys[0])
        elif any(v == '' and c not in spec['match_empty'] for c, v in zip(spec['columns'], vals)):
            continue
        elif spec['separator'] is not None:
            toks = _tokens(vals[-1], spec['separator'])
            if len(set(toks)) != len(toks):
                raise ValueError(f'{s}: a key repeats in {vals[-1]!r}')
            keys = [tuple(vals[:-1]) + (t,) for t in toks]
        else:
            keys = [tuple(vals)]
        for k in keys:
            for t in index.get(k, []):
                out.add((s, p, t))
    return out


def _sparql(spec, this='$this', cls=None, ambiguous=False):
    col = spec['column_iris'][-1]
    link = spec['iri']
    head = f'SELECT {this} ?value WHERE {{ ' + (f'{this} a <{cls}> . ' if cls else '')
    head += f'{this} <{col}> ?value . '
    if spec['ends_with'] is not None:
        head += f'FILTER(STRENDS(?value, {json.dumps(spec["ends_with"])})) '
    head += ''.join(f'{this} <{r}> ?r{i} . ' for i, r in enumerate(spec['requires_iris']))
    head += ''.join(f'FILTER NOT EXISTS {{ {this} <{u}> ?u{i} }} ' for i, u in enumerate(spec['unless_iris']))
    if spec['separator'] is None and not ambiguous:
        return head + f'FILTER NOT EXISTS {{ {this} <{link}> ?t }} }}'
    if spec['separator'] is None:
        keys = '1'
    else:
        sep = json.dumps(spec['separator'])
        keys = f'(STRLEN(?value) - STRLEN(REPLACE(?value, {sep}, "", "q"))) / STRLEN({sep}) + 1'
    return (head + f'OPTIONAL {{ {this} <{link}> ?t }} }} GROUP BY {this} ?value '
            f'HAVING (COUNT(DISTINCT ?t) {">" if ambiguous else "<"} {keys})')


def link_shapes(specs):
    """One SHACL-SPARQL node shape per link, severity sh:Info, focus nodes by a SPARQL target."""
    g = Graph()
    g.bind('sh', SH)
    for spec in specs:
        for amb in ([False] if spec['unmatched'] == 'reported' else []) + ([True] if spec['targets'] == 'all' else []):
            base = spec['shape'] + ('-ambiguous' if amb else '')
            shape = URIRef(base)
            con = URIRef(base + '-sparql')
            target = URIRef(base + '-target')
            g.add((shape, RDF.type, SH.NodeShape))
            g.add((shape, SH.target, target))
            g.add((shape, SH.severity, SH.Info))
            g.add((target, RDF.type, SH.SPARQLTarget))
            g.add((target, SH.select, Literal(_sparql(spec, '?this', spec['domain_class'], amb))))
            g.add((shape, SH.sparql, con))
            g.add((con, RDF.type, SH.SPARQLConstraint))
            what = 'more target rows than keys' if amb else f'no {spec["kind"]} link'
            g.add((con, SH.message, Literal(f'{spec["name"]}: {what} for the value')))
            g.add((con, SH.select, Literal(_sparql(spec, ambiguous=amb))))
        if spec['flag']:
            base = spec['shape'] + '-flagged'
            shape, con, target = URIRef(base), URIRef(base + '-sparql'), URIRef(base + '-target')
            g.add((shape, RDF.type, SH.NodeShape))
            g.add((shape, SH.target, target))
            g.add((shape, SH.severity, SH.Info))
            g.add((target, RDF.type, SH.SPARQLTarget))
            g.add((target, SH.select, Literal(_flag_sparql(spec, '?this', spec['domain_class']))))
            g.add((shape, SH.sparql, con))
            g.add((con, RDF.type, SH.SPARQLConstraint))
            g.add((con, SH.message, Literal(f'{spec["name"]}: {flag_result(spec)}')))
            g.add((con, SH.select, Literal(_flag_sparql(spec))))
    return g


def flag_result(spec):
    return f'target {spec["flag"]["column"]} ends in {spec["flag"]["ends_with"]}'


def _flag_sparql(spec, this='$this', cls=None):
    end = json.dumps(spec['flag']['ends_with'])
    return (f'SELECT {this} ?value WHERE {{ ' + (f'{this} a <{cls}> . ' if cls else '')
            + f'{this} <{spec["column_iris"][-1]}> ?value . {this} <{spec["iri"]}> ?t . '
            f'?t <{spec["flag_iri"]}> ?n . FILTER(STRENDS(?n, {end})) }}')


def unresolved(g, spec, node, value):
    """The keys of a link column value on a node that have no link (for the Link_Check view):
    the value split at the separator, minus the target keys the node links to. In Link_Check they
    are joined with the separator."""
    if spec['separator'] is None:
        return [value]
    linked = {_values(g, t, spec['target_iris'])[-1] for t in g.objects(node, URIRef(spec['iri']))}
    return [t for t in _tokens(value, spec['separator']) if t not in linked]


def _has(cols, vals):
    """'Variable Name "X"', or 'Class "A", Dataset Name empty and Variable Name "B"'."""
    parts = [f'{c} "{v}"' if v != '' else f'{c} empty' for c, v in zip(cols, vals)]
    return parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]


def reason(g, spec, node, value, result):
    """One sentence for a Link_Check row: what was looked for in the target table and not found, or
    what the target carries. Made only from links.yaml and the row's published values; no value of ours."""
    rng = spec['range']
    if result == 'no link':
        vals = _values(g, node, spec['column_iris'])
        empty = ''.join(f' and an empty {c}' for c in spec['target_empty'])
        within = f' (one of the values of its {spec["target"][-1]}, split at "{spec["target_separator"]}")' if spec['target_separator'] else ''
        if spec['rule_function']:
            keys = RULE_FUNCTIONS[spec['rule_function']](g)(vals)
            if not keys:
                return f'The rule gives no key to look for in {rng} for {_has(spec["columns"], vals)}.'
            return f'No row of {rng} has ' + ', or '.join(_has(spec['target'], k) for k in keys) + f'{empty}{within}.'
        if spec['separator']:
            parts = unresolved(g, spec, node, value)
            last = ', '.join(f'"{x}"' for x in parts[:-1]) + (' or ' if len(parts) > 1 else '') + f'"{parts[-1]}"'
            head = _has(spec['target'][:-1], vals[:-1]) + ' and ' if len(vals) > 1 else ''
            return f'No row of {rng} has {head}{spec["target"][-1]} {last}{empty}{within}.'
        return f'No row of {rng} has {_has(spec["target"], vals)}{empty}{within}.'
    targets = sorted(g.objects(node, URIRef(spec['iri'])))
    if result == 'more target rows than keys':
        keys = sorted({tuple(_values(g, t, spec['target_iris'])) for t in targets})
        within = f', split at "{spec["target_separator"]}"' if spec['target_separator'] else ''
        return (f'{len(targets)} rows of {rng} match ({_has(spec["target"], keys[0]) if len(keys) == 1 else ", or ".join(_has(spec["target"], k) for k in keys)}'
                f'{within}); every one is linked.')
    marked = [_values(g, t, [spec['flag_iri']])[0] for t in targets]
    return f'The linked row of {rng} has {spec["flag"]["column"]} ' + ', '.join(f'"{m}"' for m in marked) + '; the link stays.'


LINK_CHECK_COLUMNS = ['Link', 'Kind', 'Result', 'Table', 'Row', 'Column', 'Value', 'Not resolved', 'Target table', 'Reason']
LINKS_SHEET_COLUMNS = ['Link', 'Property', 'Kind', 'Rule', 'Rule function', 'Table', 'Columns', 'Separator',
                       'Requires', 'Unless', 'Target table', 'Target columns', 'Target columns empty', 'Targets',
                       'Description', 'Flag', 'Ends with', 'Target separator', 'Not reported']


def link_check_frame(report, g, specs):
    """Link_Check as a table, from the SHACL validation report: one row per result (a row of a
    base table and the value of its link column that does not resolve, in full or in part).
    Stops on a result that is not sh:Info or not from a link shape."""
    import pandas as pd
    by_shape = {URIRef(s['shape']): (s, 'no link') for s in specs}
    by_shape.update({URIRef(s['shape'] + '-ambiguous'): (s, 'more target rows than keys')
                     for s in specs if s['targets'] == 'all'})
    by_shape.update({URIRef(s['shape'] + '-flagged'): (s, flag_result(s)) for s in specs if s['flag']})
    rows = []
    for r in report.subjects(RDF.type, SH.ValidationResult):
        if report.value(r, SH.resultSeverity) != SH.Info:
            raise ValueError(f'{r}: a result that is not sh:Info')
        if report.value(r, SH.sourceShape) not in by_shape:
            raise ValueError(f'{r}: not from a link shape')
        spec, result = by_shape[report.value(r, SH.sourceShape)]
        node = report.value(r, SH.focusNode)
        value = str(report.value(r, SH.value))
        rows.append([spec['name'], spec['kind'], result, spec['domain'], str(node), spec['columns'][-1], value,
                     spec['separator'].join(unresolved(g, spec, node, value)) if spec['separator'] and result == 'no link' else '',
                     spec['range'], reason(g, spec, node, value, result)])
    df = pd.DataFrame(rows, columns=LINK_CHECK_COLUMNS, dtype=str)
    return df.sort_values(['Link', 'Result', 'Row', 'Value'], kind='stable').reset_index(drop=True)


def links_sheet(specs):
    """The links contract as a sheet (from links.yaml): one row per link."""
    import pandas as pd
    js = lambda x: json.dumps(x, ensure_ascii=False) if x else ''
    rows = [[s['name'], s['iri'], s['kind'], s['rule'] or '', s['rule_function'] or '', s['domain'], js(s['columns']),
             s['separator'] or '', js(s['requires']), js(s['unless']), s['range'], js(s['target']),
             js(s['target_empty']), s['targets'], s['description'] or '', s['flag_rule'] or '',
             s['ends_with'] or '', s['target_separator'] or '', s['unmatched_rule'] or '']
            for s in specs]
    return pd.DataFrame(rows, columns=LINKS_SHEET_COLUMNS, dtype=str)


# --- Rule functions: from a row's column values, the target keys to try, in order.
# Each takes the base graphs and returns the function for one row. The rule each implements is
# stated in links.yaml (annotation rule); the function is that rule, nothing more.

SDTMIG_CLASS = 'https://kerfors.github.io/cdisc-for-all/def/sdtmig/SDTMIG#Class'
SDTMIG_DATASET = 'https://kerfors.github.io/cdisc-for-all/def/sdtmig/SDTMIG#Dataset%20Name'


def _model_keys(cls, dataset, variable):
    """SDTM Model keys (Class, Dataset Name, Variable Name) for a variable of a dataset of a class:
    the variable in that dataset of the class; else its general name (the dataset prefix replaced
    by "--", or the name itself if it does not start with the dataset name) among the variables
    the Model publishes for the class, then for General Observations, and for Findings About also
    for Findings."""
    general = '--' + variable[len(dataset):] if variable.startswith(dataset) and len(variable) > len(dataset) else variable
    keys = [(cls, dataset, variable), (cls, '', general), ('General Observations', '', general)]
    if cls == 'Findings About':
        keys.append(('Findings', '', general))
    return keys


def _sdtmig_model_variable(g):
    return lambda vals: _model_keys(*vals)


def _dataset_class(g):
    """The class the SDTMIG table gives each dataset. Stops if a dataset has more than one."""
    out = {}
    for s in g.subjects(URIRef(SDTMIG_DATASET), None):
        d = str(g.value(s, URIRef(SDTMIG_DATASET)))
        c = str(g.value(s, URIRef(SDTMIG_CLASS)))
        if out.setdefault(d, c) != c:
            raise ValueError(f'SDTMIG dataset {d}: classes {out[d]} and {c}')
    return out


def _cosmos_model_variable(g):
    classes = _dataset_class(g)

    def keys(vals):
        domain, variable = vals
        if domain in classes:
            return _model_keys(classes[domain], domain, variable)
        return [k for k in _model_keys('', domain, variable) if k[0] == 'General Observations']
    return keys


def _cosmos_nsv(g):
    def keys(vals):
        domain, variable = vals
        if variable.startswith(domain) and len(variable) > len(domain):
            return [(variable[len(domain):],)]
        return []
    return keys


def _cd_short_version(g):
    """SDTMIG 4.2.1: a variable whose name ends in "CD" is the short version of the variable
    without the "CD" suffix. The target key: the row's other key values, and its name without the
    final "CD"."""
    def keys(vals):
        *rest, variable = vals
        if variable.endswith('CD') and len(variable) > 2:
            return [tuple(rest) + (variable[:-2],)]
        return []
    return keys


def _model_name_fragment(g):
    """An SDTM Model Variable Name, with a leading "--" removed, as a fragment."""
    def keys(vals):
        variable = vals[-1]
        return [(variable[2:] if variable.startswith('--') else variable,)]
    return keys


RULE_FUNCTIONS = {
    'sdtmig-model-variable': _sdtmig_model_variable,
    'cosmos-model-variable': _cosmos_model_variable,
    'cosmos-nsv': _cosmos_nsv,
    'cd-short-version': _cd_short_version,
    'model-name-fragment': _model_name_fragment,
}
