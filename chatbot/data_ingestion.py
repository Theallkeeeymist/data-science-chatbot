import os, time, requests, re, sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from chatbot.Data_Ingestion.hf_loader import HuggingFaceLoader
from chatbot.Data_Ingestion.github_loader import GithubMdLoader
from chatbot.Data_Ingestion.web_loader import AnalyticsVidhyaLoader

from chatbot.exception.exception import ChatbotException
from chatbot.src_logging.logger import logging

load_dotenv()

INDEX_NAME = os.getenv("INDEX_NAME")
DIMENSION = 768

def main():
    try:
        logging.info("Starting Data Ingestion Pipeline...")
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

        existing_indexes = [index.name for index in pc.list_indexes()]

        if INDEX_NAME not in existing_indexes:
            pc.create_index(
                name=INDEX_NAME,
                dimension=DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            time.sleep(10)
            logging.info(f"Created Pinecone index: {INDEX_NAME}")
        else:
            logging.info(f"Index '{INDEX_NAME}' already exists.")

        # Setup Embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
        )

        documents = []
        metadata = []

        loaders = [
            HuggingFaceLoader([
                "UdayG01/DataScienceInterviewQuestions", 
                "manasuma/ml_interview_qa"
            ]),
            GithubMdLoader([
                "https://github.com/youssefHosni/Data-Science-Interview-Questions-Answers/blob/main/SQL%20%26%20DB%20Interview%20Questions%20%26%20Answers%20for%20Data%20Scientists.md"
            ]),
            AnalyticsVidhyaLoader([
                "https://www.analyticsvidhya.com/blog/2024/06/data-science-coding-questions/"
            ])
        ]

        for loader in loaders:
            try:
                raw_data = loader.load_data()

                for item in raw_data:
                    documents.append(item['text'])
                    metadata.append(item['metadata'])
            except Exception as e:
                logging.error(f"Error loading data with {type(loader).__name__}: {e}")
            
        if not documents:
                logging.warning("No data collected from loaders.")
                return
        logging.info(f"Total Questions Collected: {len(documents)}")

        vector_store = PineconeVectorStore(
            index_name=INDEX_NAME,
            embedding=embeddings
        )

        Batch = 100
        for i in range(0, len(documents), Batch):
            batch_docs = documents[i:i+Batch]
            batch_metadata = metadata[i:i+Batch]

            vector_store.add_texts(texts=batch_docs, metadatas=batch_metadata)
            logging.info(f"Inserted batch {i} - {i+len(batch_docs)}")
            
        logging.info("Data Ingestion Completed Successfully.")
    except Exception as e:
        raise ChatbotException(e,sys)
    
# if __name__ == "__main__":
#     main()