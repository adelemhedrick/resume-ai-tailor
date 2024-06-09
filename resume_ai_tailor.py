#!/usr/bin/env python3
"""
This module, ResumeAiTailorPipeline, provides a comprehensive toolkit for tailoring resumes and
cover letters to specific job postings. It utilizes AI services from OpenAI to analyze job
descriptions and generate customized application documents. The module handles everything from
fetching job postings online, processing LaTeX-based resume data, to generating tailored resumes and
cover letters in both LaTeX and PDF formats.

The functionalities include web scraping, AI-driven content analysis and generation, LaTeX document
manipulation, and PDF compilation. This module is designed to help job seekers create highly
customized and optimized job application materials that significantly increase their chances of
landing job interviews.
"""
from __future__ import (
    annotations,
)  # This import is necessary for forward references in type hints
from typing import Dict, Any, cast, Optional, List, Union, Tuple
from abc import ABC, abstractmethod
import argparse
import json
import re
from datetime import datetime
import time
import os
import subprocess
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class ResumeAiTailorPipeline:  # pylint: disable=too-few-public-methods
    """
    Manages the creation of tailored resumes and cover letters based on job postings.

    Attributes:
        resume_file_path (str): Path to the LaTeX resume file.
        file_prefix (str): Prefix for naming output files.
        job_posting (JobPosting): Job posting handler.
        output_folder (str): Directory for storing output files.
        resume (Resume): Resume document handler.
        cover_letter (CoverLetter): Cover letter document handler.
    """

    OUTPUT_DIRECTORY: str = "output"

    def __init__(
        self, resume_file_path: str, job_posting_url: str, file_prefix: str
    ) -> None:
        """
        Initializes the pipeline with paths and settings for processing the resume and job posting.

        Args:
            resume_file_path (str): Path to the LaTeX resume file.
            job_posting_url (str): URL to the online job posting.
            file_prefix (str): Prefix for generated files.
        """
        self._resume_file_path: str = resume_file_path
        self._file_prefix: str = file_prefix
        self._job_posting: JobPosting = JobPosting(job_posting_url)
        self._output_folder: str = ""
        self._resume: Resume = None
        self._cover_letter: CoverLetter = None

    def run(self) -> ResumeAiTailorPipeline:
        """
        Executes the entire pipeline process for resume and cover letter generation.

        Returns:
            ResumeAiTailorPipeline: Self instance after processing.
        """
        (
            self._create_folder_with_timestamp()  #  pylint: disable=protected-access
            ._create_resume()  #  pylint: disable=protected-access
            ._create_cover_letter()  #  pylint: disable=protected-access
        )
        return self

    def _create_folder_with_timestamp(self) -> ResumeAiTailorPipeline:
        """
        Creates a new output folder with a timestamp to avoid overwriting previous files.

        Returns:
            ResumeAiTailorPipeline: Self instance with updated output folder path.
        """
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_folder = os.path.join(self.OUTPUT_DIRECTORY, f"resume_{timestamp}")

        if not os.path.exists(self._output_folder):
            os.makedirs(self._output_folder)
            print(f"Folder created: {self._output_folder}")
        else:
            print(f"Folder already exists: {self._output_folder}")
        return self

    def _create_resume(self) -> ResumeAiTailorPipeline:
        """
        Creates a tailored resume based on the job posting.

        Returns:
            ResumeAiTailorPipeline: Self instance with the created resume.
        """
        self._resume = (
            Resume(
                output_folder=self._output_folder,
                file_prefix=self._file_prefix,
                job_posting=self._job_posting,
            )
            .load(self._resume_file_path)
            .create()
            .save()
        )
        return self

    def _create_cover_letter(self) -> ResumeAiTailorPipeline:
        """
        Creates a tailored cover letter that complements the tailored resume.

        Returns:
            ResumeAiTailorPipeline: Self instance with the created cover letter.
        """
        self._cover_letter = (
            CoverLetter(
                output_folder=self._output_folder,
                file_prefix=self._file_prefix,
                job_posting=self._job_posting,
                resume=self._resume,
            )
            .create()
            .save()
        )
        return self


