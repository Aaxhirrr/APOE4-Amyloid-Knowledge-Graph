# extract_triples.py - FINAL ROBUST VERSION
import os
import json
import openai
from dotenv import load_dotenv
import certifi
import httpx
import time # NEW: Import the time library for adding delays

load_dotenv()

# --- Custom HTTP Client with Updated Certificates ---
custom_http_client = httpx.Client(verify=certifi.where())
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=custom_http_client,
)

def extract_triples(text, max_retries=3):
    """
    Calls the OpenAI API to extract triples, now with retry logic and delays.
    """
    prompt = (
        "Extract triples (Subject, Relation, Object) about APOE4 and amyloid-beta from this abstract.\n"
        "Respond ONLY with a JSON array of objects {\"subject\":...,\"relation\":...,\"object\":...}.\n\n"
        f"{text}\n"
    )
    
    # --- NEW: Retry Mechanism ---
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                timeout=30 # Add a timeout for the request
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}. Retrying in 3 seconds...")
            time.sleep(3) # Wait for 3 seconds before trying again
            
    print("  All retry attempts failed for this line.")
    return [] # Return an empty list if all retries fail


if __name__ == "__main__":
    all_triples = []
    corpus_file = "pubmed_corpus.txt"
    
    print(f"Reading from '{corpus_file}'...")
    try:
        with open(corpus_file, encoding="utf-8") as f:
            abstracts = [line.strip() for line in f if line.strip()]
        
        for i, line in enumerate(abstracts):
            print(f"\nProcessing abstract {i + 1}/{len(abstracts)}: '{line[:60]}...'")
            
            triples = extract_triples(line)
            if triples:
                print(f"  -> Successfully extracted {len(triples)} triples.")
                all_triples.extend(triples)
            
            # --- NEW: Polite Delay ---
            # Add a 1-second pause between each API call to respect rate limits
            time.sleep(1)

    except FileNotFoundError:
        print(f"ERROR: The file '{corpus_file}' was not found. Please run fetch_pubmed.py first.")

    with open("extracted_triples.json", "w", encoding="utf-8") as out:
        json.dump(all_triples, out, indent=2)
        
    print(f"\n-------------------------------------------------")
    print(f"Extraction complete. Total triples extracted: {len(all_triples)}")
    print(f"-------------------------------------------------")