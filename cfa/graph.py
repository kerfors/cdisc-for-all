"""Writing a base graph, and its hash.

Graph hash: SHA-256 of the canonical N-Triples (RDFC-1.0). The base graphs have no blank
nodes, so canonicalisation is: each triple in canonical N-Triples form, duplicates removed,
lines sorted by code point, each line ending in LF. The 00 check compares this once with a
canonicalisation library (pyld, URDNA2015).
"""

import hashlib

from rdflib import BNode, Literal, URIRef
from rdflib.namespace import XSD

# Canonical N-Triples escapes in a literal (RDF 1.2): ECHAR for these, UCHAR for the other
# control characters U+0000-U+001F and U+007F, every other character as itself.
ECHAR = {'\b': '\\b', '\t': '\\t', '\n': '\\n', '\f': '\\f', '\r': '\\r', '"': '\\"', '\\': '\\\\'}
IRI_FORBIDDEN = set('<>"{}|^`\\ ') | {chr(c) for c in range(0x21)}


def _literal(text):
    out = []
    for ch in text:
        if ch in ECHAR:
            out.append(ECHAR[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f'\\u{ord(ch):04X}')
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'


def _iri(term):
    if set(str(term)) & IRI_FORBIDDEN:
        raise ValueError(f'IRI with a character that needs escaping: {term!r}')
    return f'<{term}>'


def canonical_lines(g):
    """The graph as sorted, de-duplicated canonical N-Triples lines (without LF). Stops on a
    blank node, or a literal with a language tag or a datatype other than xsd:string."""
    lines = set()
    for s, p, o in g:
        if isinstance(s, BNode) or isinstance(o, BNode):
            raise ValueError('a blank node in a base graph')
        if isinstance(o, Literal):
            if o.language or o.datatype not in (None, XSD.string):
                raise ValueError(f'not a plain literal: {o!r}')
            obj = _literal(str(o))
        elif isinstance(o, URIRef):
            obj = _iri(o)
        else:
            raise TypeError(f'unexpected object {o!r}')
        lines.add(f'{_iri(s)} {_iri(p)} {obj} .')
    return sorted(lines)


def graph_sha256(g):
    return hashlib.sha256(''.join(line + '\n' for line in canonical_lines(g)).encode('utf-8')).hexdigest()


def write_longturtle(g, path, prefixes):
    """The graph as rdflib longturtle (one triple per line, subjects and predicates sorted;
    deterministic). prefixes: {prefix: namespace}; they change the text, not the graph."""
    for prefix, ns in prefixes.items():
        g.bind(prefix, ns, override=True, replace=True)
    path.write_bytes(g.serialize(format='longturtle', encoding='utf-8'))
