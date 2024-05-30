
run:
	mkdir -p /tmp/chrome-profile
	python resume_ai_tailor.py \
	--resume "input/full_resume.tex" \
	--job-posting-url "https://bestbuycanada.wd3.myworkdayjobs.com/BestBuyCA_Career/job/00000-Canadian-Headquarters/Reltio-Technical-Specialist_R-36910?source=LinkedIn_Slots" \
	--output-prefix "Hedrick_BestBuy_Reltio_Technical_Specialist"

.FORCE: