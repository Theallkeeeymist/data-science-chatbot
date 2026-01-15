import os, sys
from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging

load_dotenv()

class InterviewFeedback(BaseModel):
    verdict: str = Field(description="Final verdict based on the interview if it is pass or fail")
    score: float = Field(description="Out of 100 based on the user's performance throughout score him")
    summary: str = Field(description="A brief summary of the user's performance")
    strong_areas: List[str] = Field(description="List of the strong technical areas")
    weak_areas: List[str] = Field(description="List of the weak technical areas")
    improvements: List[str] = Field(description="List of suggestions for improvement")

class InterviewJudge:
    def __init__(self):
        try:
            self.model = HuggingFaceEndpoint(
                repo_id="meta-llama/Llama-3.1-8B-Instruct",
                huggingfacehub_api_token=os.getenv("HUGGINGFACE_HUB_ACCESS_KEY"),
                task="text-generation",
                temperature=0.4
            )
            self.llm = ChatHuggingFace(llm=self.model)

            self.parser = JsonOutputParser(pydantic_object=InterviewFeedback)
        except Exception as e:
            raise ChatbotException(e, sys)
    
    def evaluate_interview(self, transcript_text):
        try:
            # Removed the loop. We assume transcript_text is already a formatted string.
            
            prompt = PromptTemplate(
                template="""
                You are an experienced Senior Data Scientist from Amazon. Evaluate this interview transcript.
                Based on time taken to answer questions, the way questions were answered and the resume that is parsed. 
                Be critical of mistakes and very very very critical in selecting a candidate.
                
                TRANSCRIPT:
                {transcript}
                
                {format_instructions}
                """,
                input_variables=["transcript"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )

            chain = prompt | self.llm | self.parser
            logging.info("Generating interview feedback")

            # Pass the text directly
            return chain.invoke({"transcript": transcript_text})
            
        except Exception as e:
            raise ChatbotException(e, sys)