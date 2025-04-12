# /ComfyUI-Prompt-Formatter/__init__.py

# Import the node class
from .categorized_prompt_formatter import CategorizedPromptFormatter, NODE_NAME

# Mapping node class names to implementations
NODE_CLASS_MAPPINGS = {
    NODE_NAME: CategorizedPromptFormatter
}

# Mapping node class names to display names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    NODE_NAME: "📝 Categorized Prompt Formatter" # Add an emoji for fun!
}

# A dictionary that contains all nodes in this file
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("...")
print("### Loading: ComfyUI-Prompt-Formatter ###")
print("### Version: 1.1")
print(f"### Node: {NODE_NAME} -> {NODE_DISPLAY_NAME_MAPPINGS[NODE_NAME]}")
print("...")