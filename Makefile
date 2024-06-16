
run:
	mkdir -p /tmp/chrome-profile
	python resume_ai_tailor.py \
	--resume "input/Hedrick_Resume.tex" \
	--job-posting-url "https://www.yelp.careers/us/en/job/YELPUS13003EXTERNALENUS/Senior-Machine-Learning-Engineer-Ads-Remote-Canada?utm_source=linkedin&utm_medium=phenom-feeds?mode=job&iis=Job+Board&iisn=LinkedIn" \
	--output-prefix "Hedrick"

lint:
	black resume_ai_tailor.py
	pylint resume_ai_tailor.py

docs:
	pyreverse --filter-mode 'ALL' \
	-o png \
	 --output-directory "assets" \
	-p  Resume-AI-Tailor \
	resume_ai_tailor.py

main:
	xelatex input/Hedrick_Resume.tex
	rm *.aux *.log *.out

.FORCE: