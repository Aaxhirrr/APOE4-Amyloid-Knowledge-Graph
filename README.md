# APOE4-Amyloid-Knowledge-Graph

![Status: Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow)

A project to build and visualize a knowledge graph of the relationship between the APOE4 gene and Amyloid from biomedical literature.

## 🚧 About The Project

This project aims to automatically process scientific articles from PubMed to extract structured relationships (triples) concerning the APOE4 gene and its connection to amyloid proteins. The extracted data is then loaded into a Neo4j graph database.

The final goal is to create an interactive web application using Streamlit that allows users to explore and visualize these complex biomedical relationships.

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
