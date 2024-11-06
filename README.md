# replgpt

`replgpt` is an interactive Python REPL enhanced with OpenAI's GPT models for intelligent assistance. This tool allows you to interleave Python commands and prompting for code generation and guidance from a GPT-based assistant.

## Features

- **Standard Python REPL**: Execute Python commands directly in the REPL. Code you write and it's results will be automatically added to your chat context.
- **GPT-Enhanced Responses**: Enter natural language commands to generate code and receive helpful responses from OpenAI's GPT model.
- **File Context**: Load files into context so your assistant can reference them.

## Installation

Install `replgpt` directly from PyPI:

```bash
pip install replgpt
```

# Usage

## Set Up API Key

Set the OPENAI_API_KEY environment variable with your OpenAI API key:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

After installing, start the REPL with:

replgpt

## Commands

Basic Commands

* Python Commands: Enter Python code as you would in a standard REPL.
* Natural Language: Enter plain text to interact with the assistant.

Special Commands inside the REPL:

* /file_to_context <file_path>: Loads the specified file into context, making its contents accessible to the assistant for reference.


Example Workflow

1.Start replgpt: Run the command replgpt in your terminal.
2.Load a File: Use /file_to_context <file_path> to load a file for context.
3.Ask Questions or Run Code: Enter natural language commands or Python code.