class JobPosting:
    """
    Handles fetching and parsing of job posting details.

    Attributes:
        job_posting_url (str): URL of the job posting.
        job_posting_content (str): Raw content of the job posting.
        company_name (str): Extracted company name from the posting.
        job_title (str): Extracted job title from the posting.
        ai_client (AIClient): Client for handling AI requests.
    """

    def __init__(self, job_posting_url: str):
        """
        Initializes the JobPosting object with the URL of the job posting.

        Args:
            job_posting_url (str): URL of the job posting.
        """
        self._job_posting_url: str = job_posting_url
        self._job_posting_content: str = None
        self._company_name: str = None
        self._job_title: str = None
        self._ai_client: AIClient = AIClient()

    def get(self) -> str:
        """
        Retrieves and stores the text content of the job posting from the web.

        Returns:
            str: The text content of the job posting.
        """
        if self._job_posting_content is None:
            try:
                options: Options = Options()
                options.headless = True  # Run in headless mode
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920x1080")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                driver.get(self._job_posting_url)
                time.sleep(5)
                self._job_posting_content = driver.find_element(
                    By.TAG_NAME, "body"
                ).text
                driver.quit()
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"An error occurred while fetching the job posting content: {e}")
        return self._job_posting_content

    def get_company_name_and_job_title(self) -> Tuple(str, str):
        """
        Extracts and returns the company name and job title from the job posting.

        Returns:
            Tuple[str, str]: A tuple containing the company name and job title.
        """
        if self._company_name is None or self._job_title is None:
            posting_json = self._ai_client.get_job_title_and_company(self.get())
            posting_object = json.loads(posting_json)
            self._company_name = posting_object["company_name"]
            self._job_title = posting_object["job_title"]

        return self._company_name, self._job_title


