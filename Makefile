lint:
	black --line-length 120 foxysafe
	isort --profile black --line-length 120 foxysafe
	ruff --fix --line-length 120 foxysafe
