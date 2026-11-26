"""The base mapping rule, stated as W3C CSVW metadata (decided 2026-11-26, option A).

The LinkML module of a source is the one hand-kept description. csvw_metadata() generates
from it one CSVW table description per source table; table_to_graph() is our implementation
of CSVW minimal-mode conversion ("Generating RDF from Tabular Data on the Web") for the
subset used here. The checks convert the same table with rdf-tabular (the reference
implementation) and compare the graphs.

The subset: every column a string; aboutUrl from the key columns (RFC 6570 simple expansion,
so an empty key component gives an empty path segment); a literal propertyUrl per column;
null "" (the default: an empty cell gives no triple); no separator (a multi-valued cell is
one literal); trim false (surrounding whitespace is kept); one virtual column for rdf:type.
A class annotation aboutUrl replaces the row IRI template (NCIt rows keep NCI's IRI); a class
annotation dialect (JSON) adds CSVW dialect properties.

For an xlsx source, CSVW describes the table as cfa.read.read_xlsx_table reads it (CSVW
defines parsing for CSV/TSV only); its url is then '<table>.csv'.
"""

import json
import re
from urllib.parse import quote

from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph, Literal, URIRef

from cfa import NS

CSVW_CONTEXT = 'http://www.w3.org/ns/csvw'
RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
TEMPLATE_VAR = re.compile(r'\{([^}]*)\}')


def pct(text):
    """Percent-encode everything but the RFC 3986 unreserved characters (as RFC 6570 simple
    expansion does)."""
    return quote(text, safe='')


def class_iri(source, table):
    return f'{NS}def/{source}#{pct(table)}'


def property_iri(source, table, column):
    return f'{NS}def/{source}/{pct(table)}#{pct(column)}'


def row_iri_prefix(source, table):
    return f'{NS}id/{source}/{pct(table)}/'


def graph_iri(source):
    return f'{NS}graph/{source}'


def csvw_name(column):
    """A CSVW column name for a header: the header percent-encoded so that it is an RFC 6570
    varname ('-', '.', '~' encoded too). Reversible."""
    if column.startswith('_'):
        raise ValueError(f'{column!r}: CSVW reserves names starting with "_"')
    return pct(column).replace('-', '%2D').replace('.', '%2E').replace('~', '%7E')


def load_module(path):
    return SchemaView(str(path))


def module_source(sv):
    return sv.schema.annotations['source'].value


def key_columns(sv, table):
    keys = sv.get_class(table).unique_keys
    if list(keys) != ['row_key']:
        raise ValueError(f'{table}: expected exactly one unique key, row_key; found {list(keys)}')
    return list(keys['row_key'].unique_key_slots)


def columns(sv, table):
    return list(sv.get_class(table).attributes)


def check_module(sv):
    """Every class_uri and slot_uri is the one the mapping rule gives; every key column is a
    column. Stops on the first difference."""
    source = module_source(sv)
    for table in sv.all_classes():
        cls = sv.get_class(table)
        if cls.class_uri != class_iri(source, table):
            raise ValueError(f'{table}: class_uri {cls.class_uri} is not {class_iri(source, table)}')
        for column, att in cls.attributes.items():
            if att.slot_uri != property_iri(source, table, column):
                raise ValueError(f'{table}.{column}: slot_uri {att.slot_uri} is not the rule IRI')
            if att.range not in (None, 'string') or att.multivalued:
                raise ValueError(f'{table}.{column}: a base column is a single string')
        missing = [k for k in key_columns(sv, table) if k not in cls.attributes]
        if missing:
            raise ValueError(f'{table}: key columns not among the columns: {missing}')
    return True


def csvw_metadata(sv, table, url):
    """The CSVW table description of one source table, generated from its LinkML class."""
    source = module_source(sv)
    cls = sv.get_class(table)
    ann = {k: v.value for k, v in (cls.annotations or {}).items()}
    dialect = {'trim': False}
    for k in ('delimiter', 'quoteChar', 'skipRows', 'header'):
        if k in ann:
            dialect[k] = ann[k]
    if 'dialect' in ann:
        dialect.update(json.loads(ann['dialect']))
    cols = [{'titles': c, 'name': csvw_name(c), 'propertyUrl': property_iri(source, table, c)}
            for c in columns(sv, table)]
    cols.append({'virtual': True, 'propertyUrl': RDF_TYPE, 'valueUrl': class_iri(source, table)})
    keys = key_columns(sv, table)
    about = row_iri_prefix(source, table) + '/'.join('{' + csvw_name(k) + '}' for k in keys)
    if 'aboutUrl' in ann:
        about = ann['aboutUrl']
    return {
        '@context': CSVW_CONTEXT,
        'url': url,
        'dialect': dialect,
        'tableSchema': {
            'columns': cols,
            'primaryKey': [csvw_name(k) for k in keys],
            'aboutUrl': about,
        },
    }


SUPPORTED = {
    'meta': {'@context', 'url', 'dialect', 'tableSchema'},
    'tableSchema': {'columns', 'primaryKey', 'aboutUrl'},
    'column': {'titles', 'name', 'propertyUrl'},
    'virtual': {'virtual', 'propertyUrl', 'valueUrl'},
}


def _expand(template, values):
    def one(m):
        var = m.group(1)
        if var[:1] in '+#./;?&':
            raise ValueError(f'{template}: only simple expansion is supported')
        value = values[var]
        return '' if value == '' else pct(value)
    return TEMPLATE_VAR.sub(one, template)


def table_to_graph(meta, df):
    """CSVW minimal mode for the subset above: one node per row (aboutUrl), its rdf:type, and
    one plain literal per non-empty cell. Stops on: a feature outside the subset, a header
    that differs from the column titles, two rows with the same node."""
    if set(meta) - SUPPORTED['meta'] or meta['dialect'].get('trim') is not False:
        raise ValueError('CSVW metadata outside the supported subset (or trim not false)')
    ts = meta['tableSchema']
    if set(ts) - SUPPORTED['tableSchema']:
        raise ValueError(f'tableSchema keys outside the subset: {sorted(set(ts) - SUPPORTED["tableSchema"])}')
    cols = [c for c in ts['columns'] if not c.get('virtual')]
    virtual = [c for c in ts['columns'] if c.get('virtual')]
    for c in cols:
        if set(c) - SUPPORTED['column']:
            raise ValueError(f'{c["titles"]}: column keys outside the subset')
    for c in virtual:
        if set(c) - SUPPORTED['virtual']:
            raise ValueError('virtual column keys outside the subset')
    titles = [c['titles'] for c in cols]
    if titles != list(df.columns):
        raise ValueError(f'header differs from the CSVW titles:\n  table {list(df.columns)}\n  CSVW  {titles}')
    names = [c['name'] for c in cols]
    props = [URIRef(c['propertyUrl']) for c in cols]
    g = Graph()
    seen = {}
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        s = URIRef(_expand(ts['aboutUrl'], dict(zip(names, row))))
        if s in seen:
            raise ValueError(f'rows {seen[s]} and {i}: the same node {s}')
        seen[s] = i
        for c in virtual:
            g.add((s, URIRef(c['propertyUrl']), URIRef(c['valueUrl'])))
        for p, v in zip(props, row):
            if v != '':
                g.add((s, p, Literal(v)))
    return g
