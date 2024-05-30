#!/usr/bin/env python3
from __future__ import annotations  # This import is necessary for forward references in type hints

import argparse
import base64
import json
import os
import subprocess
from typing import cast
import requests
from openai import OpenAI

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

class ResumeAiTailor:

    RESUME_PROMPT = """Analyze the following job posting content:
    {job_posting_content}

    Analyze my resume in LaTeX:
    {full_resume_content}
    
    Tailor my resume to the job posting and return just the resume in LaTeX.
    Make the resume a two page resume, using the moderncv fancy style.

    Do not return anything before or after the LaTeX code and do not include ```
    """

    COVER_LETTER_PROMPT = """Analyze the following job posting content:
    {job_posting_content}

    Analyze my resume in LaTeX:
    {full_resume_content}
    
    Create a cover letter using my resume to the job posting using the moderncv and fancy style.
    Return just the cover letter in LaTeX.
    Do not return anything before or after the LaTeX code and do not include ```
    """

    def __init__(self, full_resume_path: str, job_posting_url: str, output_file_prefix: str) -> None:
        self.full_resume_path: str = full_resume_path
        self.job_posting_url: str = job_posting_url
        self.output_file_prefix: str = output_file_prefix
        self.job_posting_content: str = ""
        self.full_resume_content: str = ""
        self.resume_tex_file: str = ""
        self.cover_letter_tex_file: str = ""
        self.open_ai_client: OpenAI = None

    def run(self) -> ResumeAiTailor:
        (self.get_url_content()
         .load_full_resume()
         .create_ai_client()
         .get_tailored_resume()
         .get_tailored_cover_letter())
        return self

    def get_url_content(self) -> ResumeAiTailor:
        try:
            options = Options()
            options.headless = True  # Run in headless mode
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=options)
            
            driver.get(self.job_posting_url)
            time.sleep(5)  # Wait for the page to load completely
            
            self.job_posting_content = driver.find_element(By.TAG_NAME, "body").text
            
            with open("job_posting_content.txt", 'w') as file:
                file.write(self.job_posting_content)
            
            print(f"Job posting content saved to job_posting_content.txt")
            driver.quit()
        except Exception as e:
            print(f"An error occurred while fetching the job posting content: {e}")
        
        return self

    def load_full_resume(self) -> ResumeAiTailor:
        with open(self.full_resume_path, 'r') as file:
            self.full_resume_content = file.read()
        return self

    def create_ai_client(self) -> ResumeAiTailor:
        self.open_ai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        return self

    def send_open_ai_request(self, message: str) -> str:
        response = self.open_ai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "user",
                    "content": message,
                }
            ],
            max_tokens=1024,
        )
        # Extract the LaTeX content and remove any \documentclass or \begin{document}, \end{document} commands
        latex_content = response.choices[0].message.content
        #latex_content = self.clean_latex_content(latex_content)
        return cast(str, latex_content)

    def clean_latex_content(self, latex_content: str) -> str:
        # Correct or remove invalid commands
        cleaned_content = latex_content.replace("\\usepassed on", "").replace("\\useleavevmode", "")
        return cleaned_content

    def compile_latex_to_pdf(self, tex_file: str) -> None:
        try:
            subprocess.run(['xelatex', tex_file], check=True)
            base_name = os.path.splitext(tex_file)[0]
            aux_files = [f"{base_name}.aux", f"{base_name}.log", f"{base_name}.out"]
            for aux_file in aux_files:
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            print(f"Compilation of {tex_file} was successful.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred during the compilation: {e}")

    def get_tailored_resume(self) -> ResumeAiTailor:
        message = self.RESUME_PROMPT.format(job_posting_content=self.job_posting_content,
                                                     full_resume_content=self.full_resume_content)

        tailored_resume = self.send_open_ai_request(message)
        #packages = "\\documentclass{resume}\n\\usepackage{ifthen}\n\\usepackage{hyperref}\n\\usepackage{enumitem}\n\\usepackage{geometry}\n\\usepackage{url}"
        #tailored_resume = (tailored_resume.replace('\\documentclass{resume}', packages)
        #                   .replace("\\href{mailto:adele@hedrick.ca}{adele@hedrick.ca}", "adele@hedrick.ca"))

        self.resume_tex_file = f"{self.output_file_prefix}_resume.tex"

        with open(self.resume_tex_file, 'w') as file:
            file.write(tailored_resume)

        self.compile_latex_to_pdf(self.resume_tex_file)
        return self

    def get_tailored_cover_letter(self) -> ResumeAiTailor:
        message = self.COVER_LETTER_PROMPT.format(job_posting_content=self.job_posting_content,
                                                           full_resume_content=self.full_resume_content)

        tailored_cover_letter = self.send_open_ai_request(message)

        self.cover_letter_tex_file = f"{self.output_file_prefix}_cover_letter.tex"

        with open(self.cover_letter_tex_file, 'w') as file:
            file.write(tailored_cover_letter)

        self.compile_latex_to_pdf(self.cover_letter_tex_file)
        return self



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tailor your resume and cover letter to a job posting using AI.")

    parser.add_argument("--resume", dest="full_resume_path", required=True, help="Path to the full resume in LaTeX format")
    parser.add_argument("--job-posting-url", dest="job_posting_url", required=True, help="URL of the job posting")
    parser.add_argument("--output-prefix", dest="output_file_prefix", required=True, help="Prefix for the output files")

    args = parser.parse_args()

    ResumeAiTailor(full_resume_path=args.full_resume_path,
                   job_posting_url=args.job_posting_url,
                   output_file_prefix=args.output_file_prefix).run()
