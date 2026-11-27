"""The COSMoS authored model in linked (schema/cosmos_model.yaml).

The model graph is built from the COSMoS base tables only (rebuilt from the base graph), with
the classes and slots of COSMoS's pinned LinkML model files: class and slot IRIs as LinkML
expands them (SchemaView.get_uri), every value the base cell as published (a plain literal).

- load_model_map: the mapping, checked against the model files and the base module
- model_graph:    the graph; stops if a single-valued slot of a node would get two values, or a
                  row node is not in the base graph
- flatten:        the base tables rebuilt from the model graph (the reverse check)
- repeated_parts: the cells of a split column that repeat a part (RDF keeps a part once)
"""

import re

import pandas as pd
import yaml
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import RDF, Graph, Literal, URIRef

from cfa import NS
from cfa.rule import columns, pct
from cfa.view import sort_by_key

TEMPLATE_VAR = re.compile(r'\{([^}]*)\}')
ID_PREFIX = f'{NS}id/cosmos/'


def model_graph_iri():
    return f'{NS}graph/cosmos-model'


def _slot_spec(value):
    """A slot entry as {'column': c, 'split': bool} or {'object': Class}."""
    if isinstance(value, str):
        return {'column': value, 'split': False}
    if set(value) == {'object'}:
        return dict(value)
    if set(value) == {'column', 'split'} and value['split'] is True:
        return dict(value)
    raise ValueError(f'slot entry not understood: {value!r}')


def load_model_map(path, model_paths, base_sv):
    """The mapping with each class's and slot's IRI from the model files. model_paths:
    {model key: path of the pinned model file}. Stops on: a class or slot that is not in the
    model, a split on a single-valued slot (or no split on a multivalued value slot), an object
    slot whose range is not the class named, a column that is not in the base table, a template
    over an unknown column or class."""
    m = yaml.safe_load(path.read_text(encoding='utf-8'))
    if set(m['model_files']) != set(model_paths):
        raise ValueError(f'model files {sorted(model_paths)} differ from the mapping {sorted(m["model_files"])}')
    views = {k: SchemaView(str(p)) for k, p in model_paths.items()}
    classes = {}
    for name, c in m['classes'].items():
        sv = views[c['model']]
        cd = sv.get_class(name)
        if cd is None:
            raise ValueError(f'{name}: not a class of the {c["model"]} model')
        cols = columns(base_sv, c['table'])
        induced = set(sv.class_slots(name))
        slots = {}
        for slot, value in c['slots'].items():
            spec = _slot_spec(value)
            if slot not in induced:
                raise ValueError(f'{name}.{slot}: not a slot of the class in the model')
            sd = sv.induced_slot(slot, name)
            if 'object' in spec:
                if sd.range != spec['object']:
                    raise ValueError(f'{name}.{slot}: range {sd.range}, mapping says {spec["object"]}')
                spec['multivalued'] = bool(sd.multivalued)
            else:
                if spec['column'] not in cols:
                    raise ValueError(f'{name}.{slot}: {spec["column"]!r} is not a column of {c["table"]}')
                if bool(sd.multivalued) != spec['split'] and not c.get('split_by_position'):
                    raise ValueError(f'{name}.{slot}: multivalued={sd.multivalued}, split={spec["split"]}')
            spec['iri'] = URIRef(sv.get_uri(sd, expand=True))
            slots[slot] = spec
        for col in c.get('when', []):
            if col not in cols:
                raise ValueError(f'{name}: when column {col!r} is not a column of {c["table"]}')
        classes[name] = {**c, 'iri': URIRef(sv.get_uri(cd, expand=True)), 'slots': slots,
                         'when': c.get('when', []), 'row': c.get('row', False),
                         'split_by_position': c.get('split_by_position', False)}
    for name, c in classes.items():
        for var in TEMPLATE_VAR.findall(c['node']):
            if var != 'n' and var not in classes and var not in columns(base_sv, c['table']):
                raise ValueError(f'{name}: node template variable {var!r} unknown')
        for slot, spec in c['slots'].items():
            if 'object' in spec and spec['object'] not in classes:
                raise ValueError(f'{name}.{slot}: class {spec["object"]} is not mapped')
    return {'separator': m['separator'], 'model_files': m['model_files'], 'classes': classes}


def _parts(value, sep):
    return value.split(sep) if value != '' else []


def _nodes(mm, name, row, cache):
    """The nodes of a class for one row: [] if its 'when' columns are all empty; for
    split_by_position, one node per position."""
    key = name
    if key in cache:
        return cache[key]
    c = mm['classes'][name]
    if c['when'] and all(row[col] == '' for col in c['when']):
        cache[key] = []
        return []
    count = 1
    if c['split_by_position']:
        counts = {len(_parts(row[s['column']], mm['separator'])) for s in c['slots'].values()
                  if 'column' in s and row[s['column']] != ''}
        if len(counts) != 1:
            raise ValueError(f'{name}: the columns split into different numbers of parts: {counts}')
        count = counts.pop()

    def expand(n):
        def one(match):
            var = match.group(1)
            if var == 'n':
                return str(n)
            if var in mm['classes']:
                parent = _nodes(mm, var, row, cache)
                if len(parent) != 1:
                    raise ValueError(f'{name}: the {var} node of the row is not one node')
                return str(parent[0])[len(ID_PREFIX):]
            if row[var] == '':
                raise ValueError(f'{name}: empty {var} in the node template')
            return pct(row[var])
        return URIRef(ID_PREFIX + TEMPLATE_VAR.sub(one, c['node']))

    nodes = [expand(n) for n in range(1, count + 1)]
    cache[key] = nodes
    return nodes


