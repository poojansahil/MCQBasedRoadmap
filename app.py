import streamlit as st
import pandas as pd
import re
import json
import requests
from datetime import datetime, timedelta

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

# Function to generate analysis and roadmap using Hugging Face's API
def generate_roadmap(assessment_data, grade):
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
        
        # API URL for Hugging Face Inference API (using a free open model)
        # Using TinyLlama as an example, but you can change to another free model
        API_URL = "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        
        # If you have a Hugging Face API token (free to create an account)
        # You can uncomment this line and add your token
        # headers = {"Authorization": f"Bearer YOUR_HUGGING_FACE_TOKEN"}
        
        # For completely free usage without token (with limitations)
        headers = {}
        
        # Make API request
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": prompt}
        )
        
        if response.status_code != 200:
            # Fallback to local processing if API fails
            st.warning("API request failed. Falling back to local processing.")
            return fallback_processing(assessment_data, grade)
            
        response_text = response.json()[0]["generated_text"]
        
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

# Main content
col1, col2 = st.columns(2)

with col1:
    st.header("Input Assessment Data")
    
    # Grade selection
    grade = st.selectbox(
        "Student Grade Level",
        options=["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "College"]
    )
    
    # Choose AI backend
    ai_option = st.radio(
        "Choose AI Backend",
        options=["Hugging Face (Free Tier - No API Key)", 
                 "Hugging Face (With API Key)"],
        index=0
    )
    
    # API Key input if selected
    if ai_option == "Hugging Face (With API Key)":
        api_key = st.text_input("Enter Hugging Face API Key", type="password")
        if not api_key:
            st.info("You can get a free Hugging Face API key by creating an account at huggingface.co")
    
    # Model selection for Hugging Face
    if "Hugging Face" in ai_option:
        hf_model = st.selectbox(
            "Select Hugging Face Model",
            options=[
                "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "facebook/opt-350m",
                "EleutherAI/pythia-410m",
                "bigscience/bloom-560m"
            ],
            index=0
        )
    
    # Assessment data input
    st.subheader("Assessment Details")
    assessment_data = st.text_area(
        "Paste the assessment answer sheet here (any personal information will be removed)",
        height=300,
        placeholder="Example:\nName: John Doe\nGrade: 10\nSubject: Mathematics\n\nQuestion 1: A (Correct)\nQuestion 2: B (Incorrect)\nQuestion 3: C (Correct)\n..."
    )
    
    if st.button("Analyze and Generate Roadmap", type="primary"):
        if assessment_data:
            with st.spinner("Analyzing assessment data..."):
                # Remove personal information
                cleaned_data = remove_personal_info(assessment_data)
                
                # For debugging - show cleaned data
                st.subheader("Cleaned Assessment Data (Personal Info Removed)")
                st.text_area("Cleaned Data", value=cleaned_data, height=150, disabled=True)
                
                # Generate roadmap
                analysis_result = generate_roadmap(cleaned_data, grade)
                
                if analysis_result:
                    st.session_state.analysis_result = analysis_result
                    st.session_state.grade = grade
                    st.success("Analysis complete! See results in the right panel.")
                else:
                    st.error("Failed to generate analysis. Please check your input data and try again.")
        else:
            st.warning("Please enter assessment data to analyze.")

# Results display
with col2:
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
            
            # Export button
            st.download_button(
                "Download Roadmap as CSV",
                df.to_csv(index=False).encode('utf-8'),
                "student_roadmap.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No SMART goals generated. Please try again with different assessment data.")
    else:
        st.info("Enter assessment data and click 'Analyze' to generate a personalized roadmap.")

# Add footer with disclaimer
st.markdown("---")
st.caption("Disclaimer: This tool is for educational purposes only. The roadmap generated is based on AI analysis and should be reviewed by an education professional.")

# Sidebar with instructions
with st.sidebar:
    st.header("Instructions")
    st.markdown("""
    ### How to use this tool:
    
    1. **Select the student's grade level**
    2. **Choose AI backend**:
       - Hugging Face (free, no API key required)
       - Hugging Face with your own API key
    3. **Enter the assessment data** including:
       - Subject(s) covered
       - Questions and answers
       - Correct/incorrect markings
    4. **Click 'Analyze and Generate Roadmap'**
    5. **Review the results** in the right panel
    
    ### Sample Input Format:
    ```
    Subject: Mathematics
    
    Question 1: A (Correct)
    Question 2: B (Incorrect)
    Question 3: C (Correct)
    Question 4: A (Incorrect)
    Question 5: D (Correct)
    
    Total Score: 3/5
    ```
    
    ### Notes:
    - All personal information will be automatically removed
    - For best results, include specific details about questions and correct/incorrect answers
    - The free tier models may have limited quality compared to premium models
    - If the AI fails to generate a proper analysis, a fallback system will provide basic recommendations
    """)
    
    st.markdown("---")
    st.subheader("About")
    st.markdown("""
    This app uses Hugging Face's free inference API to analyze student performance on MCQ assessments and generate personalized learning roadmaps.
    
    The roadmap includes SMART goals that are:
    - **Specific**: Clearly defined objectives
    - **Measurable**: Progress can be tracked
    - **Achievable**: Realistic for the student's level
    - **Relevant**: Related to areas needing improvement
    - **Time-bound**: With suggested completion dates
    """)