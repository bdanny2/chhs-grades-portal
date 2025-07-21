import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- App config & Styles ---
st.set_page_config(page_title="Grades Portal", layout="wide")
st.markdown("""
    <style>
        body, .stApp { background-color: #f5deb3 !important; }
        section[data-testid="stSidebar"] { background-color: cornsilk !important; }
        .main-title {
            text-align: center; 
            font-size: 3em; 
            font-weight: 400; 
            margin-top: 0.5em;
            margin-bottom: 0.1em;
        }
        .subtitle {
            text-align: center;
            font-size: 1.5em;
            margin-bottom: 1em;
        }
        .section-space { margin-top: 3em; }
        .big-legend { font-size: 1.0em; }
        .block-container {
            padding-top: 1.5em !important;
            padding-bottom: 1.5em !important;
            padding-left: 3vw !important;
            padding-right: 3vw !important;
        }
    </style>
""", unsafe_allow_html=True)

SPREADSHEET_NAME = "Grades3"
SHEET_STUDENT = "Sheet2"
SHEET_TEACHERS = "Sheet7"

# --- Authenticate & Load Data ---
@st.cache_resource(show_spinner=False)
def get_clients_and_data():
    service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    teacher_ws = client.open(SPREADSHEET_NAME).worksheet(SHEET_TEACHERS)
    teacher_data = teacher_ws.get_all_records()
    teacher_df = pd.DataFrame(teacher_data)
    student_ws = client.open(SPREADSHEET_NAME).worksheet(SHEET_STUDENT)
    student_data = student_ws.get_all_values()
    header = student_data[0]
    student_df = pd.DataFrame(student_data[1:], columns=header)
    return client, teacher_df, student_df, student_ws

client, teacher_df, student_df, student_ws = get_clients_and_data()

# --- Role Selection Logic ---
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

# --- Index / Landing Page ---
if st.session_state["user_role"] is None:
    st.header("Welcome to CHHS Grading System")
    st.subheader("Please select your role to continue:")
    role = st.selectbox("I am a...", ["Select...", "Teacher", "Student", "Parent", "Admin"])
    if st.button("Continue"):
        if role != "Select...":
            st.session_state["user_role"] = role
            st.rerun()
    st.markdown("---")
    st.info("If you do not see your role or have access issues, contact the school administrator.")

# --- TEACHER INTERFACE ---
elif st.session_state["user_role"] == "Teacher":
    st.sidebar.image("logo-chhs.png", width=120)
    st.sidebar.title("Teacher Entry Portal")

    email = st.sidebar.text_input("Your Email").strip().lower()
    matched = teacher_df[teacher_df["email"].str.strip().str.lower() == email]

    if len(matched) == 0:
        st.sidebar.error("Email not recognized! Please use your registered email.")
        st.sidebar.button("Back to Role Select", on_click=lambda: st.session_state.update(user_role=None))
        st.stop()
    else:
        teacher_name = matched.iloc[0]["Teacher"]
        st.sidebar.success(f"Welcome, {teacher_name}!")
        subjects = matched["Subject"].tolist()
        subject = st.sidebar.selectbox("Select Subject", sorted(set(subjects)))

    filtered = student_df[
        (student_df["Teacher_Responsible_Email"].str.strip().str.lower() == email) &
        (student_df["Subject"] == subject)
    ]
    if not filtered.empty:
        term = st.sidebar.selectbox("Term", sorted(filtered["Term"].unique()))
        filtered = filtered[filtered["Term"] == term]
        assessment_type = st.sidebar.selectbox("Assessment Type", sorted(filtered["Assessment Type"].unique()))
        filtered = filtered[filtered["Assessment Type"] == assessment_type]

        st.header(f"Teacher Dashboard: {teacher_name}")
        st.caption(f"Subject: **{subject}**  |  Term: **{term}**  |  Assessment: **{assessment_type}**")

        editable_cols = ["Grade", "Subject Teacher Conduct Code", "Subject Teacher Comment Code"]
        filtered_view = filtered.copy()
        filtered_view["Teacher"] = teacher_name

        edited_df = st.data_editor(
            filtered_view,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Grade": st.column_config.NumberColumn("Grade", min_value=0, max_value=100),
                "Subject Teacher Conduct Code": st.column_config.SelectboxColumn(
                    "Conduct", options=["Excellent", "Good", "Average", "Needs Improvement"]
                ),
                "Subject Teacher Comment Code": st.column_config.TextColumn("Comment")
            },
            disabled=[c for c in filtered_view.columns if c not in editable_cols],
            key="grade_editor"
        )

        if st.button("Save Changes"):
            changed = (filtered[editable_cols] != edited_df[editable_cols]).any(axis=1)
            for idx in filtered[changed].index:
                row_number = idx + 2  # Header = row 1 in Sheets
                for col in editable_cols:
                    col_number = student_df.columns.get_loc(col) + 1
                    new_value = edited_df.at[idx, col]
                    student_ws.update_cell(row_number, col_number, new_value)
            st.success("Changes saved to Google Sheet!")
            st.rerun()

        st.divider()
        with st.expander("Show all students/grades (read only):"):
            st.dataframe(student_df, use_container_width=True)
    else:
        st.info("No assigned students for your filter selection.")

    if st.sidebar.button("Change Role"):
        st.session_state["user_role"] = None
        st.rerun()

# --- STUDENT INTERFACE (Placeholder) ---
elif st.session_state["user_role"] == "Student":
    st.title("Student Portal")
    st.info("🔒 This area is under development.\n\nIn future, students will be able to securely view their grades and progress reports here.")
    if st.button("Change Role"):
        st.session_state["user_role"] = None
        st.rerun()

# --- PARENT INTERFACE (Placeholder) ---
elif st.session_state["user_role"] == "Parent":
    st.title("Parent Portal")
    st.info("🔒 This area is under development.\n\nParents will soon be able to log in and view their child's grades and school progress.")
    if st.button("Change Role"):
        st.session_state["user_role"] = None
        st.rerun()

# --- ADMIN INTERFACE (Placeholder) ---
elif st.session_state["user_role"] == "Admin":
    st.title("Admin Dashboard")
    st.info("🔒 This area is under development.\n\nAdmins will be able to manage users, run analytics, and export grade reports.")
    if st.button("Change Role"):
        st.session_state["user_role"] = None
        st.rerun()

