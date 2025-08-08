# APOE4-Amyloid-Knowledge-Graph
![Status: Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-orange)
![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008cc1)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991)


A project to build and visualize a knowledge graph of the relationship between the APOE4 gene and Amyloid from the complex biomedical literature.

**Live Application Demo:** `https://apoe4-amyloid-knowledge-graph.streamlit.app/`

## 🚧 About The Project

This project explores a fully automated approach to knowledge discovery as an extension of the `OntoKGen` research framework from Arizona State University. The pipeline ingests unstructured text from scientific abstracts and transforms it into a structured, queryable knowledge graph, with a specific focus on the mechanistic role of the APOE4 gene in Alzheimer's Disease pathogenesis.

It aims to automatically process scientific articles from PubMed to extract structured relationships (triples) concerning the APOE4 gene and its connection to amyloid proteins. The extracted data is then loaded into a Neo4j graph database.

The final goal is to create an interactive web application (OntoKGen-Bio) using Streamlit that allows users to explore and visualize these complex biomedical relationships.

### Current Status

This repository is currently under active development. The core pipeline for:
1.  Fetching data from PubMed (`fetch_pubmed.py`)
2.  Extracting relationship triples (`extract_triples.py`)
3.  Loading data into Neo4j (`load_neo4j.py`)
...is being built and refined. The Streamlit application (`app.py`) is in its initial stages.

## Getting Started

*(More detailed instructions will be added soon)*

1.  **Clone the repo**
    ```sh
    git clone [https://github.com/Aaxhirrr/APOE4-Amyloid-Knowledge-Graph.git](https://github.com/Aaxhirrr/APOE4-Amyloid-Knowledge-Graph.git)
    ```
2.  **Install dependencies**
    ```sh
    pip install -r requirements.txt
    ```

## Technology Stack

* **Backend:** Python
* **Web Framework:** Streamlit
* **Database:** Neo4j
* **Data Source:** PubMed

THIS README WILL BE UPDATED SOON.
