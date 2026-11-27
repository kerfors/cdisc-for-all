"""SSSOM mapping sets for the links by rule whose rule matches a general name (rule functions
in cfa.link). One row per link triple; the predicate and the comment say which part of the
rule matched. The rule itself is stated in schema/links.yaml; this module only reports it."""
import csv

import yaml

SKOS = 'http://www.w3.org/2004/02/skos/core#'
SEMAPV = 'https://w3id.org/semapv/vocab/'
COLUMNS = ['subject_id', 'predicate_id', 'object_id', 'mapping_justification', 'comment']


def branch(rule_function, vals, key):
    """The predicate (skos local name) and the comment for one link triple, from the row's column
    values and the target key that matched."""
    if rule_function in ('sdtmig-model-variable', 'cosmos-model-variable'):
        variable = vals[-1]
        cls, dataset, name = key
        if dataset:
            return 'exactMatch', f'Model row with the same Class ({cls}), Dataset Name ({dataset}) and Variable Name ({name})'
        if name == variable:
            return 'exactMatch', f'Variable Name {name} (it does not start with the Dataset Name) among the variables the Model publishes for Class {cls}'
        return 'broadMatch', f'general name {name} (for {variable}) among the variables the Model publishes for Class {cls}'
    if rule_function == 'cosmos-nsv':
        domain, variable = vals
        return 'broadMatch', f'sdtm_variable {variable} with the domain prefix {domain} removed equals the registry Variable Name {key[0]}'
    raise ValueError(f'no SSSOM branch for rule function {rule_function!r}')


def curie(iri, prefixes):
    """The CURIE of iri under the longest matching prefix. Stops if none matches."""
    best = max((p for p, ns in prefixes.items() if iri.startswith(ns)), key=lambda p: len(prefixes[p]), default=None)
    if best is None:
        raise ValueError(f'no prefix for {iri}')
    return f'{best}:{iri[len(prefixes[best]):]}'


def expand(c, prefixes):
    p, local = c.split(':', 1)
    return prefixes[p] + local


def mapping_rows(specs_matched, prefixes):
    """specs_matched: list of (spec, matched) with matched from make_links. The rows, sorted."""
    rows = []
    for spec, matched in specs_matched:
        for (s, t), (vals, key) in matched.items():
            pred, comment = branch(spec['rule_function'], vals, key)
            rows.append({'subject_id': curie(str(s), prefixes), 'predicate_id': f'skos:{pred}',
                         'object_id': curie(str(t), prefixes), 'mapping_justification': 'semapv:LexicalMatching',
                         'comment': f"{spec['name']}: {comment}"})
    return sorted(rows, key=lambda r: (r['subject_id'], r['object_id']))


def write_sssom(path, rows, metadata):
    """SSSOM TSV: the metadata as YAML in lines starting with "#", then the table."""
    header = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True, width=10000)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        for line in header.rstrip('\n').split('\n'):
            f.write('#' + line + '\n')
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


def read_sssom(path):
    """The metadata and the rows of an SSSOM TSV written by write_sssom."""
    with open(path, encoding='utf-8', newline='') as f:
        lines = f.read().split('\n')
    meta = yaml.safe_load('\n'.join(l[1:] for l in lines if l.startswith('#')))
    body = [l for l in lines if l and not l.startswith('#')]
    return meta, list(csv.DictReader(body, delimiter='\t'))
