# /ComfyUI-Prompt-Formatter/__init__.py

# Import the node class
from .categorized_prompt_formatter import CategorizedPromptFormatter, NODE_NAME as NODE_NAME_FORMATTER
from .categorized_random_prompt_formatter import CategorizedRandomPromptFormatter, NODE_NAME_RANDOM

# Mapping node class names to implementations
NODE_CLASS_MAPPINGS = {
    NODE_NAME_FORMATTER: CategorizedPromptFormatter,
    NODE_NAME_RANDOM: CategorizedRandomPromptFormatter, 
}

# Mapping node class names to display names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    NODE_NAME_FORMATTER: "📝 Categorized Prompt Formatter",
    NODE_NAME_RANDOM: "📝 Categorized Random Prompt Formatter",
}
# A dictionary that contains all nodes in this file
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("...")
print("### Loading: ComfyUI-Prompt-Formatter ###")
print("### Version: 1.2")
print(f"### Node: {NODE_NAME_FORMATTER} -> {NODE_DISPLAY_NAME_MAPPINGS[NODE_NAME_FORMATTER]}")
print(f"### Node: {NODE_NAME_RANDOM} -> {NODE_DISPLAY_NAME_MAPPINGS[NODE_NAME_RANDOM]}")
print("...")