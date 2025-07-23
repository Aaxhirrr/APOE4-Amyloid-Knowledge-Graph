# load_neo4j.py — RESILIENT VERSION
import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PWD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PWD))

# Heuristics for guessing entity types
def guess_label(name: str):
    lowers = name.lower()
    if any(term in lowers for term in ["apoe", "psen", "gene"]):
        return "Gene"
    if any(term in lowers for term in ["amyloid", "plaque", "clearance", "pathology", "tau", "neuroinflammation"]):
        return "Pathology"
    if any(term in lowers for term in ["alzheimer", "dementia"]):
        return "Disease"
    if any(term in lowers for term in ["memory", "cognitive", "decline"]):
        return "Symptom"
    return "Other"

def add_triple(tx, s, s_label, r, o, o_label, evidence):
    # Use MERGE to avoid creating duplicate nodes and relationships
    query = """
    MERGE (a:%s {name: $s})
    MERGE (b:%s {name: $o})
    MERGE (a)-[rel:RELATION {type: $r}]->(b)
    SET rel.evidence = $evidence
    """ % (s_label, o_label)
    tx.run(query, s=s, o=o, r=r, evidence=evidence[:250]) # Truncate evidence if needed

if __name__ == "__main__":
    try:
        triples = json.load(open("extracted_triples.json", encoding="utf-8"))
        corpus_lines = open("pubmed_corpus.txt", encoding="utf-8").read().splitlines()
    except FileNotFoundError as e:
        print(f"Error: Could not find a required file. {e}")
        exit()

    print("Clearing the database...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n") # Clear out old data before loading

    print(f"Loading {len(triples)} triples into Neo4j...")
    with driver.session() as session:
        for idx, t in enumerate(triples):
            # I jsut FIXED this: Use .get() to safely access keys. This prevents KeyErrors.
            subj = t.get("subject")
            rel = t.get("relation")
            obj = t.get("object")

            # New commit: If any key is missing, skip this triple and print a warning.
            if not (subj and rel and obj):
                print(f"  -> WARNING: Skipping malformed triple at index {idx}: {t}")
                continue
            
            # Sanitize relation type for Neo4j
            rel_sanitized = rel.upper().replace(" ", "_").replace("-", "_")
            
            # Use naive mapping for evidence text
            evidence = corpus_lines[idx % len(corpus_lines)] if corpus_lines else "No evidence text available."
            
            session.execute_write(
                add_triple,
                subj, guess_label(subj),
                rel_sanitized,
                obj, guess_label(obj),
                evidence
            )
            
    print("Load complete.")
    driver.close()