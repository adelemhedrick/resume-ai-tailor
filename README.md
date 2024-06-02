# Resume AI Tailor

This project is a work in progress so do what you will with that!

## Overview

**ResumeAiTailor** is a Python-based application designed to help job seekers tailor their resumes and cover letters to specific job postings. Utilizing AI services from OpenAI, the tool analyzes job descriptions and generates customized application documents. It handles everything from fetching job postings online, processing LaTeX-based resume data, to generating tailored resumes and cover letters in both LaTeX and PDF formats.

## Key Features

- **Dynamic Resume and Cover Letter Customization:** Tailors resumes and cover letters to match the specific requirements of job postings.
- **AI-Powered Analysis:** Uses OpenAI's services to analyze job postings and suggest customizations.
- **PDF and LaTeX Output:** Generates documents in both PDF and LaTeX formats, ready for submission.
- **Automated Web Scraping:** Automatically fetches job posting content from provided URLs.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- LaTeX distribution (e.g., TeX Live) to compile documents to PDF
- Chromium or Google Chrome browser (for Selenium web driver)

### Setting Up a Python Environment

1. **Install Python 3.8+ and pip**
   Ensure Python and pip are installed. You can download them from python.org.

2. **Create a Virtual Environment**
   It's recommended to use a virtual environment to avoid conflicts with system-wide packages.
   ```
   python3 -m venv venv
   source venv/bin/activate  # Activate the virtual environment
   ```

3. **Install Required Python Packages**
   Install the required packages using pip:
   ```
   pip install -r requirements.txt
   ```
### Additional Linux Environment Setup

4. **Install Chromium or Google Chrome**
   ResumeAiTailor uses Selenium for web scraping, which requires a web browser.
   ```
   sudo apt-get update
   sudo apt-get install chromium-browser
   ```

5. **Install WebDriver**
   The `webdriver-manager` package should handle this automatically, but you can manually install ChromeDriver if needed:
   ```
   sudo apt-get install chromium-chromedriver
   ```

6. **Install LaTeX**
   The tool generates PDFs using LaTeX, so a LaTeX distribution like TeX Live is necessary:
   ```
   sudo apt-get install texlive-full
   ```

## Usage
To run ResumeAiTailor, you need to provide the path to your LaTeX resume, the job posting URL, and a file prefix for the output files.

```
python resume_ai_tailor.py \
	--resume path/to/your_resume.tex \
	--job-posting-url "http://example.com/job-posting" \
	--output-prefix "output_filename_prefix"
```
This will process the job posting, tailor your resume and cover letter based on the posting, and save the tailored documents in the specified output directory.