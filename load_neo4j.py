# load_neo4j.py  —  add entity labels & evidence strings
import os, json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
URI  = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PWD  = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PWD))

# Very simple heuristics for entity types
def guess_label(name: str):
    lowers = name.lower()
    if "apoe" in lowers or "psen" in lowers or "gene" in lowers:
        return "Gene"
    if "amyloid" in lowers or "plaque" in lowers or "clearance" in lowers:
        return "Pathology"
    if "alzheimer" in lowers or "dementia" in lowers:
        return "Disease"
    if "memory" in lowers or "cognitive" in lowers or "decline" in lowers:
        return "Symptom"
    return "Other"

def add_triple(tx, s, s_label, r, o, o_label, evidence):
    tx.run(
        """
        MERGE (a:%s {name:$s})
        MERGE (b:%s {name:$o})
        MERGE (a)-[rel:RELATION {type:$r}]->(b)
        SET rel.evidence = $evidence
        """ % (s_label, o_label),
        s=s, o=o, r=r, evidence=evidence[:180]  # truncate
    )

if __name__ == "__main__":
    triples = json.load(open("extracted_triples.json"))
    # Re-read the corpus lines for evidence text
    corpus_lines = open("pubmed_corpus.txt", encoding="utf-8").read().splitlines()

    with driver.session() as session:
        for idx, t in enumerate(triples):
            subj = t["subject"]
            rel  = t["relation"].upper().replace(" ", "_")
            obj  = t["object"]
            evidence = corpus_lines[idx % len(corpus_lines)]  # naive mapping
            session.execute_write(
                add_triple,
                subj, guess_label(subj),
                rel,
                obj,  guess_label(obj),
                evidence
            )
    print("Loaded triples with labels + evidence into Neo4j.")
    driver.close()
