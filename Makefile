lint:
	black --line-length 120 foxysafe
	isort --profile black --line-length 120 foxysafe
	ruff --fix --line-length 120 foxysafe

build:
	python -m build .

check:
	python -m twine check dist/*

upload:
	python -m twine upload dist/*
