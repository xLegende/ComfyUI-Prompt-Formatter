# /ComfyUI-Prompt-Formatter/categorized_prompt_formatter.py

import yaml
import re
from collections import defaultdict

# Local utility imports
from .prompt_formatter_utils import (
    find_yaml_file,
    parse_tag,
    clean_output_string,
    resolve_category_tags,
    INCLUDE_DIRECTIVE,
    TAGS_KEY
)

class CategorizedPromptFormatter:
    """
    A ComfyUI node to categorize and format tags from a prompt using a YAML file.
    """
    NODE_NAME = "Categorized Prompt Formatter"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "category_definition_file": ("STRING", {"default": "prompt_categories.yaml"}),
                "output_template": ("STRING", {"multiline": True, "default": "<|quality|>, <|character|>, <|clothing|>, <|setting|>"}),
            },
            "optional": {
                 "input_delimiter": ("STRING", {"default": ","}),
                 "output_delimiter": ("STRING", {"default": ", "}),
                 "strip_whitespace": ("BOOLEAN", {"default": True}),
                 "case_sensitive_matching": ("BOOLEAN", {"default": False}),
                 "handle_weights": ("BOOLEAN", {"default": True}),
                 "match_underscores_spaces": ("BOOLEAN", {"default": True}),
                 "disable_duplicates": ("BOOLEAN", {"default": False}),
                 "unmatched_tag_handling": (["discard", "append_end", "output_separately"], {"default": "discard"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("formatted_prompt", "rejected_prompt")
    FUNCTION = "format_prompt"
    CATEGORY = "text/filtering"

    def format_prompt(self, prompt, category_definition_file, output_template, **kwargs):
        # --- 1. Load & Resolve Category Definitions ---
        tag_to_categories_map = defaultdict(list)
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
            resolved_tags_cache = {}
            for cat_name in list(raw_yaml_data.keys()):
                if str(cat_name).strip() not in [INCLUDE_DIRECTIVE, TAGS_KEY]:
                    resolve_category_tags(cat_name, raw_yaml_data, resolved_tags_cache, self.NODE_NAME)

            case_sensitive = kwargs.get("case_sensitive_matching", False)
            for cat_name, tags_set in resolved_tags_cache.items():
                for tag in tags_set:
                    key = tag if case_sensitive else tag.lower()
                    if key: tag_to_categories_map[key].append(cat_name)

            for key in tag_to_categories_map:
                tag_to_categories_map[key] = list(set(tag_to_categories_map[key]))
        
        # --- 2. Parse Input Prompt & Categorize ---
        categorized_tags = defaultdict(list)
        all_input_tags = set()
        matched_tags = set()

        handle_weights = kwargs.get("handle_weights", True)
        match_spaces = kwargs.get("match_underscores_spaces", True)
        case_sensitive = kwargs.get("case_sensitive_matching", False)

        for raw_tag in prompt.split(kwargs.get("input_delimiter", ",")):
            tag_original = raw_tag.strip() if kwargs.get("strip_whitespace", True) else raw_tag
            if not tag_original: continue
            all_input_tags.add(tag_original)

            _, base_parsed = parse_tag(tag_original, handle_weights)
            lookup_key = base_parsed if case_sensitive else base_parsed.lower()
            
            variants = {lookup_key}
            if match_spaces:
                variants.add(lookup_key.replace(' ', '_'))
                variants.add(lookup_key.replace('_', ' '))

            for variant in variants:
                if variant in tag_to_categories_map:
                    for category in tag_to_categories_map[variant]:
                        categorized_tags[category].append(tag_original)
                    matched_tags.add(tag_original)
                    break

        # --- 3. Process Template ---
        output_delimiter = kwargs.get("output_delimiter", ", ")
        disable_dupes = kwargs.get("disable_duplicates", False)
        added_tags = set()
        used_tags = set()
        result_parts = []
        last_end = 0

        for match in re.finditer(r"<\|([^:]+?)(?::(-?\d+))?\|>", output_template):
            cat_name, limit_str, start, end = match.group(1).strip(), match.group(2), *match.span()
            result_parts.append(output_template[last_end:start])
            
            limit = int(limit_str) if limit_str else None
            tags_for_cat = categorized_tags.get(cat_name, [])
            
            tags_to_process = tags_for_cat
            if limit is not None:
                tags_to_process = tags_for_cat[:limit] if limit > 0 else (tags_for_cat[limit:] if limit < 0 else [])

            used_tags.update(tags_to_process)
            tags_to_join = [t for t in tags_to_process if not (disable_dupes and t in added_tags and not added_tags.add(t))]
            if tags_to_join: result_parts.append(output_delimiter.join(tags_to_join))
            last_end = end
        
        result_parts.append(output_template[last_end:])
        formatted_prompt = "".join(result_parts)

        # --- 4. Handle Unmatched Tags ---
        unmatched_handling = kwargs.get("unmatched_tag_handling", "discard")
        rejected_prompt = ""
        if unmatched_handling != "discard":
            rejected_tags = list(all_input_tags - used_tags)
            if rejected_tags:
                rejected_prompt = output_delimiter.join(rejected_tags)
                if unmatched_handling == "append_end":
                    if formatted_prompt: formatted_prompt += output_delimiter
                    formatted_prompt += rejected_prompt
                    rejected_prompt = ""

        return (clean_output_string(formatted_prompt, output_delimiter), clean_output_string(rejected_prompt, output_delimiter))