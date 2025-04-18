# /ComfyUI-Prompt-Formatter/__init__.py

# Import the node class
from .categorized_prompt_formatter import CategorizedPromptFormatter, NODE_NAME as NODE_NAME_FORMATTER
from .categorized_random_prompt_formatter import CategorizedRandomPromptFormatter, NODE_NAME_RANDOM
from .categorized_prompt_analyzer import CategorizedPromptAnalyzer, NODE_NAME_ANALYZER

# Mapping node class names to implementations
NODE_CLASS_MAPPINGS = {
    NODE_NAME_FORMATTER: CategorizedPromptFormatter,
    NODE_NAME_RANDOM: CategorizedRandomPromptFormatter,
    NODE_NAME_ANALYZER: CategorizedPromptAnalyzer,   
}

# Mapping node class names to display names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    NODE_NAME_FORMATTER: "📝 Categorized Prompt Formatter",
    NODE_NAME_RANDOM: "🎲 Categorized Random Prompt Formatter",
    NODE_NAME_ANALYZER: "📊 Categorized Prompt Analyzer", 
}
# A dictionary that contains all nodes in this file
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("...")
print("### Loading: ComfyUI-Prompt-Formatter ###")
print("### Version: 1.3")
print(f"### Node: {NODE_NAME_FORMATTER} -> {NODE_DISPLAY_NAME_MAPPINGS[NODE_NAME_FORMATTER]}")
print(f"### Node: {NODE_NAME_RANDOM} -> {NODE_DISPLAY_NAME_MAPPINGS[NODE_NAME_RANDOM]}")
print(f"### Node: {NODE_NAME_ANALYZER} -> {NODE_DISPLAY_NAME_MAPPINGS[NODE_NAME_ANALYZER]}")
print("...")