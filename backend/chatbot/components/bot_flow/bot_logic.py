import os
from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from chatbot.components.rag_implementation.rag_engine import RagEngine

load_dotenv()

class InterviewLoop:
    def __init__(self, role, resume_context=None):
        # 1. Setup Model
        self.llm = HuggingFaceEndpoint(
            repo_id="meta-llama/Llama-3.1-8B-Instruct",
            huggingfacehub_api_token=os.getenv("HUGGINGFACE_HUB_ACCESS_KEY"),
            task="text-generation",
            temperature=0.4
        )
        self.model = ChatHuggingFace(llm=self.llm)
        self.rag = RagEngine()

        self.resume_context = resume_context if resume_context else "no resume provided"
        self.role = role

        # 2. Initial Chat History
        sys_msg = ChatPromptTemplate.from_messages(
            ("system", """You are a 5 year experienced data scientist at Amazon. You are conducting an interview for a {role} role.
            First check if {resume_context} is provided, if it is provided parse data from it to ask about projects experience and basically
            starter questions from that. If nothing is provided then ask some question on your one like "What projects?" "What did you do in those?"
            "What experience do you have" and similar stuff.
              
            BELOW ARE THE SET OF RULES THAT YOU MUST FOLLOW.
             
            Rules:
            1. Ask ONE question at a time.
            2. Wait for the user's answer.
            3. If the answer is good, move to the next topic. If bad, ask a clarifying question DONT JUST TELL WHAT'S WRONG TRY TO GET 
               ANSWERS FROM THE USER IF IT FAILS TO THEN PROVIDE ANSWER(and deduct marks based on this).
            4. You must ask 5 or so technical questions in total and it should include Coding question too.
            5. Questions must cover different topics like Statistics, ML, Deep Learning, SQL, Query Writing, coding etc.
            6. Based on the answer keep how many questions to be asked but the minimum count is 4 and max is 15, output "INTERVIEW_FINISHED" and provide a final Pass/Fail verdict.
            7. Keep track of how much time it takes the candidate to answer each question and how efficient their answer is.
            8. BE STRICT. REJECT IF YOU SCORE VERDICT IS LESS THAN 60 and be a good critque. GRILL THE FUCKING USER.
            9. Take a balanced interview in standard of questions.""")
        )
        self.chat_history = sys_msg.invoke({'role': self.role, 'resume_context': self.resume_context}).to_messages()

    def process_turn(self, user_input):
        self.chat_history.append(HumanMessage(content=user_input))

        # RAG INTEGRATION START
        # We inject a hidden instruction telling the model exactly what to ask next
        # This keeps your flow but forces it to use your Database questions.
        q_text, hidden_ans = self.rag.get_interview_question("Data Science")
        
        if q_text:
            # We add a temporary system message to guide the Llama model
            rag_instruction = f"""
            (System Instruction: Keep a mix of your internal question generation and the rag question.
            If you do not get a relevant reply or answer from user even after a clrifying question(You can give ATMAX 2 hints or clarifying
            question), then you should move to the next question again either from retrieved text or your internal knowledge,
            also if he gives a wrong answer or does not reply correctly keep that in your mind. Don't be lenient it's either
            Selected or Rejected based on their performance. No LENIENCY. REMEMBER THAT.
            Your NEXT question MAY or MAY NOT be based on this retrieved text: "{q_text}". 
            Do not answer it yourself. Just ask it to the candidate.)
            """
            self.chat_history.append(SystemMessage(content=rag_instruction))

        response = self.model.invoke(self.chat_history)
        ai_msg = response.content

        self.chat_history.append(AIMessage(content=ai_msg))

        return ai_msg
    
    def get_transcript_str(self):
        """
        convert the chat history objects into a readable string for the judge
        """
        transcript = ""
        for msg in self.chat_history:
            if isinstance(msg, SystemMessage):
                continue

            role = "Interviewer" if isinstance(msg, AIMessage) else "Candidate"
            transcript += f"{role}: {msg.content} \n\n"
        return transcript