def model_graph(mm, frames, base_rows):
    """The model graph. frames: {table: the base table as text}; base_rows: the set of row
    nodes of the base graph."""
    g = Graph()
    single = {}
    sep = mm['separator']
    for name, c in mm['classes'].items():
        df = frames[c['table']]
        for rec in df.to_dict('records'):
            cache = {}
            nodes = _nodes(mm, name, rec, cache)
            for i, node in enumerate(nodes):
                if c['row'] and node not in base_rows:
                    raise ValueError(f'{name}: {node} is not a row node of the base graph')
                g.add((node, RDF.type, c['iri']))
                for slot, spec in c['slots'].items():
                    if 'object' in spec:
                        for child in _nodes(mm, spec['object'], rec, cache):
                            g.add((node, spec['iri'], child))
                        continue
                    value = rec[spec['column']]
                    if value == '':
                        continue
                    if c['split_by_position']:
                        value = _parts(value, sep)[i]
                    if spec['split']:
                        for part in _parts(value, sep):
                            g.add((node, spec['iri'], Literal(part)))
                        continue
                    seen = single.setdefault((node, spec['iri']), value)
                    if seen != value:
                        raise ValueError(f'{node} {slot}: two values {seen!r} and {value!r}')
                    g.add((node, spec['iri'], Literal(value)))
    return g


def _roots(mm):
    children = {s['object'] for c in mm['classes'].values() for s in c['slots'].values() if 'object' in s}
    return [name for name in mm['classes'] if name not in children]


def flatten(mm, g, table):
    """The table rebuilt from the model graph: from each root node of a class on that table,
    its value slots, its single objects (and positional ones, joined at the separator in
    position order) merged in, and one row per child of a multivalued object (one row with
    that child's columns empty if it has none). A split column's parts are joined in sorted
    order, as RDF keeps no order."""
    sep = mm['separator']

    def cells(name, node):
        c = mm['classes'][name]
        out = {}
        for slot, spec in c['slots'].items():
            if 'column' in spec:
                values = sorted(str(o) for o in g.objects(node, spec['iri']))
                if len(values) > 1 and not spec['split']:
                    raise ValueError(f'{node} {slot}: more than one value')
                out[spec['column']] = sep.join(values)
        return out

    def rows(name, node):
        c = mm['classes'][name]
        base = cells(name, node)
        expand = []
        for slot, spec in c['slots'].items():
            if 'object' not in spec:
                continue
            kids = sorted(g.objects(node, spec['iri']))
            child = mm['classes'][spec['object']]
            if child['split_by_position']:
                kids = sorted(kids, key=lambda k: int(str(k).rsplit('/', 1)[1]))
                merged = {}
                for k in kids:
                    for col, v in cells(spec['object'], k).items():
                        merged.setdefault(col, []).append(v)
                for s in child['slots'].values():
                    base[s['column']] = sep.join(merged.get(s['column'], []))
            elif spec['multivalued']:
                expand.append((spec['object'], kids))
            else:
                if len(kids) > 1:
                    raise ValueError(f'{node} {slot}: more than one object')
                if kids:
                    base.update(cells(spec['object'], kids[0]))
                else:
                    base.update({s['column']: '' for s in child['slots'].values() if 'column' in s})
        out = [base]
        for child_name, kids in expand:
            empty = {s['column']: '' for s in mm['classes'][child_name]['slots'].values() if 'column' in s}
            new = []
            for r in out:
                if not kids:
                    new.append({**r, **empty})
                for k in kids:
                    for kr in rows(child_name, k):
                        new.append({**r, **kr})
            out = new
        return out

    result = []
    for name in _roots(mm):
        if mm['classes'][name]['table'] != table:
            continue
        for node in sorted(g.subjects(RDF.type, mm['classes'][name]['iri'])):
            result.extend(rows(name, node))
    return pd.DataFrame(result, dtype=str)


def split_columns(mm, table):
    return sorted({s['column'] for c in mm['classes'].values() if c['table'] == table
                   for s in c['slots'].values() if s.get('split')})


def as_sets(df, cols, sep):
    """The table with each cell of the split columns as its distinct parts, sorted."""
    df = df.copy()
    for col in cols:
        df[col] = df[col].map(lambda v: sep.join(sorted(set(v.split(sep)))) if v != '' else '')
    return df


def repeated_parts(mm, frames, keys):
    """Rows of a split column whose cell repeats a part: Table, key columns as one text, Column, Value."""
    out = []
    sep = mm['separator']
    for table, df in frames.items():
        for col in split_columns(mm, table):
            for rec in df.to_dict('records'):
                parts = _parts(rec[col], sep)
                if len(parts) != len(set(parts)):
                    out.append({'Table': table, 'Row': ' / '.join(rec[k] for k in keys[table]),
                                'Column': col, 'Value': rec[col]})
    return pd.DataFrame(out, columns=['Table', 'Row', 'Column', 'Value'], dtype=str)


def compare(rebuilt, base, keys, split_cols, sep):
    """Rows and cells where the rebuilt table differs from the base table (split columns as sets)."""
    cols = list(rebuilt.columns)
    if sorted(cols) != sorted(base.columns):
        return {'columns': sorted(set(cols) ^ set(base.columns))}
    a = sort_by_key(as_sets(rebuilt[cols], split_cols, sep), keys)
    b = sort_by_key(as_sets(base[cols], split_cols, sep), keys)
    if len(a) != len(b):
        return {'rows': (len(a), len(b))}
    diff = (a != b)
    return {col: int(diff[col].sum()) for col in cols if diff[col].any()}
