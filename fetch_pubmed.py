# fetch_pubmed.py - FINAL ROBUST VERSION WITH AGGRESSIVE CLEANING
import os
from Bio import Entrez
import time
import re
from unidecode import unidecode

def clean_text(text):
    """
    A robust function to clean text by removing HTML tags, normalizing unicode,
    and fixing whitespace.
    """
    # Remove HTML tags using a regular expression
    clean = re.sub(r'<.*?>', '', text)
    # Normalize unicode characters to their closest ASCII equivalent (e.g., Îµ -> e)
    clean = unidecode(clean)
    # Replace multiple whitespace characters with a single space
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def fetch_pubmed_abstracts(query, max_results=20, email="your.email@example.com"):
    """
    Searches PubMed and robustly fetches and CLEANS abstracts by parsing XML.
    """
    Entrez.email = email
    
    print(f"Searching PubMed for: '{query}'...")
    try:
        search_handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
        search_record = Entrez.read(search_handle)
        search_handle.close()
    except Exception as e:
        print(f"Error during PubMed search: {e}")
        return []
    
    id_list = search_record["IdList"]
    if not id_list:
        print("No articles found for the query.")
        return []
        
    print(f"Found {len(id_list)} articles. Fetching full records...")
    try:
        fetch_handle = Entrez.efetch(db="pubmed", id=id_list, rettype="full", retmode="xml")
        fetch_record = Entrez.read(fetch_handle)
        fetch_handle.close()
    except Exception as e:
        print(f"Error during PubMed fetch: {e}")
        return []
    
    abstracts = []
    print("Parsing and cleaning abstracts...")
    for article in fetch_record['PubmedArticle']:
        try:
            abstract_text_list = article['MedlineCitation']['Article']['Abstract']['AbstractText']
            full_abstract = ' '.join(abstract_text_list)
            
            cleaned_abstract = clean_text(full_abstract)
            
            if cleaned_abstract:
                abstracts.append(cleaned_abstract)
            
            time.sleep(0.1) # Be polite to the API server
        except KeyError:
            continue
            
    print(f"Successfully extracted and cleaned {len(abstracts)} abstracts.")
    return abstracts

if __name__ == "__main__":
    # --- Configuration ---
    SEARCH_QUERY = "(APOE4[Title/Abstract] AND amyloid[Title/Abstract])"
    MAX_ARTICLES = 30 # Fetching more to ensure we get enough good ones after cleaning
    YOUR_EMAIL = "aashir.javed2003@gmail.com"
    OUTPUT_FILE = "pubmed_corpus.txt"
    
    # Prerequisite check for the new library
    try:
        from unidecode import unidecode
    except ImportError:
        print("\nERROR: The 'unidecode' library is required for text cleaning.")
        print("Please install it by running: pip install unidecode\n")
        exit()

    abstracts = fetch_pubmed_abstracts(SEARCH_QUERY, MAX_ARTICLES, YOUR_EMAIL)
    
    if abstracts:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for abstract in abstracts:
                f.write(abstract + "\n")
        print(f"Clean abstracts saved to '{OUTPUT_FILE}'")