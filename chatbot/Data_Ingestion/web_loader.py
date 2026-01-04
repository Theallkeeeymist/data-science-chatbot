import requests
import sys
import re
from chatbot.Data_Ingestion.base import DataSourceLoader
from chatbot.exception.exception import ChatbotException
from bs4 import BeautifulSoup
from chatbot.src_logging.logger import logging

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