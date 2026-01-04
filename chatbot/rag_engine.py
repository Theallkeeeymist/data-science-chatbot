import os, sys
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
import random

from chatbot.src_logging.logger import logging
from chatbot.exception.exception import ChatbotException

load_dotenv()

INDEX_NAME = os.getenv("INDEX_NAME")

class RagEngine:
    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index(INDEX_NAME)
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        self.vector_store = PineconeVectorStore(index_name=INDEX_NAME, embedding=self.embeddings)
        logging.info("RAG Engine initialized successfully.")
    
    def get_interview_question(self, topic="Data Science"):
        """
        Retrieves a question based on some topic related to data science, but
        introduces randomness to avoid repetition of the same questions everytime.
        """
        try:
            """
            Variation introduces randomness to the query which can fetch us diverse queries
            from search results.
            """
            variations = ["interview questions", "concepts", "advanced", "basic", "coding", "sql queries"]
            query = f"{topic} {random.choice(variations)}"

            results = self.vector_store.similarity_search(query, k=7)

            if not results:
                return None, None
            
            selected_doc = random.choice(results)

            question_text = selected_doc.page_content
            answer_text = selected_doc.metadata.get("answer", "Answer not found in DB.")

            return question_text, answer_text
        except Exception as e:
            raise ChatbotException(e, sys)

# Test
# if __name__ == "__main__":
#     engine = RagEngine()
#     q, a = engine.get_interview_question("Machine Learning")
#     print(f"Question: {q}")
#     print(f"Hidden Answer: {a[:100]}...") # Printing only first 100 chars