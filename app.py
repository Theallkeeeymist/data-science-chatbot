import streamlit as st
import time
from datetime import datetime
from chatbot.rag_engine import RagEngine
from chatbot.judge import InterviewJudge

# CONFIGURATION
TOTAL_QUESTIONS = 2
INTERVIEW_DURATION_MINUTES = 5

# PAGE SETUP
st.set_page_config(page_title="DS Interview Bot", page_icon="🤖")

# CSS
st.markdown("""
    <style>
    .stButton>button {width: 100%; border-radius: 5px; height: 3em;}
    .report-card {background-color: #f0f2f6; padding: 20px; border-radius: 10px;}
    .pass {color: #28a745; font-weight: bold;}
    .fail {color: #dc3545; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# SESSION STATE INITIALIZATION
if "page" not in st.session_state:
    st.session_state.page = "login"
if "interview_history" not in st.session_state:
    st.session_state.interview_history = [] # Stores {q, user_ans, hidden_ans}
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "current_question_data" not in st.session_state:
    st.session_state.current_question_data = None
if "user_answer_input" not in st.session_state:
    st.session_state.user_answer_input = ""

# Initialize Engines
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RagEngine()
if "judge_engine" not in st.session_state:
    st.session_state.judge_engine = InterviewJudge()

# HELPER FUNCTIONS
def start_interview():
    st.session_state.page = "interview"
    st.session_state.start_time = datetime.now()
    st.session_state.current_q_index = 0
    st.session_state.interview_history = []
    # Fetch first question
    load_next_question()

def load_next_question():
    q_text, hidden_ans = st.session_state.rag_engine.get_interview_question("Data Science")
    st.session_state.current_question_data = {
        "question": q_text,
        "hidden_answer": hidden_ans
    }

def submit_answer():
    user_ans = st.session_state.user_answer_input
    
    # Save the turn
    st.session_state.interview_history.append({
        "question": st.session_state.current_question_data['question'],
        "hidden_answer": st.session_state.current_question_data['hidden_answer'],
        "user_answer": user_ans
    })
    
    # Move to next
    st.session_state.current_q_index += 1
    
    if st.session_state.current_q_index >= TOTAL_QUESTIONS:
        st.session_state.page = "feedback"
    else:
        load_next_question()
    
    # Request clearing the input box on the next rerun (can't set while widget exists)
    st.session_state._clear_user_answer = True

# --- PAGE 1: LOGIN ---
def show_login():
    st.title("🤖 AI Data Science Interviewer")
    st.markdown("### Master your interview skills with real-time AI feedback.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=150)
    
    with col2:
        name = st.text_input("Enter your full name to begin")
        role = st.selectbox("Target Role", ["Data Scientist", "ML Engineer", "Data Analyst"])
        
        if st.button("Start Interview"):
            if name:
                st.session_state.user_name = name
                st.session_state.role = role
                start_interview()
                st.rerun()
            else:
                st.warning("Please enter your name.")

# PAGE 2: INTERVIEW
def show_interview():
    # Header: Timer and Progress
    col1, col2 = st.columns([3, 1])
    with col1:
        progress = st.session_state.current_q_index / TOTAL_QUESTIONS
        st.progress(progress, text=f"Question {st.session_state.current_q_index + 1} of {TOTAL_QUESTIONS}")
    
    with col2:
        elapsed = datetime.now() - st.session_state.start_time
        remaining = max(0, INTERVIEW_DURATION_MINUTES * 60 - elapsed.total_seconds())
        mins, secs = divmod(remaining, 60)
        st.metric("Time Left", f"{int(mins):02}:{int(secs):02}")

    st.divider()

    # Chat Area
    q_data = st.session_state.current_question_data
    if q_data:
        st.chat_message("assistant").write(q_data['question'])
    
    # Input Area (Form prevents reload on every keystroke)
    # If a previous submission requested clearing the input, perform it before the widget is created
    if st.session_state.get("_clear_user_answer"):
        st.session_state.user_answer_input = ""
        del st.session_state["_clear_user_answer"]

    with st.form(key="answer_form"):
        st.text_area("Your Answer:", key="user_answer_input", height=150)
        submit_btn = st.form_submit_button("Submit Answer")
        
        if submit_btn:
            submit_answer()
            st.rerun()

# PAGE 3: FEEDBACK
def show_feedback():
    st.title("📊 Interview Results")
    
    if "feedback_report" not in st.session_state:
        with st.spinner("Analyzing your answers against the Answer Key..."):
            report = st.session_state.judge_engine.evaluate_interview(st.session_state.interview_history)
            st.session_state.feedback_report = report
    
    report = st.session_state.feedback_report
    
    # Top Level Stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Score", f"{report.get('score', 0)}/100")
    
    verdict = report.get('verdict', 'Neutral')
    color = "green" if verdict == "Pass" else "red"
    col2.markdown(f"### Verdict: :{color}[{verdict}]")
    
    col3.write(f"**Candidate:** {st.session_state.user_name}")

    st.info(report.get('summary', 'No summary available.'))
    
    # Detailed Columns
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("✅ Strong Areas")
        for item in report.get('strong_areas', []):
            st.success(f"- {item}")
            
    with col_b:
        st.subheader("⚠️ Areas for Improvement")
        for item in report.get('improvement_tips', []):
            st.warning(f"- {item}")

    st.divider()
    
    # Transcript Review
    with st.expander("📝 Review Full Transcript & Correct Answers"):
        for i, turn in enumerate(st.session_state.interview_history):
            st.markdown(f"**Q{i+1}: {turn['question']}**")
            st.markdown(f"*You said:* {turn['user_answer']}")
            st.markdown(f"*:blue[Ideal Answer:]* {turn['hidden_answer']}")
            st.divider()
            
    if st.button("Restart Interview"):
        st.session_state.clear()
        st.rerun()

# MAIN ROUTER
if st.session_state.page == "login":
    show_login()
elif st.session_state.page == "interview":
    show_interview()
elif st.session_state.page == "feedback":
    show_feedback()