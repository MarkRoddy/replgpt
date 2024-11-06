# Define variables
PACKAGE_NAME = replgpt
DIST_DIR = dist

# Default target: build the package
build: deps
	@echo "Building the package..."
	python setup.py sdist bdist_wheel

# System dependencies needed for installing and managing dependencies
deps: 
	pip install setuptools wheel twine

# Clean build artifacts
clean:
	@echo "Cleaning up build artifacts..."
	rm -rf $(DIST_DIR) *.egg-info build

# Upload to Test PyPI
upload-test: build
	@echo "Uploading to Test PyPI..."
	twine upload --repository-url https://test.pypi.org/legacy/ $(DIST_DIR)/*

# Upload to official PyPI
upload: build
	@echo "Uploading to PyPI..."
	twine upload $(DIST_DIR)/*

# Install the package from Test PyPI for testing
install-test:
	@echo "Installing package from Test PyPI..."
	pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple $(PACKAGE_NAME)

# Uninstall the package from Test PyPI
uninstall-test:
	@echo "Uninstalling package installed from Test PyPI..."
	pip uninstall -y $(PACKAGE_NAME)

# Install the package from PyPI
install:
	@echo "Installing package from PyPI..."
	pip install $(PACKAGE_NAME)

# Uninstall the package installed from PyPI
uninstall:
	@echo "Uninstalling package installed from PyPI..."
	pip uninstall -y $(PACKAGE_NAME)

# Full pipeline to build, upload to Test PyPI, install, and test
test-pypi: clean upload-test install-test
	@echo "Test PyPI upload and installation complete."
	replgpt

# Full pipeline to build, upload to PyPI, install, and test
release: clean upload install
	@echo "Release to PyPI complete."

.PHONY: build clean upload-test upload install-test uninstall-test install uninstall test-pypi release
