import urllib.request
import json

invs = ['inv-41771fb9', 'inv-5145b3e6', 'inv-1bfcb9bc']
for inv_id in invs:
    print('================== ' + inv_id + ' ==================')
    url = f'http://127.0.0.1:8000/api/knowledge-graph/{inv_id}'
    req = urllib.request.urlopen(url)
    res = json.loads(req.read().decode())
    case_num = res.get('case_number')
    nodes = res.get('nodes', [])
    edges = res.get('edges', [])
    print(f"Case: {case_num} | Nodes: {len(nodes)} | Edges: {len(edges)} | Neo4j Connected: {res.get('neo4j_connected')}")
    for n in nodes:
        print(f"  Node: id={n['id']:<10} | label={n['label']:<18} | type={n['type']:<10} | category={n.get('category', 'n/a'):<10} | is_tech={n.get('is_technical')}")
    print("Edges:")
    for e in edges:
        print(f"  Edge: {e['source']:<10} --[{e['relationship']}]--> {e['target']:<10} (suspicious={e.get('suspicious')})")
