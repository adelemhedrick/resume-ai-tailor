#!/usr/bin/env python3
from __future__ import annotations  # This import is necessary for forward references in type hints

import argparse
import base64
import json
import re
from datetime import datetime
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

    OUTPUT_DIRECTORY = "output"
    RESUME_JSON_SCHEMA = """
        {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "skills": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "skill": {
                "type": "string"
              },
              "details": {
                "type": "string"
              }
            },
            "required": ["skill", "details"]
          }
        },
        "certificates": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "year": {
                "type": "string"
              },
              "title": {
                "type": "string"
              }
            },
            "required": ["year", "title"]
          }
        },
        "experience": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "company": {
                "type": "string"
              },
              "location": {
                "type": "string"
              },
              "roles": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "job_title": {
                      "type": "string"
                    },
                    "period": {
                      "type": "string"
                    }
                  },
                  "required": ["job_title", "period"]
                }
              },
              "description": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": ["company", "location", "roles", "description"]
          }
        },
        "education": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "year": {
                "type": "string"
              },
              "degree": {
                "type": "string"
              },
              "institution": {
                "type": "string"
              },
              "GPA": {
                "type": "string"
              }
            },
            "required": ["year", "degree", "institution", "GPA"]
          }
        },
        "publications": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "year": {
                "type": "string"
              },
              "title": {
                "type": "string"
              },
              "description": {
                "type": "string"
              }
            },
            "required": ["year", "title", "description"]
          }
        },
        "projects": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {
                "type": "string"
              },
              "description": {
                "type": "string"
              }
            },
            "required": ["name", "description"]
          }
        }
      },
      "additionalProperties": false,
      "required": []
        }
        """

    EXTRACT_JOB_TITLE_AND_COMPANY_PROMPT = """
        Analyze the following job posting content:
        {job_posting_content}

        Return the company name and job title in JSON format using this json schema:
        {{
          "type": "object",
          "properties": {{
            "company_name": {{
              "type": "string",
              "description": "The name of the company where the job is located."
            }},
            "job_title": {{
              "type": "string",
              "description": "The title of the job."
            }}
          }},
          "required": ["company", "job_title"]
        }}

        Do not return anything before or after the JSON, and do not include ```
        """

    COMPANY_PROMPT = """Analyze the following job posting content:
        {job_posting_content}

        Analyze the experience I had at {company} which is a list in JSON format:
        {company_description}
        
        Tailor this list to the job posting and return a list back in the same JSON format.

        Do not return anything before or after the JSON code and do not include ```
        """

    COVER_LETTER_PROMPT = """Analyze the following job posting content:
        {job_posting_content}

        Here is my contact information:
        {personal_information}

        Analyze my resume currently in JSON format:
        {full_resume_content}
        
        Create a cover letter using my resume for the job posting using the moderncv and fancy style.
        Return just the cover letter in LaTeX.
        Do not return anything before or after the LaTeX code and do not include ```
        """

    def __init__(self, full_resume_path: str, job_posting_url: str, file_prefix: str) -> None:
        self.full_resume_path: str = full_resume_path
        self.job_posting_url: str = job_posting_url
        self.file_prefix: str = file_prefix
        self.personal_information: dict = None
        self.company_name: str = ""
        self.job_title: str = ""
        self.output_folder: str = ""
        self.job_posting_content: str = ""
        self.full_resume_latex: str = ""
        self.full_resume_json: dict = None
        self.resume_tex_file: str = ""
        self.cover_letter_tex_file: str = ""
        self.open_ai_client: OpenAI = None

    def run(self) -> ResumeAiTailor:
        (self.create_folder_with_timestamp()
         .get_url_content()
         .create_ai_client()
         .load_full_resume()
         .get_company_name_and_job_title()
         .get_tailored_resume()
         .get_tailored_cover_letter())
        return self

    def create_folder_with_timestamp(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_folder = os.path.join(self.OUTPUT_DIRECTORY, f"resume_{timestamp}")
        
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"Folder created: {self.output_folder}")
        else:
            print(f"Folder already exists: {self.output_folder}")
        return self

    def get_url_content(self) -> ResumeAiTailor:
        try:
            options = Options()
            options.headless = True  # Run in headless mode
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920x1080')

            service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=options)
            
            driver.get(self.job_posting_url)
            time.sleep(5)  # Wait for the page to load completely
            
            self.job_posting_content = driver.find_element(By.TAG_NAME, "body").text
            
            with open(f"{self.output_folder}/job_posting_content.txt", 'w') as file:
                file.write(self.job_posting_content)
            
            print(f"Job posting content saved to job_posting_content.txt")
            driver.quit()
        except Exception as e:
            print(f"An error occurred while fetching the job posting content: {e}")
        
        return self

    def load_full_resume(self) -> ResumeAiTailor:
        with open(self.full_resume_path, 'r') as file:
            self.full_resume_latex = file.read()

        latex_content = self.full_resume_latex.replace("\\&", "__AND__")

        name_match = re.search(r'\\name\{([^}]+)\}\{([^}]+)\}', latex_content)
        address_match = re.search(r'\\address\{([^}]+)\}', latex_content)
        phone_match = re.search(r'\\phone\[mobile\]\{([^}]+)\}', latex_content)
        email_match = re.search(r'\\email\{([^}]+)\}', latex_content)

        self.personal_information = {
            "name": f"{name_match.group(1)} {name_match.group(2)}",
            "address": address_match.group(1),
            "phone": phone_match.group(1),
            "email": email_match.group(1)
        }

        latex_content = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', latex_content, re.DOTALL).group(1)

        data = {}

        skills_match = re.search(r'\\section\{Skills\}(.*?)\\section|$', latex_content, re.DOTALL)
        if skills_match:
            skills = skills_match.group(1)
            skills_items = re.findall(r'\\cvitem\{([^}]+)\}\{([^}]+)\}', skills)
            data['skills'] = [{"skill": item[0], "details": item[1]} for item in skills_items]

        certificates_match = re.search(r'\\section\{Certifications\}(.*?)\\section|$', latex_content, re.DOTALL)
        if certificates_match:
            certificates_content = certificates_match.group(1)
            certificates_items = re.findall(r'\\cvitem\{(\d+)\}\{([^}]+)\}', certificates_content)
            data['certificates'] = [{"year": cert[0], "title": cert[1]} for cert in certificates_items]

        experience_match = re.search(r'\\section\{Experience\}(.*?)\\section|$', latex_content, re.DOTALL)
        if experience_match:
            data["experience"] = []
            experience_content = experience_match.group(1)
            companies = re.findall(r'\\subsection\{(.+?)\}(.*?)(?=\\subsection|$)', experience_content, re.DOTALL)
            for company in companies:
                company_name = company[0].strip()
                company_content = company[1].strip()

                roles = re.findall(r'\\cventry\{([^}]+)\}\{([^}]+)\}\{([^}]*)\}', company_content)
                location = roles[0][2]
                descriptions = re.findall(r'\\begin\{itemize\}(.*?)\\end\{itemize\}', company_content, re.DOTALL)
                overall_description = []
                if descriptions:
                    overall_description = [item.strip() for item in re.findall(r'\\item (.+)', descriptions[-1])]
                
                role_details = [{"job_title": role[1], "period": role[0]} for role in roles]

                company_info = {
                    "company": company_name,
                    "location": location,
                    "roles": role_details,
                    "description": overall_description
                }
                
                data["experience"].append(company_info)

        education_match = re.search(r'\\section\{Education\}(.*?)\\section|$', latex_content, re.DOTALL)
        if education_match:
            education_content = education_match.group(1)
            education_items = re.findall(r'\\cventry\{([^}]+)\}\{([^}]+)\}\{([^}]*?)\}\{([^}]*?)\}\{(.*?)\}\{\}', education_content)
            data['education'] = [{"year": edu[0], "degree": edu[1], "institution": edu[3], "GPA": edu[4].strip("\\textit{}")} for edu in education_items if "GPA" in edu[4]]

        publication_match = re.search(r'\\section\{Publications\}(.*?)(\\section|$)', latex_content, re.DOTALL)
        if publication_match:
            publication_content = publication_match.group(1)
            publication_items = re.findall(r'\\cventry\{([^}]+)\}\{([^}]+)\}\{\}\{\}\{\}\{([^}]+)\}', publication_content)
            data['publications'] = [{"year": pub[0], "title": pub[1], "description": pub[2].strip()} for pub in publication_items]

        projects_match = re.search(r'\\section\{Projects\}(.*?)(\\section|$)', latex_content, re.DOTALL)
        if projects_match:
            projects = projects_match.group(1)
            project_items = re.findall(r'\\cvitem\{\}\{\\textbf\{([^}]+)\}\.(.*?)\}', projects, re.DOTALL)
            data['projects'] = [{"name": proj[0].strip(), "description": proj[1].strip()} for proj in project_items]

        def replace_in_dict(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    obj[key] = replace_in_dict(value)
            elif isinstance(obj, list):
                return [replace_in_dict(item) for item in obj]
            elif isinstance(obj, str):
                return obj.replace('__AND__', '\\&')
            return obj

        self.full_resume_json = replace_in_dict(data)
        with open(f"{self.output_folder}/full_resume_as_json.json", 'w') as file:
            json.dump(data, file, indent=4)

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

    def compile_latex_to_pdf(self, tex_file: str) -> None:
        try:
            subprocess.run(['xelatex', '-output-directory=' + self.output_folder, tex_file], check=True)
            base_name = os.path.splitext(tex_file)[0]
            aux_files = [f"{base_name}.aux", f"{base_name}.log", f"{base_name}.out"]
            for aux_file in aux_files:
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            print(f"Compilation of {tex_file} was successful.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred during the compilation: {e}")

    def get_company_name_and_job_title(self) -> ResumeAiTailor:
        message = self.EXTRACT_JOB_TITLE_AND_COMPANY_PROMPT.format(job_posting_content=self.job_posting_content)

        posting_json = self.send_open_ai_request(message)

        posting_object = json.loads(posting_json)
        self.company_name = posting_object["company_name"]
        self.job_title = posting_object["job_title"]

        json_file = f"{self.output_folder}/posting_info.json"
        with open(json_file, 'w') as file:
            file.write(posting_json)
        return self

    @staticmethod
    def json_to_latex_experience(experience_data):
        latex_output = ""
        for company in experience_data:
            latex_output += f"\\subsection{{{company['company']}}}\n"
            num_roles = len(company['roles'])
            for i, role in enumerate(company['roles']):
                job_title = role['job_title']
                if i == num_roles - 1 and company['description']:  # Check if it's the last role and there is a description
                    # Open the last role with a description block
                    latex_output += f"\\cventry{{{role['period']}}}{{{job_title}}}{{}}{{}}{{}}{{\n"
                    latex_output += "    \\begin{itemize}\n"
                    for item in company['description']:
                        latex_output += f"        \\item {item}\n"
                    latex_output += "    \\end{itemize}\n"
                    latex_output += "}\n"  # Close the last role entry with the description inside
                elif i == 0:
                    latex_output += f"\\cventry{{{role['period']}}}{{{job_title}}}{{{company['location']}}}{{}}{{}}{{}}\n"
                else:
                    # Standard role entry without description
                    latex_output += f"\\cventry{{{role['period']}}}{{{job_title}}}{{}}{{}}{{}}{{}}\n"
            latex_output += "\n"

        return latex_output

    def get_tailored_resume(self) -> ResumeAiTailor:

        tailored_experience = []
        for experience_original in self.full_resume_json["experience"]:
            experience_new = experience_original
            message = self.COMPANY_PROMPT.format(job_posting_content=self.job_posting_content,
                                                company=experience_new["company"],
                                                company_description=experience_new["description"])
            response = self.send_open_ai_request(message)
            experience_new["description"] = json.loads(response)
            tailored_experience.append(experience_new)

        with open(f"{self.output_folder}/tailored_experience.json", 'w') as file:
            json.dump(tailored_experience, file, indent=4)

        
        tailored_resume_latex = self.full_resume_latex
        experience_latex = self.json_to_latex_experience(tailored_experience).replace('\\', '\\\\')
        tailored_resume_latex = re.sub(r'(?<=\\section{Experience}).*?(?=\\section)', experience_latex, tailored_resume_latex, flags=re.DOTALL)
        
        self.resume_tex_file = f"{self.output_folder}/{self.file_prefix}_{self.company_name}_{self.job_title}_resume.tex"

        with open(self.resume_tex_file, 'w') as file:
            file.write(tailored_resume_latex)

        self.compile_latex_to_pdf(self.resume_tex_file)
        return self

    def get_tailored_cover_letter(self) -> ResumeAiTailor:
        message = self.COVER_LETTER_PROMPT.format(job_posting_content=self.job_posting_content,
                                                  full_resume_content=self.full_resume_json,
                                                  personal_information=json.dumps(self.personal_information, indent=4))

        tailored_cover_letter = self.send_open_ai_request(message)

        self.cover_letter_tex_file = f"{self.output_folder}/{self.file_prefix}_{self.company_name}_{self.job_title}_cover_letter.tex"

        with open(self.cover_letter_tex_file, 'w') as file:
            file.write(tailored_cover_letter)

        self.compile_latex_to_pdf(self.cover_letter_tex_file)
        return self


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tailor your resume and cover letter to a job posting using AI.")

    parser.add_argument("--resume", dest="full_resume_path", required=True, help="Path to the full resume in LaTeX format")
    parser.add_argument("--job-posting-url", dest="job_posting_url", required=True, help="URL of the job posting")
    parser.add_argument("--output-prefix", dest="file_prefix", required=True, help="Prefix for the output files")

    args = parser.parse_args()

    ResumeAiTailor(full_resume_path=args.full_resume_path,
                   job_posting_url=args.job_posting_url,
                   file_prefix=args.file_prefix).run()
