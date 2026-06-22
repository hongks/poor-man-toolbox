"""
Code Review Script using Ollama's Code Llama Model.

This script takes a Python file as an argument, reads its content,
sends it to Ollama for a code review, and prints the suggestions.
"""

import ollama
import sys
from typing import Optional

# Ollama runs locally on port 11434
OLLAMA_SERVER_URL = "http://localhost:11434"


def get_code_review(code_snippet: str) -> str:
    """Sends a Python code snippet to Ollama for review and returns suggestions."""
    prompt = f"Review the following Python code and suggest improvements:\n\n```python\n{code_snippet}\n```"
    response = ollama.chat(
        model="deepseek-r1:1.5b", messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"]


def read_file(file_path: str) -> Optional[str]:
    """Reads the content of a file and returns it as a string."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except UnicodeDecodeError:
        print(f"Error: Could not read '{file_path}'. Ensure it is encoded in UTF-8.")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
    return None


def main() -> None:
    """Main function that reads the file, processes the code, and prints review suggestions."""
    if len(sys.argv) != 2:
        print("Usage: python code_review.py <file_path>")
        sys.exit(1)

    code_file_path = sys.argv[1]
    code = read_file(code_file_path)

    if code is not None:
        suggestions = get_code_review(code)
        print("Code Review Suggestions:\n", suggestions)


if __name__ == "__main__":
    main()
