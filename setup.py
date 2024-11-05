from setuptools import setup, find_packages

# Read the contents of requirements.txt
with open("requirements.txt") as f:
        requirements = f.read().splitlines()

        setup(
                name="replgpt",
                version="0.1.0",
                description="An interactive REPL with GPT-based assistance",
                long_description=open("README.md").read(),
                long_description_content_type="text/markdown",
                author="Your Name",
                author_email="your.email@example.com",
                url="https://github.com/yourusername/replgpt",
                packages=find_packages(),
                include_package_data=True,
                python_requires=">=3.6",
                install_requires=requirements,  # Load dependencies from requirements.txt
                entry_points={
                "console_scripts": [
                                "replgpt=replgpt.replgpt:main",
                            ],
                    },
                classifiers=[
                        "Programming Language :: Python :: 3",
                        "License :: OSI Approved :: BSD License",
                        "Operating System :: OS Independent",
                    ],
            )
