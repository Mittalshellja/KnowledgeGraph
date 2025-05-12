from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import spacy
import PyPDF2
import networkx as nx
import matplotlib.pyplot as plt
import os
import uuid

app = FastAPI()

# Allow CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use your frontend URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import spacy.cli
spacy.cli.download("en_core_web_sm")

nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(uploaded_file):
    text = ""
    reader = PyPDF2.PdfReader(uploaded_file.file)
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_relationships(text):
    doc = nlp(text)
    edges = []

    for sent in doc.sents:
        for token in sent:
            if token.dep_ in ('nsubj', 'dobj') and token.head.pos_ == 'VERB':
                subject = token.text
                verb = token.head.text
                obj = [child for child in token.head.children if child.dep_ == 'dobj']
                if obj:
                    edges.append((subject, verb + " " + obj[0].text))

    entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "PRODUCT", "WORK_OF_ART"]]
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            edges.append((entities[i], "related_to", entities[j]))

    return edges
import networkx as nx
import matplotlib.pyplot as plt
import uuid

def create_graph_image(edges):
    import matplotlib.pyplot as plt
    import networkx as nx

    G = nx.DiGraph()

    for edge in edges:
        if len(edge) == 2:
            G.add_edge(edge[0], edge[1])
        else:
            G.add_edge(edge[0], edge[2], label=edge[1])

    # Better layout for large graphs
    pos = nx.spring_layout(G, k=1.8, iterations=200, seed=42)

    # Prepare image
    plt.figure(figsize=(24, 18), dpi=300)
    nx.draw_networkx_nodes(G, pos, node_size=2500, node_color="lightblue")
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='-|>', arrowsize=20, edge_color='gray', width=1.5)
    nx.draw_networkx_labels(G, pos, font_size=9, font_family="sans-serif")

    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.5)

    plt.axis("off")
    output_path = f"graph_{uuid.uuid4().hex}.png"
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return output_path



@app.post("/upload/")
async def upload(file: UploadFile = None, text: str = Form(None)):
    if file:
        text_content = extract_text_from_pdf(file)
    elif text:
        text_content = text
    else:
        return {"error": "Please upload a PDF or provide text input."}

    edges = extract_relationships(text_content)
    image_path = create_graph_image(edges)
    return {"image_url": f"http://localhost:10000/{image_path}"}

@app.get("/{image_name}")
def get_image(image_name: str):
    return FileResponse(image_name, media_type="image/png")
