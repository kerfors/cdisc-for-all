# Convert a table with its CSVW metadata by rdf-tabular (minimal mode, validating) to N-Triples.
# Usage: ruby csvw_rdf_tabular.rb <metadata.json> <out.nt>   (run in the metadata's folder)
require "rdf/tabular"
require "rdf/ntriples"
graph = RDF::Graph.new
RDF::Tabular::Reader.open(ARGV[0], minimal: true, validate: true,
                          base_uri: "file://#{File.expand_path(ARGV[0])}") { |reader| graph << reader }
File.write(ARGV[1], graph.dump(:ntriples))
