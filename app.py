import streamlit as st
import pandas as pd
import re
import json
import requests
from datetime import datetime, timedelta
import time

# Set page configuration
st.set_page_config(
    page_title="MCQ Assessment Analyzer",
    page_icon="📊",
    layout="wide"
)

# App title and description
st.title("📊 MCQ Assessment Analyzer")
st.markdown("""
This application analyzes a student's MCQ assessment answers and generates a personalized roadmap with SMART goals.
""")

# Initialize session state variables
if 'student_answers' not in st.session_state:
    st.session_state.student_answers = {}
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'correct_answers' not in st.session_state:
    st.session_state.correct_answers = {}

# Function to remove personal information
def remove_personal_info(text):
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REMOVED]', text)
    
    # Remove phone numbers
    text = re.sub(r'\b(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b', '[PHONE REMOVED]', text)
    
    # Remove names (this is a simplified approach - might need refinement)
    text = re.sub(r'Name:\s*[A-Za-z\s]+', 'Name: [NAME REMOVED]', text)
    
    # Remove student IDs
    text = re.sub(r'ID:\s*[A-Za-z0-9-]+', 'ID: [ID REMOVED]', text)
    text = re.sub(r'Student ID:\s*[A-Za-z0-9-]+', 'Student ID: [ID REMOVED]', text)
    
    return text

# Function to try multiple APIs with fallback
def try_multiple_apis(prompt, api_key=None):
    # List of API configurations to try in order
    api_configs = [
        {
            "name": "Hugging Face - TinyLlama",
            "url": "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "headers": {"Authorization": f"Bearer {api_key}"} if api_key else {},
            "payload": {"inputs": prompt},
            "response_handler": lambda r: r.json()[0]["generated_text"]
        },
        {
            "name": "Hugging Face - FLAN-T5-XXL",
            "url": "https://api-inference.huggingface.co/models/google/flan-t5-xxl",
            "headers": {"Authorization": f"Bearer {api_key}"} if api_key else {},
            "payload": {"inputs": prompt},
            "response_handler": lambda r: r.json()[0]["generated_text"]
        },
        {
            "name": "Hugging Face - OPT",
            "url": "https://api-inference.huggingface.co/models/facebook/opt-350m",
            "headers": {"Authorization": f"Bearer {api_key}"} if api_key else {},
            "payload": {"inputs": prompt},
            "response_handler": lambda r: r.json()[0]["generated_text"]
        },
        {
            "name": "Hugging Face - BLOOM",
            "url": "https://api-inference.huggingface.co/models/bigscience/bloom-560m",
            "headers": {"Authorization": f"Bearer {api_key}"} if api_key else {},
            "payload": {"inputs": prompt},
            "response_handler": lambda r: r.json()[0]["generated_text"]
        }
    ]
    
    last_error = None
    
    # Try each API in sequence
    for config in api_configs:
        try:
            st.info(f"Trying {config['name']}...")
            
            response = requests.post(
                config["url"],
                headers=config["headers"],
                json=config["payload"],
                timeout=30  # 30 second timeout
            )
            
            if response.status_code == 200:
                try:
                    result = config["response_handler"](response)
                    st.success(f"Successfully got response from {config['name']}")
                    return result
                except Exception as e:
                    st.warning(f"Error processing response from {config['name']}: {str(e)}")
                    last_error = e
                    continue
            else:
                st.warning(f"API {config['name']} returned status code {response.status_code}")
                last_error = Exception(f"Status code: {response.status_code}")
                continue
                
        except Exception as e:
            st.warning(f"Error with {config['name']}: {str(e)}")
            last_error = e
            continue
    
    # If we get here, all APIs failed
    raise Exception(f"All APIs failed. Last error: {str(last_error)}")

