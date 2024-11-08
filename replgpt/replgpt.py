import code
import openai
import re
import readline  # For enhanced REPL history handling
import os
import sys
import io
import json
import readline
import traceback
from contextlib import redirect_stdout, redirect_stderr
from collections import OrderedDict

from replgpt import prompt_or_code


system_prompt = """
You are a Python coding assistant embedded within a Python REPL environment. In addition to user
provided prompts, you will also be supplied with a list of Python code the user has run as well
as the output from the commands. Use both these to inform how you respond to user prompts.
Additionally, a user may choose to provide you with the contents of files on their system. This
is likely going to be the contents of Python files they are working with but in theory it could
be any type of file. Use this to inform your responses well.

User prompts will likely contain requests to generate Python code. Please do so and follow any
style or conventions the user requests. Barring that, try to match style and conventions to that
of any python files provided, and to a lesser extent, match the style of commands run by the user.

Bear in mind that the user will be actively running Python code in the context of the REPL which
is providing you with prompts. While you may be able to run Python code yourself, there is never
a case where you should do so, even if they request you to do so. In that case, you should consider
the request directed at the REPL and not yourself.

Lastly, a REPL environment is constrained to the space provided by a terminal, as such breviaty
is essential. Please refrain from any unnecessary niceties such as 'have a great day'. In addition,
refrain from providing examples that were not requested. For example, if a user requests a function
to be generated, do not provide sample input and/or outputs for this function.
"""

json_system_prompt = """
Provide the following pieces of information in your response:
- user_visible_response: The text to be displayed to the user in response to their prompt. This may or may not include Python code.
- python_code: A piece of Python code that either the user requested directly, or code that would perform an action the user requested to be performed. An example of the former is if the user said 'write a function that...', this attribute should contain a copy of the function requested. Note that that function should still show up in the user visible reponse. An example of code to impliment an action is if the user said 'print the contents of variable x'. In this case, the python_code attribute should contain the code to print this variable. Note that the code in this attribute will not be shown to the user. So if you think it's useful for the user to see the code, you should include it in the user_visible_response attribute.
- should_execute: Whether or not you believe the user wants the code you generated to be executed. If the user asked you to generate code that defines something, such as a function or class, you can infer it should be executed unless there would be clear side effects. If the user asks for unstructred code, say 'write code that lists the contents of my cwd', use your judgement. However, if the user requested an action to be performed, say 'lists the contents of my cwd', flag this as something that should be executed. However, in the face of ambiguity, you should set should_execute to false.
"""

response_json_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "repl_response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "user_visible_response": {"type": "string"},
                "python_code": {"type": "string"},
                "should_execute":  {"type": "boolean"},
                },
            "required": ["user_visible_response", "python_code", "should_execute"],
            "additionalProperties": False
            }
        }
    }

welcome_banner = """Welcome to ReplGPT, the LLM-Enhanced Python REPL!

This REPL allows you to:
- Enter and execute Python code which will be included your AI Agent's context window.
- Enter natural language prompts to interact with your Agent.
- Automatically execute code generated by the Agent.

You also have a few useful commands at your disposal, such as controlling automatic code execution and adding local information to the Agent's context window. Run /help to see more details on these commands.

For now, type in your Python code or prompts below."""
# - /eval - Run any Python code in the last response from your AI assistant. Can be called multiple times.

