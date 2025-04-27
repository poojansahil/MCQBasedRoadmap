import streamlit as st
import pandas as pd
import json
import os
import time
from openai import OpenAI
import matplotlib.pyplot as plt

st.set_page_config(page_title="Student Performance Analyzer", layout="wide")

def analyze_answers(client, answer_key, student_answers, subject):
    """
    Use OpenAI API to analyze student answers and generate improvement roadmap
    """
    prompt = f"""
    As an educational assessment expert, analyze the following student answers against the answer key for {subject}.
    
    Answer Key:
    {answer_key}
    
    Student Answers:
    {student_answers}
    
    Provide a comprehensive analysis in JSON format with the following structure:
    {{
        "overall_performance": "Overall assessment of performance with score percentage",
        "strengths": ["List of specific strengths identified", "..."],
        "weaknesses": ["List of specific areas needing improvement", "..."],
        "concept_mastery": {{
            "concept1": "percentage mastery",
            "concept2": "percentage mastery",
            "...": "..."
        }},
        "improvement_roadmap": [
            {{
                "goal": "Specific, measurable goal",
                "timeline": "Suggested timeline (in weeks)",
                "resources": "Recommended resources",
                "action_items": ["Specific actions to take", "..."]
            }},
            {{
                "...": "..."
            }}
        ]
    }}
    
    Focus on providing actionable insights and a personalized roadmap for improvement.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are an educational assessment expert."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error analyzing answers: {str(e)}")
        return None

def create_roadmap_table(roadmap_data):
    """Convert roadmap data to a pandas DataFrame"""
    df = pd.DataFrame(roadmap_data)
    return df

def display_concept_mastery(concept_mastery):
    """Create a bar chart for concept mastery"""
    concepts = list(concept_mastery.keys())
    mastery_values = [float(v.strip('%')) if isinstance(v, str) and '%' in v 
                     else float(v) if isinstance(v, (int, float)) 
                     else 0 for v in concept_mastery.values()]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(concepts, mastery_values, color='skyblue')
    ax.set_xlabel('Mastery Level (%)')
    ax.set_title('Concept Mastery Analysis')
    ax.set_xlim(0, 100)
    
    # Add the percentage text on the bars
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, 
                f"{mastery_values[i]:.1f}%", va='center')
    
    return fig

def main():
    st.title("Student Performance Analyzer")
    
    # API Key input
    api_key = st.text_input("Enter OpenAI API Key", type="password", key="api_key_input")
    
    # Subject selection
    subject = st.selectbox("Select Subject", ["Mathematics", "Science", "English", "History", "Computer Science", "Other"], key="subject_select")
    if subject == "Other":
        subject = st.text_input("Enter Subject Name", key="custom_subject_input")
    
    # Answer key and student answers input
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Answer Key")
        st.caption("Enter the correct answers with question numbers")
        answer_key = st.text_area("Format: Q1: [answer], Q2: [answer], etc.", height=300, key="answer_key_area")
    
    with col2:
        st.subheader("Student Answers")
        st.caption("Enter the student's answers with question numbers")
        student_answers = st.text_area("Format: Q1: [answer], Q2: [answer], etc.", height=300, key="student_answers_area")
    
    analyze_button = st.button("Analyze Performance", key="analyze_button")
    
    if analyze_button and api_key and answer_key and student_answers:
        with st.spinner("Analyzing student performance..."):
            try:
                # Initialize OpenAI client
                client = OpenAI(api_key=api_key)
                
                # Analyze the answers
                analysis_results = analyze_answers(client, answer_key, student_answers, subject)
                
                if analysis_results:
                    # Display results
                    st.success("Analysis completed!")
                    
                    # Overall performance
                    st.header("Overall Performance")
                    st.write(analysis_results["overall_performance"])
                    
                    # Strengths and weaknesses
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Strengths")
                        for strength in analysis_results["strengths"]:
                            st.markdown(f"✅ {strength}")
                    
                    with col2:
                        st.subheader("Areas for Improvement")
                        for weakness in analysis_results["weaknesses"]:
                            st.markdown(f"🔍 {weakness}")
                    
                    # Concept mastery visualization
                    st.subheader("Concept Mastery Analysis")
                    fig = display_concept_mastery(analysis_results["concept_mastery"])
                    st.pyplot(fig)
                    
                    # Improvement roadmap
                    st.header("Personalized Improvement Roadmap")
                    roadmap_df = create_roadmap_table(analysis_results["improvement_roadmap"])
                    
                    # Format the action items column to display as bullet points
                    if 'action_items' in roadmap_df.columns:
                        roadmap_df['action_items'] = roadmap_df['action_items'].apply(
                            lambda items: '\n'.join([f"• {item}" for item in items]) if isinstance(items, list) else items
                        )
                    
                    st.table(roadmap_df)
                    
                    # Download options
                    st.subheader("Download Analysis")
                    
                    # Convert to CSV
                    csv = roadmap_df.to_csv(index=False)
                    st.download_button(
                        label="Download Roadmap as CSV",
                        data=csv,
                        file_name="improvement_roadmap.csv",
                        mime="text/csv",
                        key="download_csv_button"
                    )
                    
                    # Convert full analysis to JSON
                    json_data = json.dumps(analysis_results, indent=2)
                    st.download_button(
                        label="Download Full Analysis as JSON",
                        data=json_data,
                        file_name="student_analysis.json",
                        mime="application/json",
                        key="download_json_button"
                    )
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    
    # Instructions if fields are empty
    if not api_key or not answer_key or not student_answers:
        st.info("Please fill in all fields to analyze student performance.")
    
    # Add footer
    st.markdown("---")
    st.caption("Student Performance Analyzer uses OpenAI's API to provide deep analysis and personalized improvement plans.")

if __name__ == "__main__":
    main()