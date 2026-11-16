.PHONY: data pipeline test

data:
	python scripts/download_data.py

pipeline:
	python scripts/run_pipeline.py

test:
	pytest -q
	Rscript -e "testthat::test_dir('tests/testthat', stop_on_failure = TRUE)"
