%.ruby.txt %.ref.txt &: %.txt
	python dict.py $< --ref $@.ref.txt -o $@.ruby.txt