.PHONY: test project check
test:
	PYTHONPATH=engine/src python3 -m unittest discover -s engine/tests -v
project:
	python3 scripts/generate_xcode_project.py
check: test
	python3 -m compileall -q engine/src scripts
