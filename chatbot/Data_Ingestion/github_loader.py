import requests
import re, sys
from chatbot.Data_Ingestion.base import DataSourceLoader
from chatbot.exception.exception import ChatbotException
from chatbot.src_logging.logger import logging

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