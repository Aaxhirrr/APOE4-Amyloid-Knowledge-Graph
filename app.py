# app.py – Final Corrected Version
import os
import tempfile
from collections import Counter
import json
import streamlit as st
from neo4j import GraphDatabase
from pyvis.network import Network
from dotenv import load_dotenv
import networkx as nx
import openai

# -----------------------------------------------------------------------------
# --- 1. HELPER FUNCTIONS ---
# -----------------------------------------------------------------------------

def fetch(driver, limit: int, year_range=(1990, 2025)):
    """Fetches a subgraph from Neo4j, with a placeholder for a year filter."""
    cypher = """
    MATCH (a)-[r:RELATION]->(b)
    RETURN labels(a)[0] AS sLabel, a.name AS subj,
           r.type AS rel, r.evidence AS evidence,
           labels(b)[0] AS oLabel, b.name AS obj
    LIMIT $limit
    """
    with driver.session() as s:
        params = {"limit": limit, "min_year": year_range[0], "max_year": year_range[1]}
        return [r.data() for r in s.run(cypher, params)]

def calculate_analytics(records):
    """Creates a NetworkX graph to calculate centrality metrics."""
    if not records: return {"degree": {}, "betweenness": {}}
    G = nx.Graph()
    for r in records:
        G.add_edge(r["subj"], r["obj"])
    return {"degree": nx.degree_centrality(G), "betweenness": nx.betweenness_centrality(G)}

# --- Find and replace this entire function in your app.py ---

def run_louvain_analysis(driver):
    """Runs the Louvain community detection algorithm using modern GDS syntax."""
    with driver.session() as session:
        try:
            # Drop the graph if it exists to ensure we're using the latest data
            session.run("CALL gds.graph.drop('ad_graph_louvain') YIELD graphName")
        except:
            # Do nothing if the graph doesn't exist
            pass
        
        try:
            # FIXED: Use the modern, more compatible syntax for graph projection
            # This tells GDS to create a graph named 'ad_graph_louvain' using ALL nodes (*)
            # and all relationships of type 'RELATION'.
            session.run("""
                CALL gds.graph.project(
                    'ad_graph_louvain',
                    '*',
                    'RELATION'
                ) YIELD graphName
            """)
            
            # Run the Louvain algorithm as before
            result = session.run("""
                CALL gds.louvain.stream('ad_graph_louvain')
                YIELD nodeId, communityId
                RETURN gds.util.asNode(nodeId).name AS name, communityId
            """)
            community_map = {record['name']: record['communityId'] for record in result.data()}
            
            # Clean up the projection
            session.run("CALL gds.graph.drop('ad_graph_louvain') YIELD graphName")
            
            return community_map
            
        except Exception as e:
            st.error(f"Neo4j GDS Error: {e}. The GDS library may be undergoing maintenance or the query failed.")
            return {}

def extract_triples_from_text(text):
    """Calls OpenAI to extract triples from user-provided text."""
    prompt = f"Extract triples (Subject, Relation, Object) about Alzheimer's Disease from this text. Respond ONLY with a JSON array of objects formatted as {{\"subject\":...,\"relation\":...,\"object\":...}}.\n\n{text}"
    try:
        resp = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        st.error(f"OpenAI API Error: {e}")
        return []

