from time import time
import streamlit as st
import json
import os, sys
import hashlib
from streamlit_ace import st_ace
from langchain_community.document_loaders import PyPDFLoader
from chatbot.components.bot_flow.bot_logic import InterviewLoop
from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging
from chatbot.components.judge.judge_logic import InterviewJudge 

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Interviewer", page_icon="🤖", layout="wide")

# --- CSS STYLING ---
st.markdown("""
<style>
    .stChatMessage { font-family: 'Courier New', monospace; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E1E1E; text-align: center; margin-bottom: 2rem; }
    .auth-container { border: 1px solid #ddd; padding: 2rem; border-radius: 10px; background-color: white; }
    /* Hide the default file uploader border for a cleaner look */
    [data-testid='stFileUploader'] { border: 1px dashed #ccc; padding: 20px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SIMPLE AUTHENTICATION SYSTEM (JSON BASED) ---
USER_DB_FILE = "users.json"

def load_users():
    try:
        if not os.path.exists(USER_DB_FILE):
            return {}
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        raise ChatbotException(e, sys)

def save_user(username, password_hash, role):
    try:
        users = load_users()
        users[username] = {"password": password_hash, "role": role}
        with open(USER_DB_FILE, "w") as f:
            json.dump(users, f)
    except Exception as e:
        raise ChatbotException(e, sys)
    
def hash_password(password):
    try:
        return hashlib.sha256(password.encode()).hexdigest()
    except Exception as e:
        raise ChatbotException(e, sys)
    
def verify_user(username, password):
    try:
        users = load_users()
        if username in users and users[username]["password"] == hash_password(password):
            return users[username]
        return None
    except Exception as e:
        raise ChatbotException(e, sys)

def resume_loader(upload_file):
    try:
        loader = PyPDFLoader(upload_file)
        resume = loader.load()

        text = ""
        for line in resume:
            text += line.page_content + "\n"
        return text
    except Exception as e:
        raise ChatbotException(e, sys)

# --- STATE MANAGEMENT ---
if "page" not in st.session_state:
    st.session_state.page = "auth"
if "coding_mode" not in st.session_state:
    st.session_state.coding_mode = False
if "user_data" not in st.session_state:
    st.session_state.user_data = {} # Stores name, role, resume_text

# --- PAGE 1: AUTHENTICATION (Login / Register) ---
def show_auth_page():
    st.markdown('<div class="main-header">🔐 AI Interview Portal</div>', unsafe_allow_html=True)

    try:
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            tab1, tab2 = st.tabs(["Login", "Create Account"])
            
            with tab1:
                st.write("### Welcome Back")
                login_user = st.text_input("Username", key="login_user")
                login_pass = st.text_input("Password", type="password", key="login_pass")
                
                if st.button("Login", use_container_width=True):
                    user_info = verify_user(login_user, login_pass)
                    if user_info:
                        st.success("Login Successful!")
                        st.session_state.user_data = {"name": login_user, "role": user_info["role"]}
                        st.session_state.page = "resume_upload"
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password")

            with tab2:
                st.write("### New Candidate Registration")
                new_user = st.text_input("Choose Username", key="new_user")
                new_pass = st.text_input("Choose Password", type="password", key="new_pass")
                new_role = st.selectbox("Target Role", ["Data Scientist", "ML Engineer", "Data Analyst"], key="new_role")
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if new_user and new_pass:
                        if verify_user(new_user, "dummy"): # Check existence
                            st.warning("Username already exists.")
                        else:
                            save_user(new_user, hash_password(new_pass), new_role)
                            st.success("Account created! Please log in.")
                    else:
                        st.warning("Please fill all fields.")
    except Exception as e:
        raise ChatbotException(e, sys)

# RESUME ONBOARDING
def show_resume_page():
    st.markdown('<div class="main-header">📄 Candidate Profile</div>', unsafe_allow_html=True)
    
    try:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.info(f"**Welcome, {st.session_state.user_data.get('name')}!**\n\nTarget Role: {st.session_state.user_data.get('role')}")
            st.write("Uploading your resume helps our AI tailor questions to your actual experience.")
            
        with col2:
            uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Skip & Continue ➔", use_container_width=True):
                    st.session_state.user_data["resume_text"] = "No resume provided."
                    st.session_state.page = "interview"
                    st.rerun()
            
            with col_b:
                if uploaded_file is not None:
                    if st.button("Process & Start Interview 🚀", type="primary", use_container_width=True):
                        
                        with st.spinner("Analyzing Resume..."):
                            # 1. Save the uploaded file temporarily so PyPDFLoader can read it
                            temp_path = f"./temp_{uploaded_file.name}"
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            try:
                                # 2. Call your existing resume_loader function
                                resume_text = resume_loader(temp_path)
                                
                                # 3. Save text to session state
                                st.session_state.user_data["resume_text"] = resume_text
                                st.toast("Resume parsed successfully!")
                                
                            except Exception as e:
                                st.error(f"Failed to parse resume: {e}")
                                st.session_state.user_data["resume_text"] = "Error parsing resume."
                            
                            finally:
                                # 4. Cleanup temp file
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)

                        # 5. Move to Interview
                        st.session_state.page = "interview"
                        st.rerun()
    except Exception as e:
        raise ChatbotException(e, sys)

# --- PAGE 3: INTERVIEW INTERFACE (Your Existing Logic) ---
def is_coding_question(text):
    text = text.lower()
    # Broader keywords to catch more cases
    triggers = [
        "write", "create", "implement", "code", "solution", 
        "function", "script", "query", "sql", "python", "pandas"
    ]
    # Check if ANY two keywords appear together (e.g., "write" + "function")
    # OR if specific strong phrases exist
    strong_triggers = ["write a", "code for", "implement a", "sql query"]
    
    has_strong = any(t in text for t in strong_triggers)
    has_context = sum(1 for t in triggers if t in text) >= 2
    
    # Negative check to prevent it from triggering on feedback ("Your code was good")
    is_feedback = "your code" in text or "you provided" in text
    
    return (has_strong or has_context) and not is_feedback

def show_interview_page():
    try:
        # 1. Initialize Bot
        if "bot" not in st.session_state:
            user_role = st.session_state.user_data.get('role')
            resume = st.session_state.user_data.get('resume_text')
            st.session_state.bot = InterviewLoop(role=user_role, resume_context=resume)
            
        if "messages" not in st.session_state:
            user_name = st.session_state.user_data.get('name')
            st.session_state.messages = [{"role": "assistant", "content": f"Hello {user_name}. Based on your profile, tell me about yourself:"}]

        # 2. Check Coding Mode
        last_msg = st.session_state.messages[-1]
        if last_msg["role"] == "assistant":
            st.session_state.coding_mode = is_coding_question(last_msg["content"])

        # 3. Layout Logic
        if st.session_state.coding_mode:
            show_coding_interface()
        else:
            show_chat_interface()
    except Exception as e:
        raise ChatbotException(e, sys)

def show_chat_interface():
    try:       
        st.title(f"Interview: {st.session_state.user_data.get('role')}")
        st.caption("Mode: Conversational")
        st.divider()

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if user_input := st.chat_input("Type your answer..."):
            process_submission(user_input)
    except Exception as e:
        raise ChatbotException(e, sys)

def show_coding_interface():
    try:
        col_chat, col_code = st.columns([1, 1])
        
        with col_chat:
            st.subheader("💬 Interview Chat")
            with st.container(height=600):
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
        
        with col_code:
            st.subheader("📝 Code Editor")
            st.info("Write your solution and press Submit.")
            
            code_input = st_ace(language="python", theme="monokai", height=400, key="code_editor")
            
            if st.button("🚀 Submit Solution", type="primary"):
                if code_input:
                    process_submission(f"My Code Solution:\n```python\n{code_input}\n```")
                else:
                    st.warning("Editor is empty.")
    except Exception as e:
        raise ChatbotException(e, sys)

# PAGE 4: FEEDBACK PAGE
def show_feedback_page():
    st.markdown('<div class="main-header">📊 Interview Results</div>', unsafe_allow_html=True)
    
    # 1. Initialize Judge & Generate Report (Run only once)
    if "feedback_report" not in st.session_state:
        judge = InterviewJudge()
        with st.spinner("Analyzing your interview performance..."):
            # We pass the full chat history from the bot logic
            if "bot" in st.session_state:
                transcript_txt = st.session_state.bot.get_transcript_str()
            else:
                transcript_txt = "No Interview history found"
            report = judge.evaluate_interview(transcript_txt)
            st.session_state.feedback_report = report
    
    report = st.session_state.feedback_report
    
    # 2. Top Stats (Scorecard)
    col1, col2, col3 = st.columns(3)
    col1.metric("Candidate", st.session_state.user_data.get('name'))
    col2.metric("Overall Score", f"{report.get('score', 0)}/100")
    
    verdict = report.get('verdict', 'Neutral')
    verdict_color = "green" if verdict == "Pass" else "red"
    col3.markdown(f"### Verdict: :{verdict_color}[{verdict}]")

    st.info(f"**Summary:** {report.get('summary')}")
    
    # 3. Detailed Feedback
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.success("### ✅ Strong Areas")
        for item in report.get('strong_areas', []):
            st.write(f"- {item}")
            
    with col_b:
        st.warning("### ⚠️ Areas for Improvement")
        for item in report.get('weak_areas', []):
            st.write(f"- {item}")
            
    st.divider()
    st.markdown("### 💡 Actionable Tips")
    for tip in report.get('improvement_tips', []):
        st.info(f"💡 {tip}")

    # 4. Buttons
    if st.button("Start New Interview"):
        st.session_state.clear()
        st.rerun()

def process_submission(user_content):
    try:
        # 1. User Message
        st.session_state.messages.append({"role": "user", "content": user_content})
        
        # 2. Get AI Response
        with st.spinner("Interviewer is thinking..."):
            ai_response = st.session_state.bot.process_turn(user_content)
        
        # 3. Add AI Response to Chat
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        if "INTERVIEW_FINISHED" in ai_response:
            st.balloons()
            st.success("Interview Finished! Generating Report...")
            st.session_state.page = "feedback"
            st.rerun()
        
        # If not finished, just rerun to update the chat window
        st.rerun()
        
    except Exception as e:
        raise ChatbotException(e, sys)

# MAIN ROUTER
try:
    if st.session_state.page == "auth":
        show_auth_page()
    elif st.session_state.page == "resume_upload":
        show_resume_page()
    elif st.session_state.page == "interview":
        show_interview_page()
    elif st.session_state.page == "feedback": # Added this
        show_feedback_page()
except Exception as e:
    raise ChatbotException(e, sys)