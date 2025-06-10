# /ComfyUI-Prompt-Formatter/__init__.py

# Ensure utils are loaded first to check dependencies
from . import prompt_formatter_utils

# Import node classes
from .categorized_prompt_formatter import CategorizedPromptFormatter
from .categorized_random_prompt_formatter import CategorizedRandomPromptFormatter
from .categorized_prompt_analyzer import CategorizedPromptAnalyzer
from .wildcard_importer import WildcardImporter

# Standardize NODE_NAME attribute in WildcardImporter for consistency
if not hasattr(WildcardImporter, 'NODE_NAME'):
    WildcardImporter.NODE_NAME = "Wildcard Importer"

# Mapping node implementations
NODE_CLASS_MAPPINGS = {
    CategorizedPromptFormatter.NODE_NAME: CategorizedPromptFormatter,
    CategorizedRandomPromptFormatter.NODE_NAME: CategorizedRandomPromptFormatter,
    CategorizedPromptAnalyzer.NODE_NAME: CategorizedPromptAnalyzer,  
    WildcardImporter.NODE_NAME: WildcardImporter,
}

# Mapping display names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    CategorizedPromptFormatter.NODE_NAME: "📝 Categorized Prompt Formatter",
    CategorizedRandomPromptFormatter.NODE_NAME: "🎲 Categorized Random Prompt Formatter",
    CategorizedPromptAnalyzer.NODE_NAME: "📊 Categorized Prompt Analyzer", 
    WildcardImporter.NODE_NAME: "📂 Wildcard Importer",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

# Print loading info to console
print("\n### Loading: ComfyUI-Prompt-Formatter (Version: 1.4.2) ###")
for name, display_name in NODE_DISPLAY_NAME_MAPPINGS.items():
    print(f"  - {name} -> {display_name}")
print("###-------------------------------------------###\n")