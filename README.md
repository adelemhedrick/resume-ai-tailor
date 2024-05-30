# Resume AI Tailor

## Requirements

* TeX Live - in Linux environment use 
* Python Environment with:
	* selenium
	* OpenAI SDK

mkdir -p /tmp/chrome-profile



pdflatex resume.tex

Setting up Ubuntu/WSL environment:
 sudo apt install texlive-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-xetex -y


sudo apt install -y chromium-browser

wget https://chromedriver.storage.googleapis.com/90.0.4430.24/chromedriver_linux64.zip -O /tmp/chromedriver.zip

sudo apt install -y unzip
unzip /tmp/chromedriver.zip -d /tmp/

sudo apt-get install -y libgbm-dev


pip install selenium

pyenv install 3.12
pyenv virtualenv 3.12 resume-ai-tailor


wget https://chromedriver.storage.googleapis.com/125.0.6422.112/chromedriver_linux64.zip -O /tmp/chromedriver.zip
