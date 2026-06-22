#!/bin/bash

content=$(cat "$1")

read -r -d '' prompt << EOL
Review the provided code and suggest improvements based on best practices, readability, and maintainability.
Identify and remove any code smells or anti-patterns. Provide code examples where applicable.
Respond in Markdown format.
Finally, present a revised version of the code incorporating the suggested improvements.
If the file contains no code or requires no changes, state 'No changes needed'.
EOL

# suggestions=$(docker exec ollama ollama run deepseek-r1:1.5b "Code: $content $prompt")
# echo ${suggestions}
docker exec ollama ollama run stable-code "Code: $content $prompt"
