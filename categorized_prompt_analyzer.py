# /ComfyUI-Prompt-Formatter/categorized_prompt_analyzer.py

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

class CategorizedPromptAnalyzer:
    """
    A node to analyze tag occurrences in a prompt against YAML-defined categories.
    """
    NODE_NAME = "Categorized Prompt Analyzer"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "analyze_targets": ("STRING", {"multiline": False, "default": "quality, eyes, 1girl"}),
                "category_definition_file": ("STRING", {"default": "prompt_categories.yaml"}),
            },
            "optional": {
                 "input_delimiter": ("STRING", {"default": ","}),
                 "target_delimiter": ("STRING", {"default": ","}),
                 "output_delimiter": ("STRING", {"default": ", "}),
                 "case_sensitive_matching": ("BOOLEAN", {"default": False}),
                 "handle_weights": ("BOOLEAN", {"default": True}),
                 "match_underscores_spaces": ("BOOLEAN", {"default": True}),
                 "generate_detailed_output": ("BOOLEAN", {"default": False}),
                 "generate_unmatched_output": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING")
    RETURN_NAMES = ("analysis_summary", "total_matched_count", "details", "unmatched_tags")
    FUNCTION = "analyze_prompt"
    CATEGORY = "text/analysis" 

    def analyze_prompt(self, prompt, analyze_targets, category_definition_file, **kwargs):
        # --- 1. Load & Resolve YAML ---
        resolved_category_tags = {} 
        yaml_path = find_yaml_file(category_definition_file, self.NODE_NAME)
        raw_yaml_data = None
        
        if yaml_path:
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f: raw_yaml_data = yaml.safe_load(f)
                if not isinstance(raw_yaml_data, dict): raw_yaml_data = None
            except Exception as e: print(f"Error [{self.NODE_NAME}]: Loading YAML {yaml_path}: {e}")

        case_sensitive = kwargs.get("case_sensitive_matching", False)
        if raw_yaml_data:
            cache = {}
            for cat_name in list(raw_yaml_data.keys()):
                 if str(cat_name).strip() not in [INCLUDE_DIRECTIVE, TAGS_KEY]:
                    tags_set = resolve_category_tags(cat_name, raw_yaml_data, cache, self.NODE_NAME)
                    key = str(cat_name).strip() if case_sensitive else str(cat_name).strip().lower()
                    resolved_category_tags[key] = {t if case_sensitive else t.lower() for t in tags_set}

        # --- 2. Parse Targets ---
        targets_info = []
        original_targets = [t.strip() for t in analyze_targets.split(kwargs.get("target_delimiter", ",")) if t.strip()]
        match_spaces = kwargs.get("match_underscores_spaces", True)

        for target in original_targets:
            norm_target = target if case_sensitive else target.lower()
            tags_to_match = resolved_category_tags.get(norm_target, set())
            if not tags_to_match: # It's a literal tag, not a category
                tags_to_match.add(norm_target)
                if match_spaces:
                    tags_to_match.add(norm_target.replace('_', ' '))
                    tags_to_match.add(norm_target.replace(' ', '_'))
            targets_info.append((target, tags_to_match))

        # --- 3. Parse and Count Prompt ---
        counts = defaultdict(int)
        details = defaultdict(list)
        matched_input_tags = set()
        all_input_tags = set()
        handle_weights = kwargs.get("handle_weights", True)

        for raw_tag in prompt.split(kwargs.get("input_delimiter", ",")):
            original_tag = raw_tag.strip()
            if not original_tag: continue
            all_input_tags.add(original_tag)
            _, base = parse_tag(original_tag, handle_weights)
            norm_base = base if case_sensitive else base.lower()
            
            variants = {norm_base}
            if match_spaces: variants.update({norm_base.replace('_', ' '), norm_base.replace(' ', '_')})
            
            for t_original, t_match_set in targets_info:
                if not variants.isdisjoint(t_match_set):
                    counts[t_original] += 1
                    details[t_original].append(original_tag)
                    matched_input_tags.add(original_tag)
        
        # --- 4. Format Outputs ---
        output_delimiter = kwargs.get("output_delimiter", ", ")
        summary = output_delimiter.join([f"{t}: {counts[t]}" for t in original_targets])
        total_count = sum(counts.values())
        
        details_str = ""
        if kwargs.get("generate_detailed_output", False):
            details_str = "\n".join([f"{t}: {counts[t]} [{output_delimiter.join(details[t])}]" for t in original_targets])

        unmatched_str = ""
        if kwargs.get("generate_unmatched_output", False):
            unmatched_str = output_delimiter.join(list(all_input_tags - matched_input_tags))

        return (summary, total_count, details_str, unmatched_str)