def get_answer_from_llm(question, context_triples):
    """Asks a question to an LLM with graph context."""
    if not context_triples: return "The graph is empty. Please load data before asking a question."
    prompt = f"Based ONLY on the following facts (triples from a knowledge graph), answer the user's question.\n\nFACTS:\n{json.dumps(context_triples, indent=2)}\n\nQUESTION:\n{question}\n\nANSWER:"
    try:
        resp = openai.chat.completions.create(model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return resp.choices[0].message.content
    except Exception as e:
        st.error(f"OpenAI API Error: {e}")
        return "Sorry, I could not process the question."

# -----------------------------------------------------------------------------
# --- 2. PAGE CONFIGURATION AND STATE ---
# -----------------------------------------------------------------------------

st.set_page_config(page_title="AD KG Explorer", layout="wide")
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if 'records' not in st.session_state:
    st.session_state.records = []
    st.session_state.analytics = {"degree": {}, "betweenness": {}}
    st.session_state.story_step = 0
    st.session_state.community_map = {}

try:
    with open("pubmed_corpus.txt", encoding="utf-8") as f:
        abstracts = [ln.strip() for ln in f if ln.strip()]
except FileNotFoundError:
    st.error("Error: seed_corpus.txt not found. Please make sure it's in the same directory.")
    abstracts = []

stories = [
    {"title": "The Core Genetic Risk", "nodes": ["APOE4 allele", "increased amyloid-β plaque deposition"], "caption": "The journey begins with the **APOE4 allele**, the primary genetic risk factor for late-onset Alzheimer's, which is strongly associated with the buildup of amyloid plaques."},
    {"title": "Cellular Disruption", "nodes": ["APOE4", "astrocytic clearance of amyloid-β", "microglial phagocytosis of fibrillar amyloid-β"], "caption": "APOE4 disrupts the brain's cleaning crew. It impairs how **astrocytes** clear out amyloid-β and reduces the ability of **microglia** to consume it."},
    {"title": "Path to Decline", "nodes": ["senile plaques", "accelerated cognitive decline measured by the Morris water-maze test"], "caption": "This buildup forms **senile plaques**. In research models, these plaques directly correlate with **accelerated cognitive decline**."}
]

# -----------------------------------------------------------------------------
# --- 3. UI RENDERING ---
# -----------------------------------------------------------------------------

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
    /* Your preferred CSS styling */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; background-color: #121212 !important; color: #E0E0E0 !important; }
    h1, h2, h3 { color: #FFFFFF; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .st-emotion-cache-16txtl3 { background-color: #1E1E1E; border-right: 1px solid #333; }
    .st-emotion-cache-16txtl3 h2, .st-emotion-cache-16txtl3 h3 { font-size: 1.5rem; color: #00faff; }
    .stButton>button { border-radius: 8px; border: 1px solid #00faff; color: #00faff; }
    .stButton>button:hover { background-color: #00faff; color: #121212; }
</style>
""", unsafe_allow_html=True)
st.title("🧠 Advanced Knowledge Graph Explorer")

try:
    driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
    driver.verify_connectivity()
except Exception as e:
    st.error(f"Failed to connect to Neo4j. Please check your .env configuration. Error: {e}")
    st.stop()

with st.sidebar:
    st.header("⚙️ Graph Controls")
    node_types = sorted(list(set(r[label] for r in st.session_state.records for label in ["sLabel", "oLabel"])))
    selected_types = st.multiselect("Filter by Node Type", options=node_types, default=node_types)
    timeline = st.slider("Filter by Publication Year (requires 'year' data)", 1990, 2025, (1990, 2025))
    edge_limit = st.slider("Max Relationships", 10, 250, 75, 10)
    if st.button("Load/Filter Graph"):
        with st.spinner("Loading graph..."):
            st.session_state.records = fetch(driver, edge_limit, timeline)
            st.session_state.analytics = calculate_analytics(st.session_state.records)
            st.session_state.community_map = {}
        st.success("Graph loaded.")

    st.markdown("---")
    st.header("🔬 Analytics")
    if st.button("Cluster Communities"):
        if st.session_state.records:
            with st.spinner("Running Louvain community detection..."):
                st.session_state.community_map = run_louvain_analysis(driver)
            st.success("Community analysis complete!")
        else:
            st.warning("Please load a graph first.")

# --- Define Filters and Entities BEFORE creating the layout ---
filtered_records = [r for r in st.session_state.records if r["sLabel"] in selected_types and r["oLabel"] in selected_types]
entities = sorted({r["subj"] for r in filtered_records} | {r["obj"] for r in filtered_records})

# --- Create Columns for Layout ---
col1, col2 = st.columns([3, 1])

# FIXED: The inspector column (col2) is now defined BEFORE the graph column (col1).
# This ensures the `selected` variable is defined before the graph needs to use it.
# The visual layout in the browser remains the same.
with col2:
    st.subheader("Tools & Inspector")
    
    st.markdown("#### 📖 Story Mode")
    step = st.session_state.story_step
    st.markdown(f"**Step {step + 1}: {stories[step]['title']}**")
    st.info(stories[step]['caption'])
    c1, c2 = st.columns(2)
    if c1.button("⬅️ Prev") and step > 0:
        st.session_state.story_step -= 1
        st.rerun()
    if c2.button("Next ➡️") and step < len(stories) - 1:
        st.session_state.story_step += 1
        st.rerun()

    st.markdown("---")
    st.markdown("#### ❓ Ask the Graph (Mini RAG)")
    qa_question = st.text_area("Ask a question based on the loaded graph data:")
    if st.button("Get Answer"):
        if qa_question:
            with st.spinner("Consulting AI assistant..."):
                st.markdown(get_answer_from_llm(qa_question, filtered_records))
        else:
            st.warning("Please enter a question.")
            
    st.markdown("---")
    st.markdown("#### ➕ Add Knowledge")
    with st.expander("Process New Text"):
        new_text = st.text_area("Paste text here to extract facts:")
        if st.button("Extract & Add to Session"):
            with st.spinner("AI is reading..."):
                new_triples = extract_triples_from_text(new_text)
                if new_triples:
                    st.success(f"Extracted {len(new_triples)} new facts!")
                    st.json(new_triples)
                else:
                    st.error("Could not extract any facts.")

    st.markdown("---")
    st.markdown("#### 🔍 Node Inspector")
    selected = st.selectbox("Select a node to inspect:", [""] + entities)
    
    if selected:
        st.markdown(f"### **{selected}**")
        st.markdown("**Graph Analytics**")
        analytics = st.session_state.analytics
        m1, m2 = st.columns(2)
        m1.metric("Degree Centrality", f"{analytics['degree'].get(selected, 0):.3f}")
        m2.metric("Betweenness Centrality", f"{analytics['betweenness'].get(selected, 0):.3f}")
        
        out_relations = [r for r in filtered_records if r["subj"] == selected]
        in_relations = [r for r in filtered_records if r["obj"] == selected]
        st.markdown("**Relationships**")
        for r in out_relations: st.markdown(f"- **{r['rel'].replace('_', ' ')}** → `{r['obj']}`")
        for r in in_relations: st.markdown(f"- `{r['subj']}` → **{r['rel'].replace('_', ' ')}**")
        
        st.markdown("---")
        st.markdown("#### 📜 Evidence from Corpus")
        hits = [a for a in abstracts if selected.lower() in a.lower()]
        if hits:
            for i, ex in enumerate(hits[:5], 1):
                st.info(f"**Excerpt {i}:** {ex}")
        else:
            st.write("_No excerpts found in the seed corpus for this entity._")

with col1:
    st.subheader("Graph Visualization")
    
    if not filtered_records:
        st.warning("No data to display. Please load the graph or adjust filters.")
    else:
        net = Network("800px", "100%", bgcolor="#121212", font_color="#E0E0E0", directed=True)
        net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=250, spring_strength=0.04, damping=0.09)
        
        deg = Counter(r["subj"] for r in filtered_records) + Counter(r["obj"] for r in filtered_records)
        color_map = {"Gene": "#66c2a5", "Pathology": "#fc8d62", "Disease": "#e78ac3", "Symptom": "#ffd92f", "Other": "#8da0cb"}
        community_palette = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FED766", "#9B59B6", "#F1C40F"]
        story_nodes = set(stories[st.session_state.story_step]['nodes'])
        
        for r in filtered_records:
            s_name, o_name, s_label, o_label = r["subj"], r["obj"], r["sLabel"], r["oLabel"]
            
            s_color, o_color = color_map.get(s_label, "#8da0cb"), color_map.get(o_label, "#8da0cb")
            if st.session_state.community_map:
                s_comm = st.session_state.community_map.get(s_name)
                o_comm = st.session_state.community_map.get(o_name)
                if s_comm is not None: s_color = community_palette[s_comm % len(community_palette)]
                if o_comm is not None: o_color = community_palette[o_comm % len(community_palette)]
            
            s_border_width = 4 if s_name in story_nodes else 2
            o_border_width = 4 if o_name in story_nodes else 2
            
            s_props = {"borderWidth": s_border_width, "shadow": False, "borderColor": s_color}
            if s_name == selected:
                s_props["borderWidth"] = 6
                s_props["borderColor"] = "#FFFFFF"
                s_props["shadow"] = True
            net.add_node(s_name, label=s_name, color=s_color, size=15+deg[s_name]*2, title=f"<b>{s_name}</b><br>Type: {s_label}", font={"size": 14, "color": "#fff"}, **s_props)

            o_props = {"borderWidth": o_border_width, "shadow": False, "borderColor": o_color}
            if o_name == selected:
                o_props["borderWidth"] = 6
                o_props["borderColor"] = "#FFFFFF"
                o_props["shadow"] = True
            net.add_node(o_name, label=o_name, color=o_color, size=15+deg[o_name]*2, title=f"<b>{o_name}</b><br>Type: {o_label}", font={"size": 14, "color": "#fff"}, **o_props)
            
            net.add_edge(s_name, o_name, label=r["rel"].replace("_", " ").title(), title=r["evidence"], color="#888", width=2)
        
        net.show_buttons(filter_=['physics', 'selection', 'rendering'])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            st.components.v1.html(open(tmp.name, 'r', encoding='utf-8').read(), height=820)
        st.download_button("Download Graph HTML", open(tmp.name, 'r').read(), "ad_graph.html", "text/html")