# Function to generate analysis and roadmap 
def generate_roadmap(assessment_data, grade, api_key=None):
    try:
        # Prepare prompt for the AI
        prompt = f"""
        I need to analyze a student's MCQ assessment answers and create a personalized roadmap. 
        Here's the information:
        
        Student Grade: {grade}
        Assessment Data: {assessment_data}
        
        Based on their performance, please:
        1. Identify strengths and weaknesses
        2. Create 3-5 SMART goals (Specific, Measurable, Achievable, Relevant, Time-bound)
        3. Suggest a timeline for each goal
        
        Format your response as JSON with the following structure:
        {{
            "strengths": ["strength1", "strength2", ...],
            "weaknesses": ["weakness1", "weakness2", ...],
            "smart_goals": [
                {{
                    "goal": "Specific goal description",
                    "measurement": "How progress will be measured",
                    "timeline": "Suggested timeline (e.g., '2 weeks')",
                    "area": "Subject area"
                }},
                ...
            ]
        }}
        """
        
        # Try multiple APIs with fallback
        try:
            response_text = try_multiple_apis(prompt, api_key)
            
            # Try to extract JSON from the response
            try:
                # First try to find JSON block in markdown format
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|({[\s\S]*})', response_text)
                if json_match:
                    json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
                    analysis = json.loads(json_str)
                else:
                    # If no JSON format is found, try to extract it from the plain text
                    try:
                        # Look for content between curly braces
                        json_match = re.search(r'{.*}', response_text, re.DOTALL)
                        if json_match:
                            analysis = json.loads(json_match.group(0))
                        else:
                            raise Exception("No JSON found in response")
                    except:
                        # If all extraction attempts fail, use fallback
                        st.warning("Failed to parse AI response. Using simplified analysis.")
                        return fallback_processing(assessment_data, grade)
            except Exception as e:
                st.warning(f"Error parsing response: {str(e)}. Using simplified analysis.")
                return fallback_processing(assessment_data, grade)
            
            # Verify the analysis has the expected structure
            if not all(key in analysis for key in ["strengths", "weaknesses", "smart_goals"]):
                st.warning("AI response missing required fields. Using simplified analysis.")
                return fallback_processing(assessment_data, grade)
                
            return analysis
            
        except Exception as e:
            st.warning(f"All APIs failed: {str(e)}. Using simplified analysis.")
            return fallback_processing(assessment_data, grade)
        
    except Exception as e:
        st.error(f"Error generating roadmap: {str(e)}")
        return fallback_processing(assessment_data, grade)

# Fallback function to generate basic analysis when API fails
def fallback_processing(assessment_data, grade):
    # Count correct and incorrect answers
    correct_count = len(re.findall(r'\(Correct\)', assessment_data, re.IGNORECASE))
    incorrect_count = len(re.findall(r'\(Incorrect\)', assessment_data, re.IGNORECASE))
    
    # Extract subject if available
    subject_match = re.search(r'Subject:\s*([^\n]+)', assessment_data)
    subject = subject_match.group(1) if subject_match else "General"
    
    # Create a basic analysis
    if correct_count > incorrect_count:
        strengths = [f"Good overall performance in {subject}"]
        weaknesses = ["Some areas need improvement"]
    else:
        strengths = ["Some questions answered correctly"]
        weaknesses = [f"Need to improve overall performance in {subject}"]
    
    # Generate basic SMART goals
    smart_goals = [
        {
            "goal": f"Review and understand all incorrect answers from the assessment",
            "measurement": "Complete practice problems related to incorrect answers",
            "timeline": "1 week",
            "area": subject
        },
        {
            "goal": f"Master the concepts covered in the assessment",
            "measurement": "Score at least 90% on a similar practice test",
            "timeline": "2 weeks",
            "area": subject
        },
        {
            "goal": f"Expand knowledge beyond the assessment topics",
            "measurement": "Complete additional exercises on related topics",
            "timeline": "3 weeks",
            "area": subject
        }
    ]
    
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "smart_goals": smart_goals
    }

# Function to create a timeline with specific dates
def create_timeline(goals):
    today = datetime.now()
    timeline_goals = []
    
    current_date = today
    for goal in goals:
        timeline_str = goal["timeline"]
        
        # Parse the timeline string to get number of weeks/days
        if "week" in timeline_str.lower():
            num_weeks = int(re.search(r'(\d+)', timeline_str).group(1))
            end_date = current_date + timedelta(weeks=num_weeks)
        elif "day" in timeline_str.lower():
            num_days = int(re.search(r'(\d+)', timeline_str).group(1))
            end_date = current_date + timedelta(days=num_days)
        elif "month" in timeline_str.lower():
            num_months = int(re.search(r'(\d+)', timeline_str).group(1))
            end_date = current_date + timedelta(days=num_months*30)  # Approximation
        else:
            # Default to 2 weeks if parsing fails
            end_date = current_date + timedelta(weeks=2)
        
        goal_with_dates = goal.copy()
        goal_with_dates["start_date"] = current_date.strftime("%Y-%m-%d")
        goal_with_dates["end_date"] = end_date.strftime("%Y-%m-%d")
        
        timeline_goals.append(goal_with_dates)
        current_date = end_date + timedelta(days=1)  # Start next goal after the previous one
    
    return timeline_goals