help_text = """
Welcome to ReplGPT, the LLM-Enhanced Python REPL!

ReplGPT is a Python REPL that lets you freely switch between writing Python code and issuing LLM prompts. Any code you run as
well as its output is included in the AI Assistants context window to aid in its responses, and any code generated by
your prompts is automatically executed and becomes available in your REPL session.

You also have a few useful commands at your disposal:
- /help - Print this help message.

- /file_to_context <file_path> - Read the contents of a local file and load it into the Agent's context window. This is can
be used to import documentation into the Agent's memory, or give it knowledge of existing code you'd like to work with inside
of the REPL. Or, if you want to understand a project's dependencies better, run `/file_to_context requirements.txt` and ask
your agent about the libraries the libraries used.


- /auto_eval <strategy> - Controls what the REPL will do with code generated by your AI agent. The default strategy of 'always'
means that any code returned by the Agent will be executed. If you have any concerns about this behavior, you can toggle this
to `never`. Alternatively, the 'infer' strategy will make an additional LLM to evaluate the safety of the generated code. In
practice this should only allow definitions (functions and classes) but will not execute code that could have side effects.
"""


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
        self.use_json_mode = False  # Toggle for JSON-based API response mode
        self.file_context = OrderedDict()  # Store file paths and their contents in the order they were added
        self.auto_eval_strategy = 'always'
        
        # Initialize the system message (REPL description) as part of the conversation
        self.system_message = {
            "role": "system",
            "content": self.get_system_prompt()
        }
        self.conversation_history.append(self.system_message)

    def get_system_prompt(self):
        if self.use_json_mode:
            return json_system_prompt
        else:
            return system_prompt

    def toggle_json_mode(self):
        self.use_json_mode = not self.use_json_mode
        # Update system prompt based on the mode
        self.system_message = {
            "role": "system",
            "content": self.get_system_prompt()
        }
        # Reset conversation history with updated system prompt
        self.conversation_history = [self.system_message]
        print(f"JSON mode {'enabled' if self.use_json_mode else 'disabled'}.")

    def push(self, line):
        # Allow special command to print conversation history or toggle JSON mode
        if line.strip() == "/print_history":
            self.print_conversation_history()
            return
        elif line.strip() == "/toggle_json_mode":
            self.toggle_json_mode()
            return
        elif line.strip() == "/help":
            print(help_text)
            return
        elif line.startswith("/debug"):
            openai.log = "debug"
            return
        elif line.startswith("/file_to_context"):
            _, file_path = line.split(maxsplit=1)
            self.add_file_to_context(file_path)
            return
        elif line.startswith("/auto_eval"):
            _, strategy = line.split(maxsplit=1)
            valid_strategies = ['always', 'never', 'infer']
            if strategy not in valid_strategies:
                print(f"Error: Invalid strategy '{strategy}'. Try one of the following: {', '.join(valid_strategies)}, or run /help for more info.")
            else:
                self.auto_eval_strategy = strategy
            return

        # Track command and its output/errors
        output_stream = DualStream(sys.stdout)  # For capturing and displaying stdout
        error_stream = DualStream(sys.stderr)  # For capturing and displaying stderr

        # Redirect stdout and stderr to capture both streams
        with redirect_stdout(output_stream), redirect_stderr(error_stream):
            try:
                compiled_code = compile(line, "<stdin>", "single")
                exec(compiled_code, self.locals)
            except SyntaxError as e:
                if prompt_or_code.is_prompt(line):
                    self.handle_prompt(line)
                else:
                    print(f"SyntaxError: {e}")
            except Exception as e:
                # Print the exception exactly as it would normally be displayed
                traceback.print_exc()

        # Capture output and errors for history
        raw_output = output_stream.get_value()
        raw_errors = error_stream.get_value()

        char_thesh = self.retained_char_threshold()
        output = self.limit_command_output(raw_output, char_thesh)
        errors = self.limit_command_output(raw_errors, char_thesh)
        
        # Store command, output, and errors in history for context    
        command_entry = f">>> {line}\n{output}"
        if errors.strip():
            command_entry += f"\n{errors}"
        self.history.append(command_entry)

    def limit_command_output(self, output, char_threshold):
        """
        Given a potentially large amount of output from a Python command,
        thoughtfully limit the size of the output before retaining it for
        inclusion in our conversation. If the output is less that the
        character threshold, this function is a no-op.
        """
        output = output.strip()
        if len(output) < char_threshold:
            return output
        else:
            half_threshold = char_threshold // 2
            beginning = output[:half_threshold]
            end = output[-half_threshold:]
            return f"{beginning}\n<output truncated>\n{end}"

    def retained_char_threshold(self):
        # We don't want to overflow the context window with the output from a runaway
        # command so we truncate over a certain threshold. This threshold is arbitrarily
        # decided to be 1% of the total context window for a gpt-4o-mini model, the current
        # current default model for the repl. This model has a 128,000 token contenxt limit,
        # and OpenAI states that a token is roughly 4 chars. So we calculate our threshold
        # here, then use that to limit the command output retained.
        token_threshold = 128000 * 0.01 
        char_threshold = token_threshold * 4
        return int(char_threshold)
    
    def add_file_to_context(self, file_path):
        try:
            with open(file_path, "r") as file:
                self.file_context[file_path] = file.read()
                print(f"File '{file_path}' added to context.")
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}")

    def handle_prompt(self, user_input):
        if self.use_json_mode:
            self.handle_json_prompt(user_input)
        else:
            self.handle_standard_prompt(user_input)

    def build_user_message(self, user_input):
        # Build user message with command history and file contents
        message_content = (
            "The following are the last entered Python commands with their outputs and errors:\n\n" +
            "\n".join(self.history)
        )

        # Include file contents if any files are loaded
        if self.file_context:
            message_content += "\n\nIncluding file contents:\n"
            for file_path, file_contents in self.file_context.items():
                message_content += f"\nFile: {file_path}\n{file_contents}\n"

        # Append user input to the message content
        message_content += f"\n\nUser input: {user_input}"

        # Create and return the user message structure
        return {
            "role": "user",
            "content": message_content
        }

    def handle_standard_prompt(self, user_input):
        user_message = self.build_user_message(user_input)
        self.conversation_history.append(user_message)

        try:
            # Send the conversation history to the OpenAI API for context continuity
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=self.conversation_history,
                stream=True  # Stream response
            )

            # Process streamed response
            full_response = ""
            for chunk in response:
                text = chunk["choices"][0]["delta"].get("content", "")
                print(text, end="", flush=True)
                full_response += text

            # While we have the full output, check if new need to print a \n char or not. If
            # we don't do this we get the '>>>' input prompt on the same line as the
            # LLM response.
            if not full_response.endswith("\n"):
                print("")

            # Append the assistant's response to conversation history for context
            assistant_message = {"role": "assistant", "content": full_response}
            self.conversation_history.append(assistant_message)

            # Check if there's Python code in the response and prompt user to execute it
            code_snippet = self.extract_code(full_response)
            if code_snippet and ('always' == self.auto_eval_strategy):
                self.execute_code(code_snippet)

        except openai.error.OpenAIError as e:
            print(f"Error communicating with OpenAI API: {e}")
            print("Returning to REPL prompt.")

        # Clear command history after each prompt submission
        self.history.clear()
        self.file_context.clear()

    def handle_json_prompt(self, user_input):
        user_message = self.build_user_message(user_input)
        self.conversation_history.append(user_message)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=self.conversation_history,
                response_format=response_json_schema,
                )
            json_response = response.choices[0].message.content
            response = json.loads(json_response)

            # Display text to the user
            print(response.get("user_visible_response", ""))

            # Execute code if we got code and `should_execute` is True
            if response.get("should_execute") and response.get("python_code"):
                print("Executing generated code...")
                self.execute_code(response["python_code"])

            # Append assistant's response to conversation history for context
            self.conversation_history.append({"role": "assistant", "content": json_response})

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
        except openai.error.OpenAIError as e:
            print(f"Error communicating with OpenAI API: {e}")
            print("Returning to REPL prompt.")

        # Clear command history after each prompt submission
        self.history.clear()
        self.file_context.clear()

    def extract_code(self, text):
        match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        return match.group(1) if match else None

    def execute_code(self, code_snippet):
        try:
            exec(code_snippet, self.locals)
            print("Code executed successfully.")

            # Add code to the input history, as if the user typed it themselves
            readline.add_history(code_snippet)
        except Exception as e:
            print(f"Error executing code: {e}")
        
    def raw_input(self, prompt=">>> "):
        try:
            return input(prompt)
        except EOFError:
            print("\nExiting REPL.")
            raise SystemExit

    def print_conversation_history(self):
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
    repl.interact(banner = welcome_banner)
    
if __name__ == "__main__":
    main()
