"""Provenance.json of a base graph: graph IRI, the source pin, input and schema SHA-256, the
triple count, the graph hash, and the text hashes of the source table and of the view.
No timestamp: a rebuild from the same pin gives the same file."""

import json
from importlib.metadata import version

from cfa import REPO_ROOT
from cfa.pins import file_sha256, reference_versions
from cfa.view import TEXT_HASH_METHOD

TOOLS = ['rdflib', 'linkml', 'pyshacl', 'openpyxl', 'pandas']


def provenance(source, inputs, schema_files, graph_iri, triples, graph_hash, source_text_hash,
               view_text_hash):
    rel = lambda p: p.relative_to(REPO_ROOT).as_posix()
    return {
        'source': source,
        'graph': graph_iri,
        'pin': reference_versions()[source],
        'inputs': {rel(p): file_sha256(p) for p in inputs},
        'schema': {rel(p): file_sha256(p) for p in schema_files},
        'triples': triples,
        'graph_sha256': graph_hash,
        'graph_sha256_method': 'SHA-256 of the canonical N-Triples (RDFC-1.0; no blank nodes)',
        'source_text_sha256': source_text_hash,
        'view_text_sha256': view_text_hash,
        'text_sha256_method': TEXT_HASH_METHOD,
        'tools': {t: version(t) for t in TOOLS},
    }


def flat(prov):
    """Provenance as flat {key: str} for the Provenance sheet of the view."""
    out = {}

    def walk(prefix, value):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(f'{prefix}.{k}' if prefix else k, v)
        else:
            out[prefix] = str(value)
    walk('', prov)
    return out


def write_provenance(path, prov):
    path.write_text(json.dumps(prov, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
