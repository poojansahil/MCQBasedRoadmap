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

def infer_topic(question_text):
    question_text = question_text.lower()
    if any(word in question_text for word in ["triangle", "circle", "angle", "geometry"]):
        return "Geometry"
    if any(word in question_text for word in ["equation", "algebra", "solve", "expression"]):
        return "Algebra"
    if any(word in question_text for word in ["force", "motion", "energy", "velocity"]):
        return "Physics"
    if any(word in question_text for word in ["cell", "photosynthesis", "nucleus", "organism"]):
        return "Biology"
    if any(word in question_text for word in ["democracy", "constitution", "government"]):
        return "Civics"
    if any(word in question_text for word in ["gdp", "economy", "trade", "business"]):
        return "Economics"
    return "General"

def fallback_processing(assessment_data, grade):
    question_lines = re.findall(r'Question\s*(\d+):\s*([A-E])\s*(\(Correct\)|\(Incorrect\))?', assessment_data, re.IGNORECASE)
    topic_mistakes = {}
    topic_corrects = {}
    for match in question_lines:
        q_num, student_ans, correctness = match
        q_text_search = re.search(rf'Question {q_num}: (.*)', assessment_data)
        q_text = q_text_search.group(1) if q_text_search else ""
        topic = infer_topic(q_text)
        if correctness.lower() == '(incorrect)':
            topic_mistakes[topic] = topic_mistakes.get(topic, 0) + 1
        else:
            topic_corrects[topic] = topic_corrects.get(topic, 0) + 1

    strengths = [f"Strong understanding of {topic}" for topic, count in topic_corrects.items() if count > topic_mistakes.get(topic, 0)]
    weaknesses = [f"Needs improvement in {topic}" for topic, count in topic_mistakes.items() if count >= topic_corrects.get(topic, 0)]

    smart_goals = []
    for topic in weaknesses:
        topic_name = topic.replace("Needs improvement in ", "")
        smart_goals.append({
            "goal": f"Revise core concepts of {topic_name}",
            "measurement": "Complete 30 practice questions and review mistakes",
            "timeline": "2 weeks",
            "area": topic_name
        })

    if not smart_goals:
        smart_goals.append({
            "goal": "Continue practicing to maintain strengths",
            "measurement": "Score above 90% in next mock test",
            "timeline": "1 week",
            "area": "General"
        })

    return {"strengths": strengths, "weaknesses": weaknesses, "smart_goals": smart_goals}

# generate_roadmap, parse_question_paper, create_timeline, and the UI code remain unchanged
