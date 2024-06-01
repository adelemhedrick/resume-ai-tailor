
run:
	mkdir -p /tmp/chrome-profile
	python resume_ai_tailor.py \
	--resume "input/Hedrick_Resume.tex" \
	--job-posting-url "https://bestbuycanada.wd3.myworkdayjobs.com/BestBuyCA_Career/job/00000-Canadian-Headquarters/Reltio-Technical-Specialist_R-36910?source=LinkedIn_Slots" \
	--output-prefix "Hedrick"

lint:
	black resume_ai_tailor.py
	pylint resume_ai_tailor.py

.FORCE: