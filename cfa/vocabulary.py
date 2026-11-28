"""The vocabulary graph: the classes and properties the graphs use, in plain RDFS, restated from
the LinkML schema. One class per base table (its class_uri), one property per published column
(its slot_uri; label = the column name as published), one property per link of links.yaml (its
slot_uri; label = the link name, with its description, its rule, its marker rule and why a row
without it is not reported, as stated).
Nothing is added that the schema does not state."""
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, XSD

GRAPH = 'https://kerfors.github.io/cdisc-for-all/graph/vocabulary'


def vocabulary(index_path, specs):
    """index_path: schema/cdisc_for_all.yaml (imports every module); specs: cfa.link.load_links(...)."""
    sv = SchemaView(str(index_path))
    g = Graph()
    classes = {}
    for name, cls in sv.all_classes().items():
        c = URIRef(cls.class_uri)
        classes[name] = c
        g.add((c, RDF.type, RDFS.Class))
        g.add((c, RDFS.label, Literal(name)))
        g.add((c, RDFS.isDefinedBy, URIRef(cls.from_schema)))
        for col, att in (cls.attributes or {}).items():
            if att.range != 'string':
                raise ValueError(f'{name}.{col}: range {att.range!r}, not string')
            p = URIRef(att.slot_uri)
            g.add((p, RDF.type, RDF.Property))
            g.add((p, RDFS.label, Literal(col)))
            g.add((p, RDFS.domain, c))
            g.add((p, RDFS.range, XSD.string))
            g.add((p, RDFS.isDefinedBy, URIRef(cls.from_schema)))
    links_module = URIRef(sv.get_slot(specs[0]['name']).from_schema)
    for s in specs:
        p = URIRef(s['iri'])
        g.add((p, RDF.type, RDF.Property))
        g.add((p, RDFS.label, Literal(s['name'])))
        g.add((p, RDFS.domain, classes[s['domain']]))
        g.add((p, RDFS.range, classes[s['range']]))
        g.add((p, DCTERMS.type, Literal(s['kind'])))
        if s['description']:
            g.add((p, RDFS.comment, Literal(s['description'])))
        if s['rule']:
            g.add((p, RDFS.comment, Literal('Rule: ' + s['rule'])))
        if s['flag_rule']:
            g.add((p, RDFS.comment, Literal('Reported too: ' + s['flag_rule'])))
        if s['unmatched_rule']:
            g.add((p, RDFS.comment, Literal('A row without this link is not reported: ' + s['unmatched_rule'])))
        g.add((p, RDFS.isDefinedBy, links_module))
    return g


def unused_and_undeclared(vocab, graphs):
    """For a check against built graphs: (classes and properties of the vocabulary that no triple of
    graphs uses, classes and predicates the graphs use that the vocabulary does not declare).
    rdf:type is not counted; the NCIt concept IRIs and COSMoS's own IRIs are outside graphs passed here."""
    declared = set(vocab.subjects(RDF.type, RDF.Property)) | set(vocab.subjects(RDF.type, RDFS.Class))
    used = set()
    for g in graphs:
        used |= {p for p in g.predicates() if p != RDF.type}
        used |= set(g.objects(None, RDF.type))
    return sorted(declared - used), sorted(used - declared)


def vocabulary_prefixes(vocab):
    """Prefixes for the written file: one per namespace of the declared terms (up to and including
    "#"), named by its path after def/ (or link/, rule/), so the text is deterministic."""
    prefixes = {'rdf': str(RDF), 'rdfs': str(RDFS), 'xsd': str(XSD), 'dcterms': str(DCTERMS)}
    names = {}
    for s in set(vocab.subjects(RDF.type, RDF.Property)) | set(vocab.subjects(RDF.type, RDFS.Class)):
        ns = str(s).split('#')[0] + '#'
        if ns.startswith('https://kerfors.github.io/cdisc-for-all/rule/'):
            continue  # a by-rule IRI goes on after "#"; written in full
        path = ns[len('https://kerfors.github.io/cdisc-for-all/'):-1].replace('%20', '_')
        names[ns] = ''.join(ch if ch.isalnum() else '_' for ch in path)
    for ns, name in sorted(names.items()):
        prefixes[name] = ns
    return prefixes