class AIClient:
    """
    Provides functionalities to interact with the OpenAI API for processing job postings and
    resumes.

    Attributes:
        open_ai_client (OpenAI): Instance of the OpenAI client.
    """

    def __init__(self):
        """
        Initializes the AI client with necessary API keys.
        """
        self._open_ai_client: OpenAI = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def _send_open_ai_request(self, message: str) -> str:
        """
        Sends a request to the OpenAI API and returns the response.

        Args:
            message (str): The message to be sent to the AI.

        Returns:
            str: The AI's response as a string.
        """
        response = self._open_ai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "user",
                    "content": message,
                }
            ],
            max_tokens=1024,
        )
        return cast(str, response.choices[0].message.content)

    def get_job_title_and_company(self, job_posting_content: str) -> str:
        """
        Sends a job posting content to the AI to extract company name and job title.

        Args:
            job_posting_content (str): The content of the job posting.

        Returns:
            str: JSON string with the company name and job title.
        """
        message = f"""
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
        return self._send_open_ai_request(message)

    def get_tailored_work_experience(
        self, job_posting_content: str, company: str, company_description: str
    ) -> str:
        """
        Requests the AI to tailor the work experience description to the job posting.

        Args:
            job_posting_content (str): The content of the job posting.
            company (str): The name of the company where the experience was gained.
            company_description (str): Description of the work done at the company.

        Returns:
            str: Tailored work experience description.
        """
        message = f"""Analyze the following job posting content:
        {job_posting_content}

        Analyze the experience I had at {company} which is a list in JSON format:
        {company_description}
        
        Tailor this list to the job posting and return a list back in the same JSON format.

        Do not return anything before or after the JSON code and do not include ```
        """
        return self._send_open_ai_request(message)

    def get_tailored_cover_letter(
        self, job_posting_content: str, personal_information, resume_content
    ) -> str:
        """
        Generates a tailored cover letter based on personal information and resume content.

        Args:
            job_posting_content (str): The content of the job posting.
            personal_information (str): Personal contact information.
            resume_content (str): Content of the resume in JSON format.

        Returns:
            str: Tailored cover letter in LaTeX format.
        """
        message = f"""Analyze the following job posting content:
        {job_posting_content}

        Here is my contact information:
        {personal_information}

        Analyze my resume currently in JSON format:
        {resume_content}
        
        Create a cover letter using my resume for the job posting using the moderncv and fancy
        style.
        Return just the cover letter in LaTeX.
        Do not return anything before or after the LaTeX code and do not include ```
        """
        return self._send_open_ai_request(message)


class LaTeXtoJSONParser:
    """
    Provides methods to parse various sections of a LaTeX document into structured JSON data.
    """

    @staticmethod
    def parse_personal_information(latex_content: str) -> Dict[str, str]:
        """
        Extracts personal information from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing personal information.

        Returns:
            Dict[str, str]: A dictionary with keys 'name', 'address', 'phone', and 'email' mapped to
            their respective values.
        """
        latex_content = latex_content.replace("\\&", "__AND__")
        name_match = re.search(r"\\name\{([^}]+)\}\{([^}]+)\}", latex_content)
        address_match = re.search(r"\\address\{([^}]+)\}", latex_content)
        phone_match = re.search(r"\\phone\[mobile\]\{([^}]+)\}", latex_content)
        email_match = re.search(r"\\email\{([^}]+)\}", latex_content)
        return {
            "name": f"{name_match.group(1)} {name_match.group(2)}",
            "address": address_match.group(1),
            "phone": phone_match.group(1),
            "email": email_match.group(1),
        }

    @staticmethod
    def _parse_skills(latex_content: str) -> Optional[List[Dict[str, str]]]:
        """
        Extracts skills from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing the skills section.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries, each containing 'skill' and
            'details', or None if no skills found.
        """
        parsed_skills = None
        skills_match = re.search(
            r"\\section\{Skills\}(.*?)\\section|$", latex_content, re.DOTALL
        )
        if skills_match:
            skills = skills_match.group(1)
            skills_items = re.findall(r"\\cvitem\{([^}]+)\}\{([^}]+)\}", skills)
            parsed_skills = [
                {"skill": item[0], "details": item[1]} for item in skills_items
            ]
        return parsed_skills

    @staticmethod
    def _parse_certificates(latex_content: str) -> Optional[List[Dict[str, str]]]:
        """
        Extracts certificates from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing the certifications section.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries, each containing 'year' and
            'title', or None if no certificates found.
        """
        parsed_certificates = None
        certificates_match = re.search(
            r"\\section\{Certifications\}(.*?)\\section|$", latex_content, re.DOTALL
        )
        if certificates_match:
            certificates_content = certificates_match.group(1)
            certificates_items = re.findall(
                r"\\cvitem\{(\d+)\}\{([^}]+)\}", certificates_content
            )
            parsed_certificates = [
                {"year": cert[0], "title": cert[1]} for cert in certificates_items
            ]
        return parsed_certificates

    @staticmethod
    def _parse_experience(
        latex_content: str,
    ) -> Optional[List[Dict[str, Union[str, List[str], List[Dict[str, str]]]]]]:
        """
        Extracts professional experience from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing the experience section.

        Returns:
            Optional[List[Dict[str, Union[str, List[str], List[Dict[str, str]]]]]]: A list of
            dictionaries, each representing a company and including company name, location, roles,
            and descriptions, or None if no experience found.
        """
        experience_list = None
        experience_match = re.search(
            r"\\section\{Experience\}(.*?)\\section|$", latex_content, re.DOTALL
        )
        if experience_match:
            experience_list = []
            experience_content = experience_match.group(1)
            companies = re.findall(
                r"\\subsection\{(.+?)\}(.*?)(?=\\subsection|$)",
                experience_content,
                re.DOTALL,
            )
            for company in companies:
                company_name = company[0].strip()
                company_content = company[1].strip()

                roles = re.findall(
                    r"\\cventry\{([^}]+)\}\{([^}]+)\}\{([^}]*)\}", company_content
                )
                location = roles[0][2]
                descriptions = re.findall(
                    r"\\begin\{itemize\}(.*?)\\end\{itemize\}",
                    company_content,
                    re.DOTALL,
                )
                overall_description = []
                if descriptions:
                    overall_description = [
                        item.strip()
                        for item in re.findall(r"\\item (.+)", descriptions[-1])
                    ]

                role_details = [
                    {"job_title": role[1], "period": role[0]} for role in roles
                ]

                company_info = {
                    "company": company_name,
                    "location": location,
                    "roles": role_details,
                    "description": overall_description,
                }

                experience_list.append(company_info)
        return experience_list

    @staticmethod
    def _parse_education(latex_content: str) -> Optional[List[Dict[str, str]]]:
        """
        Extracts education details from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing the education section.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries, each containing 'year',
            'degree', 'institution', and 'GPA', or None if no education details found.
        """
        parsed_education = None
        education_match = re.search(
            r"\\section\{Education\}(.*?)\\section|$", latex_content, re.DOTALL
        )
        if education_match:
            education_content = education_match.group(1)
            education_items = re.findall(
                r"\\cventry\{([^}]+)\}\{([^}]+)\}\{([^}]*?)\}\{([^}]*?)\}\{(.*?)\}\{\}",
                education_content,
            )
            parsed_education = [
                {
                    "year": edu[0],
                    "degree": edu[1],
                    "institution": edu[3],
                    "GPA": edu[4].strip("\\textit{}"),
                }
                for edu in education_items
                if "GPA" in edu[4]
            ]
        return parsed_education

    @staticmethod
    def _parse_publications(latex_content: str) -> Optional[List[Dict[str, str]]]:
        """
        Extracts publication details from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing the publications section.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries, each containing 'year', 'title',
            and 'description', or None if no publications found.
        """
        parsed_publication = None
        publication_match = re.search(
            r"\\section\{Publications\}(.*?)(\\section|$)", latex_content, re.DOTALL
        )
        if publication_match:
            publication_content = publication_match.group(1)
            publication_items = re.findall(
                r"\\cventry\{([^}]+)\}\{([^}]+)\}\{\}\{\}\{\}\{([^}]+)\}",
                publication_content,
            )
            parsed_publication = [
                {"year": pub[0], "title": pub[1], "description": pub[2].strip()}
                for pub in publication_items
            ]
        return parsed_publication

    @staticmethod
    def _parse_projects(latex_content: str) -> Optional[List[Dict[str, str]]]:
        """
        Extracts project details from the LaTeX content.

        Args:
            latex_content (str): The LaTeX content containing the projects section.

        Returns:
            Optional[List[Dict[str, str]]]: A list of dictionaries, each containing 'name' and
            'description', or None if no projects found.
        """
        parsed_projects = None
        projects_match = re.search(
            r"\\section\{Projects\}(.*?)(\\section|$)", latex_content, re.DOTALL
        )
        if projects_match:
            projects = projects_match.group(1)
            project_items = re.findall(
                r"\\cvitem\{\}\{\\textbf\{([^}]+)\}\.(.*?)\}", projects, re.DOTALL
            )
            parsed_projects = [
                {"name": proj[0].strip(), "description": proj[1].strip()}
                for proj in project_items
            ]
        return parsed_projects

    def parse_resume(self, latex_content) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parses the entire LaTeX resume content into structured JSON format.

        Args:
            latex_content (str): The entire LaTeX content of a resume.

        Returns:
            Dict[str, List[Dict[str, Any]]]: A dictionary where each key corresponds to a section of
            the resume ('skills', 'certificates', 'experience', etc.) and each value is a list of
            parsed entities.
        """
        latex_content = latex_content.replace("\\&", "__AND__")
        latex_content = re.search(
            r"\\begin\{document\}(.*?)\\end\{document\}", latex_content, re.DOTALL
        ).group(1)

        resume = {
            "skills": self._parse_skills(latex_content),
            "certificates": self._parse_certificates(latex_content),
            "experience": self._parse_experience(latex_content),
            "education": self._parse_education(latex_content),
            "publications": self._parse_publications(latex_content),
            "projects": self._parse_projects(latex_content),
        }

        def replace_in_dict(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    obj[key] = replace_in_dict(value)
            elif isinstance(obj, list):
                return [replace_in_dict(item) for item in obj]
            elif isinstance(obj, str):
                return obj.replace("__AND__", "\\&")
            return obj

        return replace_in_dict(resume)


class Document(ABC):
    """
    Abstract base class for documents generated in the ResumeAiTailorPipeline, such as resumes and
    cover letters.

    Attributes:
        output_folder (str): The directory where the document will be saved.
        file_prefix (str): Prefix for the output files to help in organizing and identifying files
        easily.
        job_posting (JobPosting): A reference to the job posting object which contains details like
        company name and job title.
        ai_client (AIClient): Client to interact with AI services for generating content.
        doc_type (str): Type of the document (e.g., 'resume' or 'cover_letter').
        doc_content (str): The content of the document in LaTeX format.
    """

    def __init__(
        self, output_folder: str, file_prefix: str, job_posting: JobPosting
    ) -> None:
        """
        Initializes a Document object with necessary parameters and sets up an AI client.
        """
        self._output_folder: str = output_folder
        self._file_prefix: str = file_prefix
        self._job_posting: JobPosting = job_posting
        self._ai_client: AIClient = AIClient()
        self._doc_type: str = None
        self._doc_content: str = None

    @abstractmethod
    def create(self) -> Document:
        """
        Abstract method to create the document content. Must be implemented by subclasses.
        """

    def _compile_latex_to_pdf(self, tex_file: str) -> None:
        """
        Compiles LaTeX file to a PDF document.

        Args:
            tex_file (str): The path to the LaTeX file to be compiled.
        """
        try:
            subprocess.run(
                ["xelatex", "-output-directory=" + self._output_folder, tex_file],
                check=True,
            )
            base_name = os.path.splitext(tex_file)[0]
            aux_files = [f"{base_name}.aux", f"{base_name}.log", f"{base_name}.out"]
            for aux_file in aux_files:
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            print(f"Compilation of {tex_file} was successful.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred during the compilation: {e}")

    def save(self) -> Document:
        """
        Saves the document content to a file and compiles it to PDF.

        Returns:
            Document: The instance of the document with updated content.
        """
        company_name, job_title = self._job_posting.get_company_name_and_job_title()
        file_name = f"{self._output_folder}/{self._file_prefix}_{company_name}_{job_title}_{self._doc_type}.tex"  # pylint: disable=line-too-long
        file_name = file_name.replace(" ", "_")
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(self._doc_content)
        self._compile_latex_to_pdf(file_name)
        return self


class Resume(Document):
    """
    Represents a tailored resume document.

    Attributes:
        resume (Dict[str, List[Dict[str, Any]]]): Structured data representing sections of the
        resume.
        personal_information (Dict[str, str]): Personal details extracted from the resume.
    """

    def __init__(
        self, output_folder: str, file_prefix: str, job_posting: JobPosting
    ) -> None:
        """
        Initializes a Resume instance inheriting the Document base settings.
        """
        super().__init__(
            output_folder=output_folder,
            file_prefix=file_prefix,
            job_posting=job_posting,
        )

        self._doc_type = "resume"
        self._resume: Dict[str, List[Dict[str, Any]]] = None
        self._personal_information: Dict[str, str] = None

    def get_personal_information(self) -> Dict[str, str]:
        """
        Returns the personal information section of the resume.

        Returns:
            Dict[str, str]: A dictionary containing personal information such as name, address,
            phone, and email.
        """
        return self._personal_information

    def get(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns the structured resume data.

        Returns:
            Dict[str, List[Dict[str, Any]]]: The entire structured data of the resume.
        """
        return self._resume

    @staticmethod
    def _json_to_latex_experience(experience_data: List[Dict]) -> str:
        """
        Converts JSON-formatted experience data back into LaTeX format.

        Args:
            experience_data (List[Dict]): The list of dictionaries containing experience details.

        Returns:
            str: LaTeX formatted string of experience details.
        """
        latex_output = ""
        for company in experience_data:
            latex_output += f"\\subsection{{{company['company']}}}\n"
            num_roles = len(company["roles"])
            for i, role in enumerate(company["roles"]):
                job_title = role["job_title"]
                if (
                    i == num_roles - 1 and company["description"]
                ):  # Check if it's the last role and there is a description
                    # Open the last role with a description block
                    latex_output += (
                        f"\\cventry{{{role['period']}}}{{{job_title}}}{{}}{{}}{{}}{{\n"
                    )
                    latex_output += "    \\begin{itemize}\n"
                    for item in company["description"]:
                        latex_output += f"        \\item {item}\n"
                    latex_output += "    \\end{itemize}\n"
                    latex_output += (
                        "}\n"  # Close the last role entry with the description inside
                    )
                elif i == 0:
                    latex_output += f"\\cventry{{{role['period']}}}{{{job_title}}}{{{company['location']}}}{{}}{{}}{{}}\n"  # pylint: disable=line-too-long
                else:
                    # Standard role entry without description
                    latex_output += f"\\cventry{{{role['period']}}}{{{job_title}}}{{}}{{}}{{}}{{}}\n"  # pylint: disable=line-too-long
            latex_output += "\n"

        return latex_output

    def load(self, resume_file_path) -> Resume:
        """
        Loads resume data from a LaTeX file and parses it into structured JSON.

        Args:
            resume_file_path (str): Path to the LaTeX resume file.

        Returns:
            Resume: The instance of this class with loaded and parsed data.
        """
        with open(resume_file_path, "r", encoding="utf-8") as file:
            self._doc_content = file.read()

        parser = LaTeXtoJSONParser()
        self._personal_information = parser.parse_personal_information(
            self._doc_content
        )
        self._resume = parser.parse_resume(self._doc_content)
        return self

    def create(self) -> Resume:
        """
        Creates a tailored resume based on the job description and other parameters.

        Returns:
            Resume: The instance of this class with tailored content.
        """
        tailored_experience = []
        for experience in self._resume["experience"]:
            response = self._ai_client.get_tailored_work_experience(
                job_posting_content=self._job_posting.get(),
                company=experience["company"],
                company_description=experience["description"],
            )
            experience["description"] = json.loads(response)
            tailored_experience.append(experience)

        tailored_resume_latex = self._doc_content
        experience_latex = self._json_to_latex_experience(tailored_experience).replace(
            "\\", "\\\\"
        )
        self._doc_content = re.sub(
            r"(?<=\\section{Experience}).*?(?=\\section)",
            experience_latex,
            tailored_resume_latex,
            flags=re.DOTALL,
        )
        return self


class CoverLetter(Document):
    """
    Represents a tailored cover letter document.

    Attributes:
        resume (Resume): Reference to the associated resume to ensure alignment between the resume
        and the cover letter.
    """

    def __init__(
        self,
        output_folder: str,
        file_prefix: str,
        job_posting: JobPosting,
        resume: Resume,
    ) -> None:
        """
        Initializes a CoverLetter instance inheriting settings from the Document and associating it
        with a resume.
        """
        super().__init__(
            output_folder=output_folder,
            file_prefix=file_prefix,
            job_posting=job_posting,
        )

        self._doc_type = "cover_letter"
        self._resume: Resume = resume

    def create(self) -> CoverLetter:
        """
        Creates a tailored cover letter using details from the job posting and the associated
        resume.

        Returns:
            CoverLetter: The instance of this class with the tailored cover letter content.
        """
        self._doc_content = self._ai_client.get_tailored_cover_letter(
            job_posting_content=self._job_posting.get(),
            personal_information=self._resume.get_personal_information(),
            resume_content=self._resume.get(),
        )
        return self


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Tailor your resume and cover letter to a job posting using AI."
    )

    arg_parser.add_argument(
        "--resume",
        dest="resume_file_path",
        required=True,
        help="Path to the full resume in LaTeX format",
    )
    arg_parser.add_argument(
        "--job-posting-url",
        dest="job_posting_url",
        required=True,
        help="URL of the job posting",
    )
    arg_parser.add_argument(
        "--output-prefix",
        dest="file_prefix",
        required=True,
        help="Prefix for the output files",
    )

    args = arg_parser.parse_args()

    ResumeAiTailorPipeline(
        resume_file_path=args.resume_file_path,
        job_posting_url=args.job_posting_url,
        file_prefix=args.file_prefix,
    ).run()
