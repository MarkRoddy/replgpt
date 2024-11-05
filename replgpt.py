import code
import openai
import re
import readline  # For enhanced REPL history handling
import os
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

class DualStream:
    """
    Custom stream class to write output to both a target (console) and a buffer (for capturing history).
    """
    def __init__(self, target):
        self.target = target  # Target file-like object (e.g., sys.stdout or sys.stderr)
        self.buffer = io.StringIO()  # Buffer to capture all output

    def write(self, message):
        self.target.write(message)  # Write to the console (or target) immediately
        self.target.flush()  # Ensure immediate display
        self.buffer.write(message)  # Capture to buffer

    def get_value(self):
        return self.buffer.getvalue()

    def flush(self):
        self.target.flush()

class LLMEnhancedREPL(code.InteractiveConsole):
    def __init__(self, locals=None):
        super().__init__(locals=locals)
        self.history = []  # Track command history with outputs and errors
        self.in_conversation = False  # Track conversation status with LLM
        self.conversation_history = []  # Preserve full conversation context over time

        # Initialize the system message (REPL description) as part of the conversation
        self.system_message = {
            "role": "system",
            "content": (
                "This is an interactive REPL that integrates Python code execution with an AI assistant. "
                "If the user enters Python code, it will be executed; if they enter plain text, treat it as conversation."
            )
        }
        self.conversation_history.append(self.system_message)

    def push(self, line):
        # Allow special command to print conversation history
        if line.strip() == "/print_history":
            self.print_conversation_history()
            return

        # Create DualStream instances for stdout and stderr
        output_stream = DualStream(sys.stdout)  # For capturing and displaying stdout
        error_stream = DualStream(sys.stderr)  # For capturing and displaying stderr

        # Redirect stdout and stderr to capture both streams
        with redirect_stdout(output_stream), redirect_stderr(error_stream):
            try:
                compiled_code = compile(line, "<stdin>", "single")
                exec(compiled_code, self.locals)
            except SyntaxError as e:
                if self.is_plain_text(line):
                    self.handle_prompt(line)
                else:
                    print(f"SyntaxError: {e}")
            except Exception as e:
                # Print the exception exactly as it would normally be displayed
                traceback.print_exc()

        # Capture output and errors for history
        output = output_stream.get_value()
        errors = error_stream.get_value()

        # Store command, output, and errors in history for context
        command_entry = f">>> {line}\n{output.strip()}"
        if errors.strip():
            command_entry += f"\n{errors.strip()}"
        self.history.append(command_entry)

    def is_plain_text(self, line):
        # Heuristic to determine if input is conversation text or bad syntax
        return bool(re.match(r'^[a-zA-Z0-9\s,.\'\"!?]+$', line.strip()))

    def handle_prompt(self, user_input):
        # Create user message that includes the history of Python commands with outputs and errors
        user_message = {
            "role": "user",
            "content": (
                "The following are the last entered Python commands with their outputs and errors:\n\n" +
                "\n".join(self.history) + "\n\nUser input: " + user_input
            )
        }
        self.conversation_history.append(user_message)

        try:
            # Send the conversation history to the OpenAI API for context continuity
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Use preferred model
                messages=self.conversation_history,
                stream=True  # Stream response
            )

            # Process streamed response
            full_response = ""
            for chunk in response:
                text = chunk["choices"][0]["delta"].get("content", "")
                print(text, end="", flush=True)
                full_response += text

            # Append the assistant's response to conversation history for context
            assistant_message = {"role": "assistant", "content": full_response}
            self.conversation_history.append(assistant_message)

            # Check if there's Python code in the response and prompt user to execute it
            code_snippet = self.extract_code(full_response)
            if code_snippet:
                self.ask_to_execute_code(code_snippet)

        except openai.error.OpenAIError as e:
            print(f"Error communicating with OpenAI API: {e}")
            print("Returning to REPL prompt.")

        # Clear command history after each prompt submission
        self.history.clear()

    def extract_code(self, text):
        # Simple regex to capture code blocks (for now, assume ```python format)
        match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        return match.group(1) if match else None

    def ask_to_execute_code(self, code_snippet):
        user_choice = input("\nDo you want to execute the returned code? (y/n): ")
        if user_choice.lower() in ("y", "yes"):
            try:
                exec(code_snippet, self.locals)
                print("Code executed successfully.")
            except Exception as e:
                print(f"Error executing code: {e}")

    def raw_input(self, prompt=">>> "):
        try:
            return input(prompt)
        except EOFError:
            print("\nExiting REPL.")
            raise SystemExit

    def print_conversation_history(self):
        # Print the current conversation history for the user
        print("\nConversation History:")
        for msg in self.conversation_history:
            role = msg["role"]
            content = msg["content"]
            print(f"{role.capitalize()}: {content}\n")

def main():
    # Set OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: The OPENAI_API_KEY environment variable is not set.")
        print("Please set the API key to use the LLM-enhanced REPL.")
        sys.exit(1)
    
    openai.api_key = api_key

    # Start the REPL
    repl = LLMEnhancedREPL()
    repl.interact()

if __name__ == "__main__":
    main()