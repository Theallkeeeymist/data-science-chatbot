import os, time, requests, re, sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from datasets import load_dataset
from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging
from abc import ABC, abstractmethod
from typing import List, Dict

load_dotenv()

INDEX_NAME = os.getenv("INDEX_NAME")
DIMENSION = 768

class DataSourceLoader(ABC):
    """
    Every new data source added to the system must
    inherit from this abstract class
    """

    @abstractmethod
    def load_data(self) -> List[Dict]:
        """
        Must return a list of dictionaries in this format:
        [
            {
                "text": "Question: What is X?", 
                "metadata": {"source": "...", "answer": "..."}
            },
            ...
        ]
        """
        pass

class GithubMdLoader(DataSourceLoader):
    """
    Loads and processes markdown files from given Github URLs, we are
    not using WebBase loaders because it returns answers along with it as a Blob 
    but for a qna system we need to separate Question and Answer pairs.
    """
    def __init__(self, urls: list):
        self.urls = urls

    def load_data(self):
        results = []

        for url in self.urls:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

            try:
                response = requests.get(raw_url)
                if response.status_code == 200:
                    logging.info(f"Successfully fetched data from {raw_url}")
                    pattern = r"(Q\d+[:\.]\s*)(.*?)\n+(?:Answer:|Ans:)(.*?)(?=\nQ\d+[:\.]|\Z)"
                    matches = re.findall(pattern, response.text, re.DOTALL)

                    for _, q, a in matches:
                        results.append({
                            "text": q.strip(),
                            "metadata": {
                                "source": "Github",
                                "question": q.strip(),
                                "answer": a.strip()
                            }
                        })
            except Exception as e:
                raise ChatbotException(e, sys)
        return results

class HuggingFaceLoader(DataSourceLoader):
    def __init__(self, dataset_names: list):
        self.dataset_names = dataset_names

    def load_data(self):
        results = []

        for name in self.dataset_names:
            try:
               ds = load_dataset(name, split="train")
               logging.info("Dataset loaded successfully")
               for row in ds:
                   q = row.get("Question") or row.get("question") or row.get("QUESTION")
                   a = row.get("Answer") or row.get("answer") or row.get("ANSWER")
                   if q and a:
                       logging.info(f"Ques and ans found in the dataset")
                       results.append({
                           "text": q,
                           "metadata":{
                               "source": name,
                               "question": q,
                               "answer": a
                           }
                       })
                       logging.info("Question-Answer pair added to the results")
            except Exception as e:
                raise ChatbotException(e, sys)
        return results

class AnalyticsVidhyaLoader(DataSourceLoader):
    def __init__(self, urls: list):
        self.urls = urls

    def load_data(self):
        results = []
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        for url in self.urls:
            try:
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    logging.warning(f"Failed to fetch data from {url}, status code: {response.status_code}")
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Target the main article content to avoid footer/sidebar noise
                content_div = soup.find('div', class_='article-content') or soup
                
                # Find all potential question containers (paragraphs or headers)
                elements = content_div.find_all(['p', 'h3', 'h4'])
                
                current_q = None
                current_a = []
                
                for elem in elements:
                    text = elem.get_text().strip()
                    
                    # Regex to find "Q1." or "Q1:" patterns
                    if re.match(r"^Q\d+[\.:]", text):
                        # Save the PREVIOUS question before starting a new one
                        if current_q and current_a:
                            full_answer = "\n".join(current_a).strip()
                            if len(full_answer) > 10: # Filter out empty/short garbage
                                results.append({
                                    "text": f"Question: {current_q}",
                                    "metadata": {"source": "AnalyticsVidhya", "question": current_q, "answer": full_answer}
                                })
                        
                        # Start tracking NEW question
                        current_q = text
                        current_a = []
                    
                    # If we are inside a question, capture the answer text
                    elif current_q:
                        # Remove "Ans." or "Answer:" prefix if present
                        clean_text = re.sub(r"^(Ans\.|Answer:|Ans)\s*", "", text, flags=re.IGNORECASE)
                        if clean_text:
                            current_a.append(clean_text)
                
                # Don't forget the very last question!
                if current_q and current_a:
                    full_answer = "\n".join(current_a).strip()
                    results.append({
                        "text": f"Question: {current_q}",
                        "metadata": {"source": "AnalyticsVidhya", "question": current_q, "answer": full_answer}
                    })

                logging.info(f"Successfully processed data from {url}")
                    
            except Exception as e:
                raise ChatbotException(e, sys)
                
        return results

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