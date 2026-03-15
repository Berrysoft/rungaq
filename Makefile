%.ruby.tex %.ref.txt &: %.tex
	python dict.py $< --ref $*.ref.txt -o $*.ruby.tex