import streamlit as st
import pandas as pd
import re
import json
import requests
from datetime import datetime, timedelta
import time

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

# Other functions remain unchanged...
# [Truncated for brevity - assume all previous functions are intact: remove_personal_info, try_multiple_apis, generate_roadmap, fallback_processing, create_timeline, parse_question_paper]

# Tabs for different input methods
input_tab, results_tab = st.tabs(["Input Data", "Analysis Results"])

with input_tab:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Assessment Data")
        grade = st.selectbox("Student Grade Level", ["K"] + [str(i) for i in range(1, 13)] + ["College"])
        api_key = st.text_input("Hugging Face API Key (optional)", type="password")

        input_method = st.radio(
            "Input Method",
            ["Paste Complete Answer Sheet", "Enter Question Paper & Student Answers Separately"],
            index=0
        )

        if input_method == "Paste Complete Answer Sheet":
            assessment_data = st.text_area("Paste the assessment answer sheet here", height=300)
            subject = st.text_input("Subject", value="")

            if st.button("Analyze and Generate Roadmap", type="primary"):
                if assessment_data:
                    with st.spinner("Analyzing assessment data..."):
                        if subject and not re.search(r'Subject:', assessment_data):
                            assessment_data = f"Subject: {subject}\n\n{assessment_data}"

                        cleaned_data = remove_personal_info(assessment_data)
                        st.subheader("Cleaned Assessment Data")
                        st.text_area("Cleaned Data", value=cleaned_data, height=150, disabled=True)

                        analysis_result = generate_roadmap(cleaned_data, grade, api_key)

                        if analysis_result:
                            st.session_state.analysis_result = analysis_result
                            st.session_state.grade = grade
                            st.success("Analysis complete! See results in the 'Analysis Results' tab.")
                            st.query_params.update(tab="results")
                        else:
                            st.error("Failed to generate analysis.")
                else:
                    st.warning("Please enter assessment data to analyze.")

        else:
            st.subheader("Step 1: Paste Question Paper with Answer Key")
            question_paper = st.text_area("Paste the question paper here", height=200)

            if question_paper:
                subject_match = re.search(r'Subject:\s*([^\n]+)', question_paper)
                subject = subject_match.group(1) if subject_match else ""
                if not subject:
                    subject = st.text_input("Subject", value="")
                else:
                    st.info(f"Detected subject: {subject}")

                questions, correct_answers = parse_question_paper(question_paper)
                if questions:
                    st.session_state.questions = questions
                    st.session_state.correct_answers = correct_answers
                    st.success(f"Found {len(questions)} questions with {len(correct_answers)} answer keys.")
                else:
                    st.warning("No questions detected.")

            st.subheader("Step 2: Enter Student's Answers")

            if st.session_state.questions:
                st.markdown("### Option 1: Paste All Answers")
                bulk_answers = st.text_area("Paste answers (e.g. 1. A\\n2. B\\n3. C)", height=200)

                if bulk_answers:
                    answer_lines = bulk_answers.strip().split('\n')
                    for line in answer_lines:
                        match = re.match(r'(\d+)[.)\s-]*([A-E])', line.strip(), re.IGNORECASE)
                        if match:
                            q_num, ans = match.group(1), match.group(2).upper()
                            st.session_state.student_answers[q_num] = ans
                    st.success("Answers parsed and loaded!")

                st.markdown("---")
                st.markdown("### Option 2: Fill Answers Manually")

                for q in st.session_state.questions:
                    q_num = q['number']
                    q_text = q['text']
                    truncated_text = q_text[:50] + "..." if len(q_text) > 50 else q_text
                    st.markdown(f"**Q{q_num}:** {truncated_text}")

                    default_idx = "ABCDE".find(st.session_state.student_answers.get(q_num, 'A'))
                    default_idx = default_idx if default_idx >= 0 else 0

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        student_answer = st.radio(
                            f"Student's answer for Q{q_num}",
                            options=['A', 'B', 'C', 'D', 'E'],
                            index=default_idx,
                            horizontal=True,
                            key=f"answer_{q_num}"
                        )

                    with col2:
                        correct = st.session_state.correct_answers.get(q_num)
                        if correct:
                            st.markdown(f"Correct Answer: **{correct}**")
                            st.success("Correct!" if student_answer == correct else "Incorrect")
                        else:
                            st.info("No answer key available")

                    st.session_state.student_answers[q_num] = student_answer
                    st.divider()

                if st.button("Generate Assessment Analysis", type="primary"):
                    assessment_lines = [f"Subject: {subject}", ""]
                    correct_count = 0
                    total_questions = len(st.session_state.questions)

                    for q in st.session_state.questions:
                        q_num = q['number']
                        if q_num in st.session_state.student_answers:
                            student_ans = st.session_state.student_answers[q_num]
                            correct_ans = st.session_state.correct_answers.get(q_num)

                            if correct_ans:
                                is_correct = student_ans == correct_ans
                                status = "(Correct)" if is_correct else "(Incorrect)"
                                if is_correct:
                                    correct_count += 1
                            else:
                                status = ""

                            assessment_lines.append(f"Question {q_num}: {student_ans} {status}")

                    if st.session_state.correct_answers:
                        score_percent = round((correct_count / total_questions) * 100)
                        assessment_lines.append("")
                        assessment_lines.append(f"Total Score: {correct_count}/{total_questions} ({score_percent}%)")

                    assessment_text = "\n".join(assessment_lines)

                    with st.spinner("Analyzing assessment data..."):
                        analysis_result = generate_roadmap(assessment_text, grade, api_key)

                        if analysis_result:
                            st.session_state.analysis_result = analysis_result
                            st.session_state.grade = grade
                            st.success("Analysis complete! See results in the 'Analysis Results' tab.")
                            st.query_params.update(tab="results")
                        else:
                            st.error("Failed to generate analysis.")
            else:
                st.info("Please paste a question paper first to enter student answers.")

    with col2:
        st.header("Sample Input Formats")
        # [Assume unchanged sample inputs and info content here]

with results_tab:
    st.header("Analysis Results")
    # [Assume this section is unchanged and continues to show results]

st.markdown("---")
st.caption("Disclaimer: This tool is for educational purposes only.")
