import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import altair as alt

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
    service_account_info = st.secrets["gcp_service_account"]
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

    student_df["Grade"] = pd.to_numeric(student_df["Grade"], errors="coerce")
    return client, teacher_df, student_df, student_ws

client, teacher_df, student_df, student_ws = get_clients_and_data()

# --- Role Selection ---
st.sidebar.title("Select Role")
role = st.sidebar.selectbox("I am a...", ["Teacher", "Student", "Parent", "Admin"])

# --- TABS ---
tabs = st.tabs(["Teacher", "Student", "Parent", "Admin"])

# --- TEACHER TAB ---
with tabs[0]:
    if role == "Teacher":
        st.header("Teacher Entry Portal")
        email = st.text_input("Your Email").strip().lower()
        matched = teacher_df[teacher_df["email"].str.strip().str.lower() == email]

        if matched.empty:
            st.error("Email not recognized. Contact admin.")
        else:
            teacher_name = matched.iloc[0]["Teacher"]
            st.success(f"Welcome, {teacher_name}!")
            subjects = matched["Subject"].tolist()
            subject = st.selectbox("Select Subject", sorted(set(subjects)))

            filtered = student_df[
                (student_df["Teacher_Responsible_Email"].str.strip().str.lower() == email) &
                (student_df["Subject"] == subject)
            ]

            if not filtered.empty:
                term = st.selectbox("Term", sorted(filtered["Term"].unique()))
                assessment = st.selectbox("Assessment Type", sorted(filtered["Assessment Type"].unique()))
                filtered = filtered[(filtered["Term"] == term) & (filtered["Assessment Type"] == assessment)]

                st.data_editor(filtered, use_container_width=True)
            else:
                st.warning("No students assigned to your selection.")

# --- STUDENT TAB ---
with tabs[1]:
    if role == "Student":
        st.header("Student Portal")
        st.info("Student view coming soon.")

# --- PARENT TAB ---
with tabs[2]:
    if role == "Parent":
        st.header("Parent Portal")
        st.info("Parent view coming soon.")

# --- ADMIN TAB ---
with tabs[3]:
    if role == "Admin":
        st.header("Admin Dashboard")
        st.subheader("Grade Distribution")

        chart = alt.Chart(student_df.dropna(subset=["Grade"])).mark_bar().encode(
            x=alt.X("Grade", bin=True),
            y="count()",
            tooltip=["Grade"]
        ).properties(width=700, height=400)

        st.altair_chart(chart, use_container_width=True)

        st.subheader("All Student Records")
        st.dataframe(student_df, use_container_width=True)

# End
