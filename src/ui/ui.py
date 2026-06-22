import streamlit as st

class JobAnalyserUI():
    def header(self):
        st.title("Job Analyser")
        st.write("Welcome to the Job Analyser UI. Use this interface to analyze job data and extract relevant information.")
        st.divider()
    
    def sidebar(self):
        with st.sidebar:
            st.header("API Key Configuration")
            return st.text_input("Enter your OPENAI API Key here", type="password")

    def upload_resume(self):
        st.subheader("Upload Resume")
        return    st.file_uploader("Upload your Resume here", type=["pdf"])
         

    def upload_jd(self):
        st.subheader("Upload Job Description")
        return st.file_uploader("Upload the Job Description here", type=["pdf"])
    
    def show_results(self,result:dict):
        st.divider()
        st.subheader("Analysis Results")
        st.write(f'### Score: {result["overall_score"]}/100')
        if result["selected"]:
            st.success("Congratulations! Your resume matches the job requirements.")
        else:
            st.error("Unfortunately, your resume does not match the job requirements.")

        st.subheader("Strengths")
        if result["strengths"]:
            st.write("The following strengths were identified:")
            for strength in result["strengths"]:
                st.write(f"- {strength}({result['skill_scores'][strength]}/10)")
        else:
            st.write("No strengths were identified.")

        st.subheader("Areas for Improvement")
        if result["missing_skills"]:
            st.write("The following skills were identified as missing:")
            for skill in result["missing_skills"]:
                st.write(f"- {skill}({result['skill_scores'][skill]}/10)")
        else:
            st.write("No major areas for improvement were identified.")

  