from rdflib import Graph
from graphviz import Digraph

rdf = Graph()
rdf.parse("Ontology/ODMIoT_4.ttl", format="turtle")

dot = Digraph("Ontology")

node_map = {}

for i, node in enumerate(set(list(rdf.subjects()) + list(rdf.objects()))):
    node_id = f"n{i}"
    node_map[node] = node_id

    label = str(node).split("#")[-1]

    dot.node(node_id, label)

for s,p,o in rdf:
    if "owl#" in str(s):
        continue

    if "rdf-schema" in str(s):
        continue

    if "gufo" in str(s):
        continue
    dot.edge(
        node_map[s],
        node_map[o],
        label=str(p).split("#")[-1]
    )

dot.render("ontology_image", format="svg")