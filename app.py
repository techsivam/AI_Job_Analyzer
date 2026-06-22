import os
import streamlit as st
from src.core.agents import ResumeAnalysisAgent
from src.ui.ui import JobAnalyserUI
st.set_page_config(page_title="Job Analyser", page_icon=":briefcase:", layout="wide")

class JobAnalyserApp:
    def __init__(self):
        self.ui = JobAnalyserUI()
        self.agent = ResumeAnalysisAgent()
        self.api_key = None

    def run(self):
        self.ui.header()
        self.api_key = self.ui.sidebar()

        if not self.api_key:
            st.warning("Please enter your OPENAI API Key to proceed.")
            return
        os.environ["OPENAI_API_KEY"] = self.api_key

        resume_file = self.ui.upload_resume()
        jd_file = self.ui.upload_jd()


        
        if st.button("Analyze"):
            if not resume_file or not jd_file:
                st.error("Please upload both a resume and a job description to proceed.")
                return
            
            try:
                with st.spinner("Analyzing..."):
                    result = self.agent.analyze(resume_file, jd_file)
                    self.ui.show_results(result)
            except Exception as e:
                st.error(f"An error occurred during analysis: {str(e)}")



if __name__ == "__main__":
    app = JobAnalyserApp()
    app.run()
