import unittest, os
from replgpt.replgpt import LLMEnhancedREPL

class TestLLMEnhancedREPL(unittest.TestCase):

    def setUp(self):
        # Set up any necessary objects or state before each test
        self.repl = LLMEnhancedREPL()

    def test_toggle_json_mode(self):
        # Test toggling JSON mode
        initial_mode = self.repl.use_json_mode
        self.repl.toggle_json_mode()
        self.assertNotEqual(initial_mode, self.repl.use_json_mode)

    def test_add_file_to_context(self):
        # Test adding a file to context (example test, adjust as needed)
        test_file_path = "tests/test_file.txt"
        try:
            with open(test_file_path, "w") as f:
                f.write("Sample content for testing.")

            self.repl.add_file_to_context(test_file_path)
            self.assertIn(test_file_path, self.repl.file_context)
            self.assertEqual(self.repl.file_context[test_file_path], "Sample content for testing.")
        finally:
            # Clean up the test file
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    def tearDown(self):
        # Clean up if necessary after each test
        self.repl = None

if __name__ == '__main__':
    unittest.main()
