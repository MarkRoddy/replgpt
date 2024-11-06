import unittest


from replgpt.prompt_or_code import is_python_with_syntax_error

class TestPromptOrCode(unittest.TestCase):
    # Integration tests which hit the OpenAI API.

    def test_is_python_with_syntax_error(self):
        """Test some sample prompts"""
        valid_inputs = [
            "Hello, world!",
            "This is a test sentence.",
            "Is this plain text?",
            "Hello! How are you?",
            "Just checking, 123456.",
            "Please update the foo_bar() to use a list comprehension instead of a loop."
        ]
        for text in valid_inputs:
            with self.subTest(text=text):
                self.assertFalse(is_python_with_syntax_error(text))

    def test_is_python_with_syntax_error_has_error(self):
        """Test invalid inputs that should not be considered plain text."""
        invalid_inputs = [
            "print('Hello'",
            "if a = b: return True",  # Conditional statement
            "daf my_function(): pass",  # Function definition
        ]
        for text in invalid_inputs:
            with self.subTest(text=text):
                self.assertTrue(is_python_with_syntax_error(text), text)

if __name__ == '__main__':
    unittest.main()
