"""Source files and their pins. Every pin and file SHA-256 lives in Reference_Versions.json."""

import hashlib
import json
from pathlib import PurePosixPath

from cfa import REPO_ROOT

REFERENCE_VERSIONS = REPO_ROOT / 'Reference_Versions.json'


def reference_versions():
    return json.loads(REFERENCE_VERSIONS.read_text(encoding='utf-8'))


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def table_file(source, table):
    """The pinned file of a source that holds a table: the file entry whose 'sheet' is the
    table, else the file whose name without extension is the table (a CSV/TSV source), else
    the source's only file. Stops if that is not exactly one file."""
    files = reference_versions()[source]['files']
    by_sheet = [name for name, entry in files.items() if entry.get('sheet') == table]
    if len(by_sheet) == 1:
        return by_sheet[0]
    by_stem = [name for name, entry in files.items() if 'sheet' not in entry and PurePosixPath(name).stem == table]
    if not by_sheet and len(by_stem) == 1:
        return by_stem[0]
    top = [name for name, entry in files.items() if 'in' not in entry]
    if not by_sheet and not by_stem and len(top) == 1:
        return top[0]
    raise KeyError(f'{source}: no single pinned file for table {table!r}')


def checked_source_file(source, name):
    """Path of a pinned source file in base/<source>/downloads/ (by its file name; a pin may
    carry the publisher's path, such as COSMoS export/). Stops if the file's SHA-256 differs
    from its pin."""
    entry = reference_versions()[source]['files'][name]
    path = REPO_ROOT / 'base' / source / 'downloads' / PurePosixPath(name).name
    found = file_sha256(path)
    if found != entry['sha256']:
        raise ValueError(f'{source}/{name}: SHA-256 {found} differs from the pin {entry["sha256"]}')
    return path
