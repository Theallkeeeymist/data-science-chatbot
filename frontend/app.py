import streamlit as st
import requests
import sys, time
from streamlit_ace import st_ace
from langchain_community.document_loaders import PyPDFLoader
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Interviewer", page_icon="🤖", layout="wide")

# --- CSS STYLING ---
st.markdown("""
<style>
    .stChatMessage { font-family: 'Courier New', monospace; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E1E1E; text-align: center; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- API CONFIGURATION ---
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_AUTH = f"{BASE_URL}/api/auth"
API_INTERVIEW = f"{BASE_URL}/api/interview"

# --- HELPER: RESUME PARSER (Client Side) ---
def parse_resume(upload_file):
    try:
        # Save temp
        temp_path = f"./temp_{upload_file.name}"
        with open(temp_path, "wb") as f:
            f.write(upload_file.getbuffer())
        
        # Load
        loader = PyPDFLoader(temp_path)
        resume = loader.load()
        text = "".join([line.page_content for line in resume])
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return text
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return ""

# --- STATE MANAGEMENT ---
if "page" not in st.session_state:
    st.session_state.page = "auth"
if "user_data" not in st.session_state:
    st.session_state.user_data = {} 
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# PAGE 1: AUTHENTICATION (API CONNECTED)
# ==========================================
def show_auth_page():
    st.markdown('<div class="main-header">🔐 AI Interview Portal</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        # --- LOGIN ---
        with tab1:
            with st.form("login_form"):
                user = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True):
                    if user and pw:
                        try:
                            # CALL API
                            payload = {"username": user, "password": pw}
                            res = requests.post(f"{API_AUTH}/login", json=payload)
                            
                            if res.status_code == 200:
                                data = res.json()
                                st.success("Login Successful!")
                                # UPDATE: Save resume_text if the backend sends it
                                st.session_state.user_data = {
                                    "name": data["user_id"], 
                                    "role": data["role"],
                                    "resume_text": data.get("resume_text") 
                                }
                                st.session_state.page = "resume_upload"
                                st.rerun()
                            else:
                                st.error(res.json().get("detail", "Login Failed"))
                        except Exception as e:
                            st.error(f"Connection Error: {e}")

        # --- REGISTER ---
        with tab2:
            with st.form("reg_form"):
                new_user = st.text_input("Choose Username")
                new_role = st.text_input("Choose the role that you're applying for...")
                new_pw = st.text_input("Choose Password", type="password")
                
                if st.form_submit_button("Create Account", use_container_width=True):
                    if new_user and new_pw:
                        try:
                            # CALL API
                            payload = {"username": new_user, "password": new_pw, "role": new_role}
                            res = requests.post(f"{API_AUTH}/register", json=payload)
                            
                            if res.status_code == 200:
                                st.success("Account created! Please log in.")
                            else:
                                st.error(res.json().get("detail", "Registration Failed"))
                        except Exception as e:
                            st.error(f"Connection Error: {e}")

# ==========================================
# PAGE 2: RESUME UPLOAD (UPDATED)
# ==========================================
def show_resume_page():
    st.markdown('<div class="main-header">📄 Candidate Profile</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info(f"**User:** {st.session_state.user_data.get('name')}\n\n**Role:** {st.session_state.user_data.get('role')}")

    with col2:
        # --- NEW LOGIC: Check for Saved Resume ---
        saved_resume = st.session_state.user_data.get("resume_text")
        resume_source = "upload" # Default
        
        if saved_resume:
            st.success("✅ Saved resume found!")
            resume_source = st.radio("Resume Option:", ["Use Saved Resume", "Upload New Resume"])
        
        final_resume_text = None
        
        # Handle Selection
        if resume_source == "Upload New Resume" or not saved_resume:
            uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
            if uploaded_file:
                with st.spinner("Processing PDF..."):
                    final_resume_text = parse_resume(uploaded_file)
        else:
            st.info("Using your previously saved resume.")
            final_resume_text = saved_resume

        # START BUTTON
        if st.button("Start Interview 🚀", type="primary", use_container_width=True):
            if not final_resume_text:
                st.warning("Please upload a resume or select the saved one.")
            else:
                try:
                    # --- FIX: Changed 'user_id' to 'username' to match Pydantic model ---
                    payload = {
                        "username": st.session_state.user_data["name"], 
                        "role": st.session_state.user_data["role"],
                        "resume_text": final_resume_text
                    }
                    
                    # Call /start endpoint
                    res = requests.post(f"{API_INTERVIEW}/start", json=payload)
                    
                    if res.status_code == 200:
                        # Update session with the latest resume used
                        st.session_state.user_data["resume_text"] = final_resume_text 
                        
                        # Set initial greeting
                        st.session_state.messages = [{
                            "role": "assistant", 
                            "content": f"Hello {st.session_state.user_data['name']}. Based on your profile, tell me about yourself."
                        }]
                        st.session_state.page = "interview"
                        st.rerun()
                    else:
                        st.error(f"Failed to start interview: {res.text}")
                except Exception as e:
                    st.error(f"API Connection Error: {e}")

# ==========================================
# PAGE 3: INTERVIEW INTERFACE
# ==========================================
def show_interview_page():
    st.title(f"Interviewing for: {st.session_state.user_data.get('role')}")
    
    # --- ADD THIS SIDEBAR BUTTON ---
    with st.sidebar:
        st.info("Interview Controls")
        if st.button("End Interview & Get Feedback", type="primary"):
            st.session_state.page = "feedback"
            st.rerun()
    # -------------------------------
    st.divider()

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat Input
    if user_input := st.chat_input("Type your answer..."):
        # 1. Append User Message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # 2. Get AI Response
        with st.spinner("Interviewer is thinking..."):
            try:
                payload = {
                    "username": st.session_state.user_data["name"], # Ensure this matches backend expectation too
                    "message": user_input
                }
                res = requests.post(f"{API_INTERVIEW}/chat", json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    ai_reply = data["reply"]
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                    with st.chat_message("assistant"):
                        st.write(ai_reply)

                    # Check if interview is over
                    if data.get("is_finished"):
                        st.session_state.page = "feedback"
                        st.rerun()
                else:
                    st.error("Server Error")
            except Exception as e:
                st.error(f"Connection Failed: {e}")

    # Optional: Coding Editor
    with st.expander("💻 Open Code Editor"):
        code = st_ace(language="python", theme="monokai", height=200)
        if st.button("Submit Code"):
            formatted_code = f"My Solution:\n```python\n{code}\n```"
            st.info("Code copied! Paste it in the chat to submit.")
            st.code(formatted_code)

# ==========================================
# PAGE 4: FEEDBACK
# ==========================================
def show_feedback_page():
    st.markdown('<div class="main-header">📊 Interview Results</div>', unsafe_allow_html=True)

    if "feedback_data" not in st.session_state:
        with st.spinner("Generating detailed feedback report..."):
            try:
                payload = {"username": st.session_state.user_data["name"]} # Ensure key matches backend
                res = requests.post(f"{API_INTERVIEW}/feedback", json=payload)
                
                if res.status_code == 200:
                    st.session_state.feedback_data = res.json()
                else:
                    st.error("Failed to fetch feedback.")
                    return
            except Exception as e:
                st.error(f"Error: {e}")
                return

    report = st.session_state.feedback_data
    
    # Display Score
    col1, col2 = st.columns(2)
    col1.metric("Score", f"{report.get('score', 0)}/100")
    col2.write(f"**Verdict:** {report.get('verdict', 'N/A')}")
    
    st.subheader("Summary")
    st.write(report.get("summary", ""))

    c1, c2 = st.columns(2)
    with c1:
        st.success("Strong Areas")
        for i in report.get("strong_areas", []): st.write(f"- {i}")
    with c2:
        st.warning("Needs Improvement")
        for i in report.get("weak_areas", []): st.write(f"- {i}")

    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# PAGE 5: PROFILE PAGE
# ==========================================
def show_profile_page():
    st.markdown('<div class="main-header">👤 User Profile</div>', unsafe_allow_html=True)
    
    username = st.session_state.user_data.get('name')
    if not username:
        st.error("Please log in first.")
        return

    # 1. Fetch Profile
    try:
        res = requests.get(f"{API_AUTH}/profile/{username}")
        if res.status_code == 200:
            profile = res.json()
        else:
            st.error("Failed to load profile")
            return
    except Exception as e:
        st.error(f"Connection error: {e}")
        return

    # 2. User Settings
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
            st.subheader(f"@{profile['username']}")
        
        with col2:
            st.write("### ⚙️ Preferences")
            current_role = profile['current_role']
            
            with st.form("update_role_form"):
                role_options = ["Data Scientist", "ML Engineer", "Data Analyst", "Software Engineer"]
                idx = role_options.index(current_role) if current_role in role_options else 0
                
                new_role = st.selectbox("Target Role", role_options, index=idx)
                
                if st.form_submit_button("Update Role"):
                    try:
                        upd_res = requests.put(f"{API_AUTH}/profile/role", json={
                            "username": username,
                            "new_role": new_role
                        })
                        if upd_res.status_code == 200:
                            st.success("Role updated!")
                            st.session_state.user_data['role'] = new_role
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

    st.divider()

    # 3. History Table 
    st.subheader("📚 Interview History")
    history = profile.get('history', [])
    
    if history:
        import pandas as pd
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(
            df[['date', 'job_role', 'score', 'verdict']],
            use_container_width=True,
            column_config={
                "score": st.column_config.ProgressColumn(
                    "Score", format="%d", min_value=0, max_value=100
                ),
            },
            hide_index=True,
        )
    else:
        st.info("No interviews yet.")

    st.divider()
    if st.button("⬅️ Back to Home"):
        st.session_state.page = "resume_upload"
        st.rerun()

# --- MAIN ROUTER ---
if st.session_state.page == "auth":
    show_auth_page()
elif st.session_state.page == "resume_upload":
    # Navigation to Profile
    if st.button("👤 Go to Profile", use_container_width=False):
        st.session_state.page = "profile"
        st.rerun()
    show_resume_page()
elif st.session_state.page == "profile":
    show_profile_page()
elif st.session_state.page == "interview":
    show_interview_page()
elif st.session_state.page == "feedback":
    show_feedback_page()