"""The Excel view of a base graph, the text hash, the Schema sheet.

A view sheet is the table rebuilt from the graph: the columns in published order, one row
per node, sorted by the key, every cell written as a text cell (text that looks like an OOXML
escape is escaped, so reading back with cfa.read decodes it to the same text).

Text hash: SHA-256 (UTF-8) of the JSON array [header, row, ...] (each an array of strings,
an empty cell ""), rows sorted by the key columns in code point order, serialised with
json.dumps(ensure_ascii=False, separators=(',', ':')). JSON keeps cells apart even where a
cell holds a tab or a line break.
"""

import hashlib
import json

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from rdflib import Literal, URIRef
from rdflib.namespace import RDF

from cfa.read import encode_ooxml
from cfa.rule import class_iri, columns, key_columns, module_source, property_iri

HEADER_FONT = Font(name='Calibri', size=10, bold=True)
DATA_FONT = Font(name='Calibri', size=10)
GREY = PatternFill('solid', fgColor='D9D9D9')
EXCEL_CELL_LIMIT = 32767
EXCEL_SHEET_NAME_LIMIT = 31

TEXT_HASH_METHOD = ('SHA-256 (UTF-8) of the JSON array [header, row, ...], each an array of '
                    'strings (empty cell ""), rows sorted by the key columns in code point order, '
                    'json.dumps(ensure_ascii=False, separators=(",", ":")).')


def sort_by_key(df, keys):
    order = sorted(range(len(df)), key=lambda i: tuple(df[k].iat[i] for k in keys))
    return df.iloc[order].reset_index(drop=True)


def text_sha256(df, keys):
    df = sort_by_key(df, keys)
    rows = [list(df.columns)] + [list(r) for r in df.itertuples(index=False, name=None)]
    for r in rows:
        if not all(isinstance(v, str) for v in r):
            raise TypeError('a cell that is not a str')
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def view_frame(g, sv, table):
    """The table rebuilt from the graph, sorted by key. Stops on a property of the class's
    nodes that is not a column, or a column with more than one value on a node."""
    source = module_source(sv)
    cols = columns(sv, table)
    prop_col = {URIRef(property_iri(source, table, c)): c for c in cols}
    rows = []
    for s in sorted(g.subjects(RDF.type, URIRef(class_iri(source, table)))):
        row = dict.fromkeys(cols, '')
        for p, o in g.predicate_objects(s):
            if p == RDF.type:
                continue
            if p not in prop_col or not isinstance(o, Literal):
                raise ValueError(f'{s}: {p} {o!r} is not a column literal')
            if row[prop_col[p]] != '':
                raise ValueError(f'{s}: more than one value for {prop_col[p]}')
            row[prop_col[p]] = str(o)
        rows.append([row[c] for c in cols])
    return sort_by_key(pd.DataFrame(rows, columns=cols, dtype=str), key_columns(sv, table))


def schema_sheet(sv, tables):
    """The Schema sheet of a base view: per column its property IRI and whether it is part of
    the row key. Nothing descriptive of ours."""
    source = module_source(sv)
    rows = []
    for table in tables:
        keys = key_columns(sv, table)
        for c in columns(sv, table):
            rows.append({'Sheet': table, 'Column': c, 'Property': property_iri(source, table, c),
                         'Identifies_Row': 'Yes' if c in keys else 'No'})
    return pd.DataFrame(rows, columns=['Sheet', 'Column', 'Property', 'Identifies_Row'], dtype=str)


def _write_sheet(ws, df):
    for ci, head in enumerate(df.columns, 1):
        cell = ws.cell(row=1, column=ci, value=encode_ooxml(head))
        cell.data_type = 's'
        cell.font = HEADER_FONT
        cell.fill = GREY
    for ri, row in enumerate(df.itertuples(index=False, name=None), 2):
        for ci, value in enumerate(row, 1):
            if value != '':
                cell = ws.cell(row=ri, column=ci, value=encode_ooxml(value))
                cell.data_type = 's'
                cell.font = DATA_FONT
    ws.freeze_panes = 'A2'


def write_view(path, readme_lines, sheets, schema_df, provenance):
    """ReadMe, the table sheets ({name: DataFrame of str}), Schema, Provenance (a flat
    {key: str} dict). Stops on a non-str cell, a cell over the Excel limit, a long sheet name."""
    prov_df = pd.DataFrame(list(provenance.items()), columns=['Key', 'Value'], dtype=str)
    all_sheets = {**sheets, 'Schema': schema_df, 'Provenance': prov_df}
    for name, df in all_sheets.items():
        if len(name) > EXCEL_SHEET_NAME_LIMIT:
            raise ValueError(f'sheet name over {EXCEL_SHEET_NAME_LIMIT} characters: {name}')
        for col in df.columns:
            if not all(isinstance(v, str) for v in df[col]):
                raise TypeError(f'{name}.{col}: not every cell is a str')
            if (df[col].str.len() > EXCEL_CELL_LIMIT).any():
                raise ValueError(f'{name}.{col}: a cell over {EXCEL_CELL_LIMIT} characters')
    wb = Workbook()
    ws = wb.active
    ws.title = 'ReadMe'
    for ri, line in enumerate(readme_lines, 1):
        cell = ws.cell(row=ri, column=1, value=line)
        cell.data_type = 's'
        cell.font = DATA_FONT
    ws.column_dimensions['A'].width = 120
    for name, df in all_sheets.items():
        _write_sheet(wb.create_sheet(name), df)
    wb.save(path)
