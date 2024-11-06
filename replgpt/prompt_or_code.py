
import openai

system_message = (
    "You are an assistant tasked with evaluating Python code snippets. "
    "Determine whether the provided code snippet mostly consists of valid Python code that happens to contain a syntax error, "
    "or if it is something other than Python code. "
    "Respond with 'True' if it mostly looks like correct Python code, and 'False' otherwise."
    "Some examples: "
    "* This is missing a trailing paranthasis: print('Hello'"
    "* This uses a single equals for comparison, when it should be using two: if a = b: print(True)"
    "* This uses the old style print statement instead of a function style: print x"
    )

# Using gpt-4o instead of gpt-4o-mini which is the default for the repl as it
# consistently fails on some examples provided above.
openai_model="gpt-4o"

def is_python_with_syntax_error(code_snippet):
    """
    Evaluate a Python code snippet that is confirmed to generate a syntax error.

    :param code_snippet: A string containing Python code that is invalid.
    :return: Boolean indicating whether the snippet mostly contains valid Python code.
    """
    user_message = (
        f"The following Python code snippet contains a syntax error:\n\n"
        f"{code_snippet}\n"
    )

    msgs = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
        ]
    
    # Call OpenAI API to evaluate the code snippet
    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=msgs,
    )
    # Extract the response
    answer = response["choices"][0]["message"]["content"].strip()

    # Check if the response is a boolean-like answer
    if answer.lower() in ['true', 'false']:
        return answer.lower() == 'true'
    else:
        raise ValueError("Unexpected response format. Expected 'True' or 'False'.")
        

def is_prompt(code_snippet):
    return not is_python_with_syntax_error(code_snippet)
