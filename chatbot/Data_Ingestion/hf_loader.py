from datasets import load_dataset
import sys
from chatbot.Data_Ingestion.base import DataSourceLoader
from chatbot.exception.exception import ChatbotException
from chatbot.src_logging.logger import logging

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