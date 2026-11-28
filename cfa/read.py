"""Tables as text. A table is a pandas DataFrame of str: the header as columns, every cell a
str, an empty cell ''. Nothing is converted, trimmed or read as missing."""

import csv
import io
import re

import pandas as pd
import pdfplumber
from openpyxl import load_workbook

OOXML_ESCAPE = re.compile(r'_x([0-9A-Fa-f]{4})_')


def decode_ooxml(text):
    """Decode the OOXML string escape _xHHHH_ (ECMA-376): how the xlsx container stores
    characters such as CR. One pass, so a stored _x005F_x000D_ gives the text _x000D_."""
    return OOXML_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text)


def encode_ooxml(text):
    """The inverse for writing: escape the '_' of every text that looks like an escape, so
    decode_ooxml(encode_ooxml(t)) == t. openpyxl writes text as given and does not do this."""
    return OOXML_ESCAPE.sub(lambda m: '_x005F' + m.group(0), text)


def read_xlsx_table(path, sheet, skip_rows=0):
    """One sheet as a text table. skip_rows: rows above the header. The header is the run of
    non-empty cells from column A. Stops on: a cell that is not text, a value outside the
    header's columns, an empty row inside the table. Empty rows after the last row are not
    part of the table."""
    ws = load_workbook(path, read_only=True)[sheet]
    rows = ws.iter_rows(min_row=skip_rows + 1, values_only=True)
    first = next(rows)
    width = next((i for i, v in enumerate(first) if v is None), len(first))
    header = [decode_ooxml(v) for v in first[:width]]
    body = []
    for ri, row in enumerate(rows, skip_rows + 2):
        for ci, v in enumerate(row):
            if v is not None and not isinstance(v, str):
                raise TypeError(f'{sheet} row {ri} column {ci + 1}: {type(v).__name__} cell, not text')
            if v is not None and ci >= width:
                raise ValueError(f'{sheet} row {ri} column {ci + 1}: value outside the header')
        body.append((ri, ['' if v is None else decode_ooxml(v) for v in row[:width]]))
    while body and all(v == '' for v in body[-1][1]):
        body.pop()
    empty = [ri for ri, cells in body if all(v == '' for v in cells)]
    if empty:
        raise ValueError(f'{sheet}: empty rows inside the table: {empty[:10]}')
    return pd.DataFrame([cells for _, cells in body], columns=header, dtype=str)


def read_csv_table(path):
    """A comma-separated file, RFC 4180 quoting, UTF-8. A quoted "" and an unquoted empty
    value both give '' (as CSVW parsing does)."""
    with open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    return _frame(path, rows)


def read_tsv_table(path):
    """A tab-separated file with a header row, without quote handling (quoting=3), UTF-8."""
    with open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
    return _frame(path, rows)


def read_delimited_text(text, delimiter, names, label):
    """Delimited text without a header row and without quote handling (quoting=3); the column
    names come from the schema. label names the source in error messages."""
    rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, quoting=csv.QUOTE_NONE))
    return _frame(label, [list(names)] + rows)


def read_pdf_table(path, pages, header):
    """A table a PDF publishes, as a text table. pages: the 1-based page numbers it is on, in
    order; header: the header row as published. pdfplumber (extract_tables, default settings)
    must find exactly one table on each page; the header must be the first row of the first
    page and no other row; every row must have one cell per header column, none missing. A cell
    is the text pdfplumber extracts, unchanged. Cross-check: on each page, the rows, each as its
    cells joined by one space, must be a run of consecutive lines of the page text
    (pdfplumber extract_text)."""
    body = []
    with pdfplumber.open(path) as pdf:
        for n in pages:
            page = pdf.pages[n - 1]
            tables = page.extract_tables()
            if len(tables) != 1:
                raise ValueError(f'{path} page {n}: {len(tables)} tables, not 1')
            rows = tables[0]
            bad = [i + 1 for i, r in enumerate(rows) if len(r) != len(header) or any(c is None for c in r)]
            if bad:
                raise ValueError(f'{path} page {n}: rows without one cell per header column: {bad[:10]}')
            lines = page.extract_text().splitlines()
            joined = [' '.join(r) for r in rows]
            if joined[0] not in lines:
                raise ValueError(f'{path} page {n}: first table row not a line of the page text')
            i = lines.index(joined[0])
            if lines[i:i + len(joined)] != joined:
                raise ValueError(f'{path} page {n}: the table rows are not consecutive lines of the page text')
            body.extend(rows)
    if body[0] != list(header):
        raise ValueError(f'{path}: first row {body[0]} is not the header {list(header)}')
    if list(header) in body[1:]:
        raise ValueError(f'{path}: the header row occurs again inside the table')
    return pd.DataFrame(body[1:], columns=list(header), dtype=str)


def _frame(path, rows):
    header, body = rows[0], rows[1:]
    bad = [i + 2 for i, r in enumerate(body) if len(r) != len(header)]
    if bad:
        raise ValueError(f'{path}: rows with another number of fields than the header: {bad[:10]}')
    return pd.DataFrame(body, columns=header, dtype=str)
