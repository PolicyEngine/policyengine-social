.PHONY: install test format lint clean run-tests coverage

# Install dependencies
install:
	pip install -e ".[dev]"
	playwright install chromium

# Run all tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
coverage:
	coverage run -m pytest tests/ -v
	coverage report -m
	coverage html
	@echo "Coverage report generated in htmlcov/index.html"

# Format code
format:
	black scripts/ tests/
	isort scripts/ tests/

# Lint code
lint:
	flake8 scripts/ tests/ --max-line-length=100
	black --check scripts/ tests/
	mypy scripts/ --ignore-missing-imports

# Clean up generated files
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	rm -rf assets/cache/* assets/optimized/*
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Run specific test file
test-file:
	@read -p "Enter test file name (e.g., test_extract_blog_images): " file; \
	python -m pytest tests/$$file.py -v

# Generate social post for testing
generate-test:
	python scripts/generate_social_post.py \
		--slug nsf-pose-phase-1-grant \
		--title "National Science Foundation awards PolicyEngine $$300,000 grant" \
		--output posts/queue/test-post.yaml

# Extract images from a blog post
extract-images:
	@read -p "Enter blog slug: " slug; \
	python scripts/extract_blog_images.py --slug $$slug --download

# Validate all YAML files
validate-yaml:
	@python -c "import yaml; from pathlib import Path; \
	[yaml.safe_load(open(f)) for f in Path('.').rglob('*.yaml') if '.github' not in str(f)]" \
	&& echo "✓ All YAML files are valid"

# Check everything before commit
pre-commit: format lint test validate-yaml
	@echo "✓ All checks passed - ready to commit!"

# Help
help:
	@echo "Available commands:"
	@echo "  make install      - Install all dependencies"
	@echo "  make test        - Run all tests"
	@echo "  make coverage    - Run tests with coverage report"
	@echo "  make format      - Format code with black"
	@echo "  make lint        - Lint code"
	@echo "  make clean       - Clean generated files"
	@echo "  make pre-commit  - Run all checks before committing"