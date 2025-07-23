# app.py – FINAL STABLE VERSION WITH LOCAL ANALYTICS
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
    if not records: return {"degree": {}, "betweenness": {}}
    G = nx.Graph()
    for r in records:
        G.add_edge(r["subj"], r["obj"])
    return {"degree": nx.degree_centrality(G), "betweenness": nx.betweenness_centrality(G)}

# --- New commit to git: New function to run Louvain locally using NetworkX ---
def run_louvain_analysis_local(records):
    """
    Runs Louvain community detection LOCALLY using the NetworkX library.
    This bypasses the unreliable Neo4j GDS on the free tier.
    """
    if not records:
        st.warning("No graph data to analyze.")
        return {}
        
    G = nx.Graph()
    for r in records:
        G.add_edge(r["subj"], r["obj"])
    
    # Find communities using networkx
    communities = nx.community.louvain_communities(G, seed=123)
    
    # Create a map of node -> community_id
    community_map = {}
    for i, community in enumerate(communities):
        for node in community:
            community_map[node] = i
            
    st.success(f"Found {len(communities)} communities.")
    return community_map

def extract_triples_from_text(text):
    prompt = f"""
    You are an expert biomedical researcher...
    Abstract: "{text}"
    Output:
    """ 
    try:
        resp = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
        content = resp.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        return json.loads(content)
    except Exception as e:
        st.error(f"OpenAI API Error during triple extraction: {e}")
        return []

def get_answer_from_llm(question, context_triples):
    if not context_triples: return "The graph is empty."
    prompt = f"Based ONLY on the following facts... QUESTION:\n{question}\n\nANSWER:" # Abridged for brevity
    try:
        resp = openai.chat.completions.create(model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return resp.choices[0].message.content
    except Exception as e:
        st.error(f"OpenAI API Error during QA: {e}")
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
    st.session_state.community_map = {} # We still need this to store the results

try:
    with open("pubmed_corpus.txt", encoding="utf-8") as f:
        abstracts = [ln.strip() for ln in f if ln.strip()]
except FileNotFoundError:
    abstracts = []

stories = [
    {"title": "The Core Genetic Risk", "nodes": ["APOE4 allele", "increased amyloid-β plaque deposition"], "caption": "The journey begins with the **APOE4 allele**..."},
    {"title": "Cellular Disruption", "nodes": ["APOE4", "astrocytic clearance of amyloid-β", "microglial phagocytosis of fibrillar amyloid-β"], "caption": "APOE4 disrupts the brain's cleaning crew..."},
    {"title": "Path to Decline", "nodes": ["senile plaques", "accelerated cognitive decline measured by the Morris water-maze test"], "caption": "This buildup forms **senile plaques**..."}
]

# -----------------------------------------------------------------------------
# --- 3. UI RENDERING ---
# -----------------------------------------------------------------------------

st.markdown("""<style>...</style>""", unsafe_allow_html=True) # Abridged for brevity
st.title("🧠 Advanced Knowledge Graph Explorer")

try:
    driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
    driver.verify_connectivity()
except Exception as e:
    st.error(f"Failed to connect to Neo4j. Please check your .env and Streamlit Secrets. Error: {e}")
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
    # ---: Call the new local function ---
    if st.button("Cluster Communities"):
        st.session_state.community_map = run_louvain_analysis_local(st.session_state.records)
        # We need to rerun to apply the new colors to the graph
        st.rerun()

# --- The rest of the app layout remains the same ---
filtered_records = [r for r in st.session_state.records if r["sLabel"] in selected_types and r["oLabel"] in selected_types]
entities = sorted({r["subj"] for r in filtered_records} | {r["obj"] for r in filtered_records})

col1, col2 = st.columns([3, 1])

# --- We put the inspector (col2) definition after the graph (col1) again.
# The `selected` variable is defined within the col2 block, and the graph
# will just re-render on the next run when `selected` changes.
with col1:
    st.subheader("Graph Visualization")
    
    if not filtered_records:
        st.warning("No data to display. Please load the graph or adjust filters.")
    else:
        # (The entire Pyvis graph rendering block goes here, exactly as it was)
        net = Network("800px", "100%", bgcolor="#121212", font_color="#E0E0E0", directed=True)
        net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=250, spring_strength=0.04, damping=0.09)
        
        deg = Counter(r["subj"] for r in filtered_records) + Counter(r["obj"] for r in filtered_records)
        color_map = {"Gene": "#66c2a5", "Pathology": "#fc8d62", "Disease": "#e78ac3", "Symptom": "#ffd92f", "Other": "#8da0cb"}
        community_palette = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FED766", "#9B59B6", "#F1C40F", "#E67E22", "#77DD77"]
        story_nodes = set(stories[st.session_state.story_step]['nodes'])
        
        # Get the selected node from session state for highlighting
        selected_node_in_inspector = st.session_state.get('selected_node_in_inspector', None)
        
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
            if s_name == selected_node_in_inspector:
                s_props["borderWidth"] = 6
                s_props["borderColor"] = "#FFFFFF"
                s_props["shadow"] = True
            net.add_node(s_name, label=s_name, color=s_color, size=15+deg[s_name]*2, title=f"<b>{s_name}</b><br>Type: {s_label}", font={"size": 14, "color": "#fff"}, **s_props)

            o_props = {"borderWidth": o_border_width, "shadow": False, "borderColor": o_color}
            if o_name == selected_node_in_inspector:
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
    selected = st.selectbox("Select a node to inspect:", [""] + entities, key="inspector_select")
    
    # Store the selection in session state so the graph can access it on the next run
    st.session_state.selected_node_in_inspector = selected
    
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
        if abstracts:
            hits = [a for a in abstracts if selected.lower() in a.lower()]
            if hits:
                for i, ex in enumerate(hits[:5], 1):
                    st.info(f"**Excerpt {i}:** {ex}")
            else:
                st.write("_No excerpts found in corpus for this entity._")
        else:
            st.write("_Corpus file not loaded._")