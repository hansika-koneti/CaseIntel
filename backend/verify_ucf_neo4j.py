from services.neo4j_service import Neo4jKnowledgeGraphService

kg = Neo4jKnowledgeGraphService()
with kg.driver.session(database="neo4j") as s:
    r1 = s.run("MATCH (n) WHERE n.investigation_id = 'inv-c6a0726d' RETURN count(n) as c").single()
    r2 = s.run("MATCH (n)-[r]->() WHERE n.investigation_id = 'inv-c6a0726d' RETURN count(r) as c").single()
    print("Neo4j node count for inv-c6a0726d:", r1["c"])
    print("Neo4j relationship count for inv-c6a0726d:", r2["c"])

    nodes = s.run("MATCH (n) WHERE n.investigation_id = 'inv-c6a0726d' RETURN labels(n) as l, n.id as id, n.name as name").data()
    print(f"Neo4j nodes list ({len(nodes)}):")
    for n in nodes:
        print(" ", n)
