"""The link map: one HTML page from schema/links.yaml and linked/link-check.ttl. The source
tables as boxes, each link as a line (solid: published key; dashed: by rule); a click on a line
shows the link as stated (key columns, target columns, rule) and its Link_Check results. A view of
the stated links and the published report (the SHACL validation report); it adds nothing.

    python examples/link_map.py
    python examples/link_map.py --out examples/pages/link_map.html"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402
from rdflib import RDF, Graph, URIRef  # noqa: E402

from cfa.link import SH, flag_result, load_links  # noqa: E402

LINKS = REPO_ROOT / 'schema' / 'links.yaml'
CHECK = REPO_ROOT / 'linked' / 'link-check.ttl'
SIGNIN = {'sdtmig', 'sdtm-model', 'sdtmig-fragments'}
SOURCE_NAMES = {'sdtm-ct': 'SDTM CT', 'ncit-flat': 'NCIt', 'nci-code-cui-map': 'NCIt code-CUI map', 'cosmos': 'COSMoS',
                'sdtmig': 'SDTMIG v3.4', 'sdtm-model': 'SDTM v2.0', 'nsv-registry': 'NSV Registry',
                'sdtmig-fragments': 'SDTMIG v3.4 Appendix D'}
# box positions (x, y) on the map, by table; a layout choice for reading, nothing more
POSITIONS = {'Approved NSVs-alpha': (16, 30), 'SDTMIG': (16, 230), 'SDTM': (16, 430),
             'cdisc_sdtm_dataset_specializations_latest': (276, 230), 'CDISC Variable-naming Fragments': (276, 430),
             'cdisc_biomedical_concepts_hierarchy_latest': (536, 60), 'cdisc_biomedical_concepts_latest': (536, 260),
             'SDTM Terminology': (536, 460), 'Thesaurus': (796, 260), 'nci_code_cui_map': (796, 460)}


def check_table(specs):
    """The results of link-check.ttl as a table: Link and Result from sh:sourceShape (the shape of
    a link, its -ambiguous or its -flagged shape), Row sh:focusNode, Column the link column as
    published, Value sh:value. Sorted as Link_Check.xlsx is."""
    by_shape = {URIRef(s['shape']): (s, 'no link') for s in specs}
    by_shape.update({URIRef(s['shape'] + '-ambiguous'): (s, 'more target rows than keys') for s in specs if s['targets'] == 'all'})
    by_shape.update({URIRef(s['shape'] + '-flagged'): (s, flag_result(s)) for s in specs if s['flag']})
    g = Graph().parse(CHECK)
    rows = []
    for r in g.subjects(RDF.type, SH.ValidationResult):
        shape = g.value(r, SH.sourceShape)
        if shape not in by_shape:
            raise ValueError(f'{r}: not from a link shape in links.yaml')
        spec, result = by_shape[shape]
        rows.append([spec['name'], result, str(g.value(r, SH.focusNode)), spec['columns'][-1], str(g.value(r, SH.value))])
    df = pd.DataFrame(rows, columns=['Link', 'Result', 'Row', 'Column', 'Value'], dtype=str)
    return df.sort_values(['Link', 'Result', 'Row', 'Value'], kind='stable').reset_index(drop=True)


def page_data():
    specs = load_links(LINKS)
    check = check_table(specs)
    tables = {}
    for s in specs:
        for src, table in ((s['domain_source'], s['domain']), (s['range_source'], s['range'])):
            if table not in POSITIONS:
                raise ValueError(f'no position for table {table}')
            tables[table] = {'source': src, 'source_name': SOURCE_NAMES[src], 'signin': src in SIGNIN, 'xy': POSITIONS[table]}
    links = []
    for s in specs:
        rows = check[check['Link'] == s['name']]
        links.append({
            'name': s['name'], 'kind': s['kind'], 'description': s['description'], 'iri': s['iri'],
            'from': s['domain'], 'to': s['range'], 'columns': s['columns'], 'target': s['target'],
            'separator': s['separator'], 'rule': s['rule'], 'flag_rule': s['flag_rule'],
            'ends_with': s['ends_with'], 'target_separator': s['target_separator'], 'unmatched_rule': s['unmatched_rule'],
            'signin': bool({s['domain_source'], s['range_source']} & SIGNIN),
            'check': rows[['Result', 'Row', 'Column', 'Value']].values.tolist(),
        })
    return {'tables': tables, 'links': links}


def write_page(path):
    data = page_data()
    template = (Path(__file__).parent / 'link_map.html').read_text(encoding='utf-8')
    html = template.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    Path(path).write_text(html, encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description='The link map: links.yaml and Link_Check as one page.')
    parser.add_argument('--out', type=Path, default=REPO_ROOT / 'examples' / 'output' / 'link_map.html')
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = write_page(args.out)
    print(f"{len(data['links'])} links, {len(data['tables'])} tables -> {args.out}")


if __name__ == '__main__':
    main()
