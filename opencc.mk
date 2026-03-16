%.tex %.txt:
	opencc -i $@ -o $@ -c t2gov/t2gov/t2new.json
