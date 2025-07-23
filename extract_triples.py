# extract_triples.py - DEFINITIVE VERSION WITH IMPROVED PROMPT
import os
import json
import openai
from dotenv import load_dotenv
import certifi
import httpx
import time
from tqdm import tqdm

load_dotenv()

# --- Custom HTTP Client with Updated Certificates ---
custom_http_client = httpx.Client(verify=certifi.where())
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=custom_http_client,
)

def extract_triples(text, max_retries=3):
    """
    Calls the OpenAI API to extract triples using a more resilient "few-shot" prompt.
    """
    # --- FIXED: A more robust "few-shot" prompt ---
    # We give the AI an example and an explicit instruction for cases where it finds nothing.
    # This makes it much less likely to return an empty or invalid response.
    prompt = f"""
    You are an expert biomedical researcher. Your task is to extract relationships from a scientific abstract in the form of (Subject, Relation, Object) triples.

    Follow these rules:
    1. Extract facts related to APOE4, amyloid-beta, Alzheimer's Disease, and associated pathologies.
    2. The output must be a valid JSON array of objects.
    3. If you cannot find any relevant triples in the abstract, you MUST return an empty JSON array: [].

    Here is an example:
    ---
    Abstract: "The APOE4 allele is the strongest genetic risk factor for Alzheimer's disease (AD). It impairs the clearance of amyloid-beta from the brain."
    Output:
    [
        {{"subject": "APOE4 allele", "relation": "is strongest genetic risk factor for", "object": "Alzheimer's disease"}},
        {{"subject": "APOE4 allele", "relation": "impairs", "object": "clearance of amyloid-beta"}}
    ]
    ---
    
    Now, extract the triples from the following abstract:
    
    Abstract: "{text}"
    Output:
    """
    
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                timeout=60
            )
            content = resp.choices[0].message.content
            # The response might be inside a markdown code block, so we clean it
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            
            return json.loads(content)

        except json.JSONDecodeError:
             print(f"\n  Attempt {attempt + 1}/{max_retries} failed: API did not return valid JSON. Retrying...")
             time.sleep(5)
        except Exception as e:
            error_type = type(e).__name__
            print(f"\n  Attempt {attempt + 1}/{max_retries} failed with error type '{error_type}': {e}. Retrying...")
            time.sleep(5)
            
    print(f"\n  All retry attempts failed for abstract: '{text[:50]}...'. Skipping.")
    return []


if __name__ == "__main__":
    all_triples = []
    corpus_file = "pubmed_corpus.txt"
    
    print(f"Reading from '{corpus_file}'...")
    try:
        with open(corpus_file, encoding="utf-8") as f:
            abstracts = [line.strip() for line in f if line.strip()]
        
        for line in tqdm(abstracts, desc="Extracting Triples"):
            # We no longer need the aggressive cleaning
            if len(line) < 100:
                continue

            triples = extract_triples(line)
            
            if triples:
                all_triples.extend(triples)
            
            # Polite delay to respect rate limits
            time.sleep(1)

    except FileNotFoundError:
        print(f"ERROR: The file '{corpus_file}' was not found. Please run fetch_pubmed.py first.")

    with open("extracted_triples.json", "w", encoding="utf-8") as out:
        json.dump(all_triples, out, indent=2)
        
    print(f"\n-------------------------------------------------")
    print(f"Extraction complete. Total triples extracted: {len(all_triples)}")
    print(f"-------------------------------------------------")