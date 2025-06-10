#/ComfyUI-Prompt-Formatter/categorized_random_prompt_formatter.py

import yaml
import re
import random

# Local utility imports
from .prompt_formatter_utils import (
    find_yaml_file,
    clean_output_string,
    resolve_category_tags,
    INCLUDE_DIRECTIVE,
    TAGS_KEY
)

class CategorizedRandomPromptFormatter:
    """
    A ComfyUI node to generate random prompts from categories defined in a YAML file.
    """
    NODE_NAME = "Categorized Random Prompt Formatter"

          
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "category_definition_file": ("STRING", {"default": "prompt_categories.yaml"}),
                "output_template": ("STRING", {
                    "multiline": True,
                    "default": "<|quality:1|>, <|character:1|>, <|details:3|>, <|setting:1|>"
                }),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}),
            },
            "optional": { "output_delimiter": ("STRING", {"default": ", "}) }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("random_prompt", "used_seed")
    FUNCTION = "generate_prompt"
    CATEGORY = "text/generation" 

    def generate_prompt(self, category_definition_file, output_template, seed, output_delimiter=", "):
        # --- 1. Handle Seed ---
        used_seed = random.randint(0, 0xffffffffffffffff) if seed == -1 else seed
        rng = random.Random(used_seed)

        # --- 2. Load & Resolve Categories ---
        resolved_categories = {}
        yaml_path = find_yaml_file(category_definition_file, self.NODE_NAME)
        raw_yaml_data = None

        if yaml_path:
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    raw_yaml_data = yaml.safe_load(f)
                if not isinstance(raw_yaml_data, dict):
                     print(f"Warning [{self.NODE_NAME}]: YAML file '{yaml_path}' is not a dictionary.")
                     raw_yaml_data = None
            except Exception as e:
                 print(f"Error [{self.NODE_NAME}]: Loading YAML file {yaml_path}: {e}")

        if raw_yaml_data:
            cache = {}
            for cat_name in list(raw_yaml_data.keys()):
                if str(cat_name).strip() not in [INCLUDE_DIRECTIVE, TAGS_KEY]:
                    resolved_categories[str(cat_name).strip()] = resolve_category_tags(cat_name, raw_yaml_data, cache, self.NODE_NAME)
        else:
            return ("", used_seed)

        # --- 3. Process Template & Generate Prompt ---
        result_parts = []
        last_end = 0
        for match in re.finditer(r"<\|([^:]+?)(?::(\d+))?\|>", output_template):
            cat_name, count_str, start, end = match.group(1).strip(), match.group(2), *match.span()
            result_parts.append(output_template[last_end:start])
            
            num_to_pick = int(count_str) if count_str and int(count_str) >= 0 else 1
            if num_to_pick > 0:
                available_tags = list(resolved_categories.get(cat_name, []))
                if available_tags:
                    sample_count = min(num_to_pick, len(available_tags))
                    tags_to_join = rng.sample(available_tags, sample_count)
                    result_parts.append(output_delimiter.join(tags_to_join))
                else:
                    print(f"Warning [{self.NODE_NAME}]: Category '{cat_name}' not found or empty.")
            
            last_end = end
        
        result_parts.append(output_template[last_end:])
        final_prompt = clean_output_string("".join(result_parts), output_delimiter)
        
        return (final_prompt, used_seed)

    