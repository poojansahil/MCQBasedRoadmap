import streamlit as st
import pandas as pd
import re
import json
import requests
from datetime import datetime, timedelta

st.set_page_config(
    page_title="MCQ Assessment Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 MCQ Assessment Analyzer")
st.markdown("""
This application analyzes a student's MCQ assessment answers and generates a personalized roadmap with SMART goals.
""")

if 'student_answers' not in st.session_state:
    st.session_state.student_answers = {}
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'correct_answers' not in st.session_state:
    st.session_state.correct_answers = {}

# Utility functions
def remove_personal_info(text):
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REMOVED]', text)
    text = re.sub(r'\b(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b', '[PHONE REMOVED]', text)
    text = re.sub(r'Name:\s*[A-Za-z\s]+', 'Name: [NAME REMOVED]', text)
    text = re.sub(r'ID:\s*[A-Za-z0-9-]+', 'ID: [ID REMOVED]', text)
    text = re.sub(r'Student ID:\s*[A-Za-z0-9-]+', 'Student ID: [ID REMOVED]', text)
    return text

def fallback_processing(assessment_data, grade):
    correct_count = len(re.findall(r'\(Correct\)', assessment_data, re.IGNORECASE))
    incorrect_count = len(re.findall(r'\(Incorrect\)', assessment_data, re.IGNORECASE))
    subject_match = re.search(r'Subject:\s*([^\n]+)', assessment_data)
    subject = subject_match.group(1) if subject_match else "General"
    strengths = [f"Good performance in {subject}"] if correct_count >= incorrect_count else ["Needs improvement"]
    weaknesses = ["Focus on incorrect questions"]
    smart_goals = [
        {"goal": "Review incorrect answers", "measurement": "Practice similar questions", "timeline": "1 week", "area": subject},
        {"goal": "Master core concepts", "measurement": "Score >90% in mock test", "timeline": "2 weeks", "area": subject}
    ]
    return {"strengths": strengths, "weaknesses": weaknesses, "smart_goals": smart_goals}

def generate_roadmap(assessment_data, grade, api_key=None):
    if not api_key:
        return fallback_processing(assessment_data, grade)
    prompt = f"""
    Analyze this student's MCQ assessment:
    Grade: {grade}
    {assessment_data}
    Output JSON with strengths, weaknesses, 3-5 SMART goals.
    """
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/google/flan-t5-xxl",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"inputs": prompt},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            content = data[0].get("generated_text", "")
            json_match = re.search(r'({[\s\S]*})', content)
            if json_match:
                return json.loads(json_match.group(1))
        return fallback_processing(assessment_data, grade)
    except:
        return fallback_processing(assessment_data, grade)

def parse_question_paper(text):
    questions = []
    answers = {}
    pattern = r'(?:Question|Q)\s*(\d+)[.:]\s*(.*?)(?=(?:Question|Q)\s*\d+|$)'
    matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
    for match in matches:
        q_num = match.group(1)
        q_text = match.group(2).strip()
        answer_match = re.search(r'(?:Answer|Ans|Key):\s*([A-E])', q_text, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            q_text = re.sub(r'(?:Answer|Ans|Key):\s*[A-E]', '', q_text).strip()
            answers[q_num] = answer
        questions.append({'number': q_num, 'text': q_text})
    return questions, answers

def create_timeline(goals):
    today = datetime.now()
    timeline = []
    current = today
    for goal in goals:
        weeks = int(re.search(r'(\d+)', goal["timeline"]).group(1)) if 'week' in goal["timeline"].lower() else 2
        end = current + timedelta(weeks=weeks)
        goal.update({"start_date": current.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d")})
        timeline.append(goal)
        current = end + timedelta(days=1)
    return timeline

# Main UI
input_tab, results_tab = st.tabs(["Input Data", "Analysis Results"])

with input_tab:
    col1, col2 = st.columns(2)

    with col1:
        st.header("Assessment Data")
        grade = st.selectbox("Grade", ["K"] + [str(i) for i in range(1,13)] + ["College"])
        api_key = st.text_input("Hugging Face API Key (optional)", type="password")

        input_method = st.radio("Input Method", ["Paste Complete Answer Sheet", "Enter Question Paper & Answers"], index=0)

        if input_method == "Paste Complete Answer Sheet":
            assessment_data = st.text_area("Paste assessment data", height=300)
            subject = st.text_input("Subject", value="")
            if st.button("Analyze and Generate Roadmap", type="primary"):
                if subject and not re.search(r'Subject:', assessment_data):
                    assessment_data = f"Subject: {subject}\n\n{assessment_data}"
                cleaned_data = remove_personal_info(assessment_data)
                with st.spinner("Analyzing..."):
                    result = generate_roadmap(cleaned_data, grade, api_key)
                    st.session_state.analysis_result = result
                    st.session_state.grade = grade
                    st.query_params.update(tab="results")

        else:
            st.subheader("Step 1: Paste Question Paper")
            paper_text = st.text_area("Paste question paper", height=200)
            if paper_text:
                subject_match = re.search(r'Subject:\s*([^\n]+)', paper_text)
                subject = subject_match.group(1) if subject_match else st.text_input("Subject")
                questions, correct_answers = parse_question_paper(paper_text)
                st.session_state.questions = questions
                st.session_state.correct_answers = correct_answers

            st.subheader("Step 2: Enter Student Answers")
            bulk_answers = st.text_area("Paste student answers (e.g. 1. A\n2. B)", height=150)
            if bulk_answers:
                lines = bulk_answers.split('\n')
                for line in lines:
                    match = re.match(r'(\d+)[.)\s-]*([A-E])', line.strip())
                    if match:
                        q_num, ans = match.groups()
                        st.session_state.student_answers[q_num] = ans.upper()

            if st.button("Generate Assessment Analysis", type="primary"):
                lines = [f"Subject: {subject}", ""]
                correct = 0
                for q in st.session_state.questions:
                    num = q['number']
                    student_ans = st.session_state.student_answers.get(num, "")
                    correct_ans = st.session_state.correct_answers.get(num, "")
                    status = "(Correct)" if student_ans == correct_ans else "(Incorrect)"
                    if student_ans == correct_ans:
                        correct += 1
                    lines.append(f"Question {num}: {student_ans} {status}")
                total = len(st.session_state.questions)
                lines.append("")
                lines.append(f"Total Score: {correct}/{total} ({round(correct/total*100)}%)")
                data = "\n".join(lines)
                with st.spinner("Analyzing..."):
                    result = generate_roadmap(data, grade, api_key)
                    st.session_state.analysis_result = result
                    st.session_state.grade = grade
                    st.query_params.update(tab="results")

    with col2:
        st.header("Sample Input Formats")
        st.code("""
Name: John Doe
Grade: 10
Subject: Mathematics

Question 1: A (Correct)
Question 2: B (Incorrect)
Question 3: C (Correct)
...""")

with results_tab:
    st.header("Analysis Results")
    if 'analysis_result' in st.session_state:
        res = st.session_state.analysis_result
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Strengths")
            for s in res.get("strengths", []):
                st.markdown(f"- {s}")
        with col2:
            st.subheader("Weaknesses")
            for w in res.get("weaknesses", []):
                st.markdown(f"- {w}")
        st.subheader("SMART Goals")
        timeline = create_timeline(res.get("smart_goals", []))
        df = pd.DataFrame(timeline)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Please input and analyze data first!")

st.caption("\u2728 Educational tool for assessment analysis. Always validate recommendations.")
