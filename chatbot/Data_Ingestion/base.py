from abc import ABC, abstractmethod
from typing import List, Dict

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