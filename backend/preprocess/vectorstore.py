import os
from dotenv import load_dotenv
import pandas as pd
from langchain_cloudflare.embeddings import CloudflareWorkersAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_postgres import PGVector

load_dotenv()

embeddings = CloudflareWorkersAIEmbeddings(
    model_name="@cf/baai/bge-small-en-v1.5",
)

print("Connecting to database...")
vector_store = PGVector(
    embeddings=embeddings,
    embedding_length=384,
    collection_name="IT_help_desk",
    connection=os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+psycopg://"),
    pre_delete_collection=True,
)

print("Loading CSV file...")
df = pd.read_csv("data/rag_sample_qas_from_kis.csv")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n**", "\n\n" "\n", " ", ""]
)

docs = []

print("Chunking documents...")
for i, row in df.iterrows():
    data = row.to_dict()
    text = data["ki_text"]
    chunks = text_splitter.split_text(text)
    for chunk in chunks:
        docs.append(Document(page_content=chunk, metadata={"topic": data["ki_topic"]}))

print("Adding documents to vector store...")
vector_store.add_documents(docs)

print("Completed!")
