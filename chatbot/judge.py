import json
import os, sys
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from chatbot.exception.exception import ChatbotException
from chatbot.src_logging.logger import logging

load_dotenv()

class InterviewJudge:
    def __init__(self):
        # Using Gemini-Pro for the reasoning capabilities
        self.model = HuggingFaceEndpoint(
            repo_id = "google/gemma-3-1b-it",
            huggingfacehub_api_token=os.getenv("HUGGINGFACE_HUB_ACCESS_KEY"),
            task="text-generation"
        )
        self.llm = ChatHuggingFace(llm=self.model, temperature=0.4)

    def evaluate_interview(self, conversation_history):
        """
        Input: A list of dicts [{'question': '...', 'user_answer': '...', 'correct_answer': '...'}]
        Output: A dictionary with Pass/Fail, Strengths, Weaknesses
        """
        transcript_text = ""
        for i, turn in enumerate(conversation_history):
            transcript_text += f"""
            Q{i+1}: {turn['question']}
            User Answer: {turn['user_answer']}
            Hidden Ideal Answer: {turn['hidden_answer']}
            --------------------------------------------------
            """
        logging.info("Evaluation transcript generated.")
        
        prompt = f"""
        You are a Senior Data Science Hiring Manager. Evaluate this interview transcript.
        
        TRANSCRIPT:
        {transcript_text}
        
        TASK:
        Return a valid JSON object strictly following this format (no markdown, just raw json):
        {{
            "verdict": "Pass" or "Fail",
            "score": <integer_out_of_100>,
            "summary": "<2-sentence summary of candidate performance>",
            "strong_areas": ["<area 1>", "<area 2>"],
            "weak_areas": ["<area 1>", "<area 2>"],
            "improvement_tips": ["<specific actionable tip 1>", "<tip 2>"]
        }}
        """

        try:
            response = self.llm.invoke(prompt)
            content = response.content
            
            content = content.replace("```json", "").replace("```", "").strip()
            logging.info("Evaluation content generated successfully.")
            
            return json.loads(content)
        except Exception as e:
            return {
                "verdict": "Error", 
                "summary": f"Could not generate report: {e}",
                "strong_areas": [], "weak_areas": [], "improvement_tips": []
            }