# Function to parse question paper
def parse_question_paper(text):
    questions = []
    answers = {}
    
    # Use regex to find questions and their answers
    question_pattern = r'(?:Question|Q)\s*(\d+)[.:]\s*(.*?)(?=(?:Question|Q)\s*\d+|$)'
    
    # Find all matches
    matches = re.finditer(question_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        question_num = match.group(1)
        question_text = match.group(2).strip()
        
        # Look for answer key in the question text
        answer_match = re.search(r'(?:Answer|Ans|Key):\s*([A-E])', question_text, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            # Remove the answer key from the question text
            question_text = re.sub(r'(?:Answer|Ans|Key):\s*[A-E]', '', question_text).strip()
            answers[question_num] = answer
        
        questions.append({
            'number': question_num,
            'text': question_text
        })
    
    return questions, answers

# Tabs for different input methods
input_tab, results_tab = st.tabs(["Input Data", "Analysis Results"])

with input_tab:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Assessment Data")
        
        # Grade selection
        grade = st.selectbox(
            "Student Grade Level",
            options=["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "College"]
        )
        
        # API Key input (optional)
        api_key = st.text_input("Hugging Face API Key (optional)", type="password")
        if not api_key:
            st.info("You can use the app without an API key, but using your own key may improve reliability.")
        
        # Input method selection
        input_method = st.radio(
            "Input Method",
            options=["Paste Complete Answer Sheet", "Enter Question Paper & Student Answers Separately"],
            index=0
        )
        
        if input_method == "Paste Complete Answer Sheet":
            # Assessment data input
            assessment_data = st.text_area(
                "Paste the assessment answer sheet here (any personal information will be removed)",
                height=300,
                placeholder="Example:\nName: John Doe\nGrade: 10\nSubject: Mathematics\n\nQuestion 1: A (Correct)\nQuestion 2: B (Incorrect)\nQuestion 3: C (Correct)\n..."
            )
            
            # Subject input
            subject = st.text_input("Subject", value="")
            
            if st.button("Analyze and Generate Roadmap", type="primary"):
                if assessment_data:
                    with st.spinner("Analyzing assessment data..."):
                        # Add subject if provided
                        if subject and not re.search(r'Subject:', assessment_data):
                            assessment_data = f"Subject: {subject}\n\n{assessment_data}"
                        
                        # Remove personal information
                        cleaned_data = remove_personal_info(assessment_data)
                        
                        # Show cleaned data
                        st.subheader("Cleaned Assessment Data")
                        st.text_area("Cleaned Data", value=cleaned_data, height=150, disabled=True)
                        
                        # Generate roadmap
                        analysis_result = generate_roadmap(cleaned_data, grade, api_key)
                        
                        if analysis_result:
                            st.session_state.analysis_result = analysis_result
                            st.session_state.grade = grade
                            st.success("Analysis complete! See results in the 'Analysis Results' tab.")
                            # Switch to results tab
                            st.experimental_set_query_params(tab="results")
                        else:
                            st.error("Failed to generate analysis. Please check your input data and try again.")
                else:
                    st.warning("Please enter assessment data to analyze.")
        
        else:  # Enter Question Paper & Student Answers Separately
            st.subheader("Step 1: Paste Question Paper with Answer Key")
            
            question_paper = st.text_area(
                "Paste the question paper here",
                height=200,
                placeholder="Example:\nSubject: Mathematics\n\nQuestion 1: What is 2+2?\nA. 3\nB. 4\nC. 5\nD. 6\nAnswer: B\n\nQuestion 2: What is the square root of 9?\nA. 2\nB. 3\nC. 4\nD. 5\nAnswer: B"
            )
            
            if question_paper:
                # Extract subject
                subject_match = re.search(r'Subject:\s*([^\n]+)', question_paper)
                subject = subject_match.group(1) if subject_match else ""
                
                if not subject:
                    subject = st.text_input("Subject", value="")
                else:
                    st.info(f"Detected subject: {subject}")
                
                # Parse question paper
                questions, correct_answers = parse_question_paper(question_paper)
                
                if questions:
                    st.session_state.questions = questions
                    st.session_state.correct_answers = correct_answers
                    st.success(f"Found {len(questions)} questions with {len(correct_answers)} answer keys.")
                else:
                    st.warning("No questions detected. Please check your question paper format.")
            
            st.subheader("Step 2: Enter Student's Answers")
            
            if st.session_state.questions:
                # Display form for student answers
                for q in st.session_state.questions:
                    q_num = q['number']
                    q_text = q['text']
                    
                    # Display question summary
                    truncated_text = q_text[:50] + "..." if len(q_text) > 50 else q_text
                    st.markdown(f"**Q{q_num}:** {truncated_text}")
                    
                    # Multi-choice input
                    if q_num in st.session_state.student_answers:
                        default_idx = "ABCDE".find(st.session_state.student_answers[q_num])
                        default_idx = default_idx if default_idx >= 0 else 0
                    else:
                        default_idx = 0
                        
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
                        if q_num in st.session_state.correct_answers:
                            correct = st.session_state.correct_answers[q_num]
                            is_correct = student_answer == correct
                            st.markdown(f"Correct Answer: **{correct}**")
                            if is_correct:
                                st.success("Correct!")
                            else:
                                st.error("Incorrect")
                        else:
                            st.info("No answer key available")
                    
                    # Store answer in session state
                    st.session_state.student_answers[q_num] = student_answer
                    
                    st.divider()
                
                if st.button("Generate Assessment Analysis", type="primary"):
                    # Prepare assessment data
                    assessment_lines = [f"Subject: {subject}", ""]
                    
                    correct_count = 0
                    total_questions = len(st.session_state.questions)
                    
                    for q in st.session_state.questions:
                        q_num = q['number']
                        if q_num in st.session_state.student_answers:
                            student_ans = st.session_state.student_answers[q_num]
                            correct_ans = st.session_state.correct_answers.get(q_num, None)
                            
                            if correct_ans:
                                is_correct = student_ans == correct_ans
                                status = "(Correct)" if is_correct else "(Incorrect)"
                                if is_correct:
                                    correct_count += 1
                            else:
                                status = ""
                                
                            assessment_lines.append(f"Question {q_num}: {student_ans} {status}")
                    
                    # Add score if we have correct answers
                    if st.session_state.correct_answers:
                        score_percent = round((correct_count / total_questions) * 100)
                        assessment_lines.append("")
                        assessment_lines.append(f"Total Score: {correct_count}/{total_questions} ({score_percent}%)")
                    
                    assessment_text = "\n".join(assessment_lines)
                    
                    with st.spinner("Analyzing assessment data..."):
                        # Generate roadmap
                        analysis_result = generate_roadmap(assessment_text, grade, api_key)
                        
                        if analysis_result:
                            st.session_state.analysis_result = analysis_result
                            st.session_state.grade = grade
                            st.success("Analysis complete! See results in the 'Analysis Results' tab.")
                            # Switch to results tab
                            st.experimental_set_query_params(tab="results")
                        else:
                            st.error("Failed to generate analysis. Please check your input data and try again.")
            else:
                st.info("Please paste a question paper first to enter student answers.")
    
    with col2:
        st.header("Sample Input Formats")
        
        with st.expander("Sample Question Paper Format"):
            st.code("""
Subject: Mathematics

Question 1: What is 2+2?
A. 3
B. 4
C. 5
D. 6
Answer: B

Question 2: What is the square root of 9?
A. 2
B. 3
C. 4
D. 5
Answer: B

Question 3: Solve for x: 3x + 5 = 14
A. x = 3
B. x = 4
C. x = 5
D. x = 6
Answer: A
            """)
        
        with st.expander("Sample Complete Answer Sheet Format"):
            st.code("""
Name: John Doe
ID: S12345
Grade: 8
Subject: Science

Question 1: B (Correct)
Question 2: C (Incorrect)
Question 3: A (Correct)
Question 4: D (Correct)
Question 5: A (Incorrect)

Total Score: 3/5 (60%)
            """)
        
        st.header("How It Works")
        st.markdown("""
        1. **Input your data** - Either paste a complete answer sheet or enter a question paper and student answers separately
        2. **AI analysis** - The app uses multiple open-source AI models to analyze the student's performance
        3. **Fallback system** - If one API fails, the app automatically tries others
        4. **Personalized roadmap** - The analysis generates SMART goals with specific timelines
        5. **Privacy protection** - Personal information is automatically removed
        
        For best results, include:
        - The subject area
        - Correct/incorrect markings for each answer
        - Grade level of the student
        """)

with results_tab:
    st.header("Analysis Results")
    
    if 'analysis_result' in st.session_state:
        analysis = st.session_state.analysis_result
        
        # Display strengths and weaknesses
        col_strength, col_weakness = st.columns(2)
        
        with col_strength:
            st.subheader("💪 Strengths")
            for strength in analysis.get("strengths", []):
                st.markdown(f"- {strength}")
        
        with col_weakness:
            st.subheader("🎯 Areas for Improvement")
            for weakness in analysis.get("weaknesses", []):
                st.markdown(f"- {weakness}")
        
        # Create timeline with specific dates
        smart_goals = analysis.get("smart_goals", [])
        timeline_goals = create_timeline(smart_goals)
        
        # Display SMART goals with timeline
        st.subheader("📝 SMART Goals and Timeline")
        
        # Convert to DataFrame for better display
        if timeline_goals:
            df = pd.DataFrame(timeline_goals)
            # Reorder and rename columns for better display
            df = df[["area", "goal", "measurement", "start_date", "end_date"]]
            df.columns = ["Subject Area", "Goal", "Measurement", "Start Date", "End Date"]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Display interactive timeline
            st.subheader("📅 Visual Timeline")
            
            # Create timeline chart using Streamlit
            timeline_df = pd.DataFrame({
                "Goal": [f"{g['area']}: {g['goal'][:30]}..." if len(g['goal']) > 30 else f"{g['area']}: {g['goal']}" for g in timeline_goals],
                "Start": [datetime.strptime(g["start_date"], "%Y-%m-%d") for g in timeline_goals],
                "End": [datetime.strptime(g["end_date"], "%Y-%m-%d") for g in timeline_goals]
            })
            
            st.bar_chart(
                timeline_df.set_index("Goal"),
                y=["Start", "End"],
                height=300
            )
            
            # Export options
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Roadmap as CSV",
                    df.to_csv(index=False).encode('utf-8'),
                    "student_roadmap.csv",
                    "text/csv",
                    key='download-csv'
                )
            
            with col2:
                # Create a printable version for PDF
                markdown_text = "# Student Learning Roadmap\n\n"
                markdown_text += f"**Date Generated:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
                
                markdown_text += "## Strengths\n"
                for strength in analysis.get("strengths", []):
                    markdown_text += f"* {strength}\n"
                
                markdown_text += "\n## Areas for Improvement\n"
                for weakness in analysis.get("weaknesses", []):
                    markdown_text += f"* {weakness}\n"
                
                markdown_text += "\n## SMART Goals and Timeline\n\n"
                for i, goal in enumerate(timeline_goals, 1):
                    markdown_text += f"### Goal {i}: {goal['goal']}\n"
                    markdown_text += f"**Subject Area:** {goal['area']}\n"
                    markdown_text += f"**Measurement:** {goal['measurement']}\n"
                    markdown_text += f"**Timeline:** {goal['start_date']} to {goal['end_date']}\n\n"
                
                st.download_button(
                    "📄 Download as Markdown/Text",
                    markdown_text,
                    "student_roadmap.md",
                    "text/plain",
                    key='download-md'
                )
        else:
            st.info("No SMART goals generated. Please try again with different assessment data.")
    else:
        st.info("Enter assessment data in the 'Input Data' tab and click 'Analyze' to generate a personalized roadmap.")

# Add footer with disclaimer
st.markdown("---")
st.caption("Disclaimer: This tool is for educational purposes only. The roadmap generated is based on AI analysis and should be reviewed by an education professional.")

# Sidebar with information
with st.sidebar:
    st.header("About This App")
    st.markdown("""
    ### MCQ Assessment Analyzer

    This application helps educators and students analyze multiple-choice assessment results and create personalized learning roadmaps with SMART goals.
    
    **Key Features:**
    - Multiple input methods
    - Personal information removal
    - Resilient API fallback system
    - SMART goal generation
    - Visual timeline
    - Multiple export options
    
    **Open-Source AI Integration:**
    The app uses multiple free-tier LLM APIs for analysis, with an automatic fallback system if one API isn't working.
    
    **Privacy First:**
    All personal data is automatically removed before processing.
    """)
    
    st.markdown("---")
    st.subheader("Understanding SMART Goals")
    st.markdown("""
    **S**pecific: Clearly defined objectives  
    **M**easurable: Progress can be tracked  
    **A**chievable: Realistic for the student's level  
    **R**elevant: Related to areas needing improvement  
    **T**ime-bound: With specific completion dates
    """)