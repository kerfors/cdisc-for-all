"""The link map: one HTML page from schema/links.yaml and linked/Link_Check.xlsx. The source
tables as boxes, each link as a line (solid: published key; dashed: by rule); a click on a line
shows the link as stated (key columns, target columns, rule) and its Link_Check rows. A view of
the stated links and the published report; it adds nothing.

    python examples/link_map.py
    python examples/link_map.py --out examples/pages/link_map.html"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cfa.link import load_links  # noqa: E402
from cfa.read import read_xlsx_table  # noqa: E402

LINKS = REPO_ROOT / 'schema' / 'links.yaml'
CHECK = REPO_ROOT / 'linked' / 'Link_Check.xlsx'
SIGNIN = {'sdtmig', 'sdtm-model'}
SOURCE_NAMES = {'sdtm-ct': 'SDTM CT', 'ncit-flat': 'NCIt', 'nci-code-cui-map': 'NCIt code-CUI map', 'cosmos': 'COSMoS',
                'sdtmig': 'SDTMIG v3.4', 'sdtm-model': 'SDTM v2.0', 'nsv-registry': 'NSV Registry'}
# box positions (x, y) on the map, by table; a layout choice for reading, nothing more
POSITIONS = {'Approved NSVs-alpha': (16, 30), 'SDTMIG': (16, 230), 'SDTM': (16, 430),
             'cdisc_sdtm_dataset_specializations_latest': (276, 230),
             'cdisc_biomedical_concepts_hierarchy_latest': (536, 60), 'cdisc_biomedical_concepts_latest': (536, 260),
             'SDTM Terminology': (536, 460), 'Thesaurus': (796, 260), 'nci_code_cui_map': (796, 460)}


def page_data():
    specs = load_links(LINKS)
    check = read_xlsx_table(CHECK, 'Link_Check')
    tables = {}
    for s in specs:
        for src, table in ((s['domain_source'], s['domain']), (s['range_source'], s['range'])):
            if table not in POSITIONS:
                raise ValueError(f'no position for table {table}')
            tables[table] = {'source': src, 'source_name': SOURCE_NAMES[src], 'signin': src in SIGNIN, 'xy': POSITIONS[table]}
    names = {s['name'] for s in specs}
    unknown = set(check['Link']) - names
    if unknown:
        raise ValueError(f'Link_Check links not in links.yaml: {sorted(unknown)}')
    links = []
    for s in specs:
        rows = check[check['Link'] == s['name']]
        links.append({
            'name': s['name'], 'kind': s['kind'], 'description': s['description'], 'iri': s['iri'],
            'from': s['domain'], 'to': s['range'], 'columns': s['columns'], 'target': s['target'],
            'separator': s['separator'], 'rule': s['rule'], 'flag_rule': s['flag_rule'],
            'signin': bool({s['domain_source'], s['range_source']} & SIGNIN),
            'check': rows[['Result', 'Row', 'Column', 'Value', 'Not resolved']].values.tolist(),
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
