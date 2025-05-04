import argparse
import os
from graphviz import Source
from .builder import build_graph
try:
    from py2neo import Graph, Node, Relationship
except ImportError:
    Graph = None

def export_neo4j(scan_id: int, json_dict: dict):
    url = os.getenv("NEO4J_URL", "bolt://neo4j:password@localhost:7687")
    graph = Graph(url)
    tx = graph.begin()
    node_map = {}
    for n in json_dict['nodes']:
        node = Node(n['type'], id=n['id'])
        graph.merge(node, n['type'], 'id')
        node_map[n['id']] = node
    for l in json_dict['links']:
        rel = Relationship(node_map[l['source']], l['type'], node_map[l['target']])
        graph.merge(rel)
    tx.commit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_id', type=int, required=True)
    parser.add_argument('--neo4j', action='store_true')
    args = parser.parse_args()
    dot_str, json_dict = build_graph(args.scan_id)
    print(dot_str)
    if args.neo4j:
        if Graph is None:
            print("py2neo not installed")
            return
        export_neo4j(args.scan_id, json_dict)
        print("Exported to Neo4j")

if __name__ == '__main__':
    main()
