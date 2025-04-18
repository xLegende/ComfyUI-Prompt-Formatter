# /ComfyUI-Prompt-Formatter/categorized_prompt_analyzer.py

import yaml
import re
import os
import sys
from collections import defaultdict
from pathlib import Path


# --- Dependency Check ---
try:
    import yaml
except ImportError:
    print("PyYAML is not installed. Please run install.py or install it manually.", file=sys.stderr)

# --- Constants ---
NODE_NAME_ANALYZER = "Categorized Prompt Analyzer" # Specific name
INCLUDE_DIRECTIVE = "$include"
TAGS_KEY = "tags"


def get_node_directory_analyzer():
    return Path(__file__).parent

def find_yaml_file_analyzer(filename):
    if not filename: return None
    if Path(filename).is_absolute():
        if Path(filename).is_file(): return Path(filename)
        else: print(f"Warning [Analyzer]: Absolute path specified but not found: {filename}"); return None
    node_dir = get_node_directory_analyzer()
    relative_to_node = node_dir / filename
    if relative_to_node.is_file(): return relative_to_node
    try:
        current_dir = Path.cwd()
        input_dir = current_dir / 'input'
        if input_dir.exists():
             input_dir_path = input_dir / filename
             if input_dir_path.is_file(): return input_dir_path
        search_dir = node_dir
        for _ in range(5):
             input_dir = search_dir / 'input'
             if input_dir.exists():
                 input_dir_path = input_dir / filename
                 if input_dir_path.is_file(): return input_dir_path
             if (search_dir / 'ComfyUI').exists() or (search_dir / 'main.py').exists():
                 input_dir = search_dir / 'input'
                 if input_dir.exists():
                     input_dir_path = input_dir / filename
                     if input_dir_path.is_file(): return input_dir_path
                 break
             parent = search_dir.parent
             if parent == search_dir: break
             search_dir = parent
    except Exception as e: print(f"Warning [Analyzer]: Error searching for ComfyUI input directory: {e}")
    print(f"Warning [Analyzer]: YAML file '{filename}' not found as absolute, relative to node, or in input dir.")
    return None

def resolve_category_tags_analyzer(category_name, yaml_data, resolved_cache, recursion_guard=None):
    category_name = str(category_name).strip()
    if recursion_guard is None: recursion_guard = set()
    if len(recursion_guard) > 20: return set() # Depth limit
    if category_name in recursion_guard: print(f"Warning [Analyzer]: Circular dependency: '{category_name}'."); return set()
    if category_name in resolved_cache: return resolved_cache[category_name]
    if category_name not in yaml_data: return set()
    recursion_guard.add(category_name)
    category_data = yaml_data[category_name]
    final_tags = set()
    if isinstance(category_data, list):
        for item in category_data:
            item_str = str(item).strip();
            if not item_str: continue
            is_full_include = item_str.startswith('$') and len(item_str) > 1 and ' ' not in item_str and item_str[1:].replace('_', '').isalnum()
            if is_full_include:
                included_category = item_str[1:]
                final_tags.update(resolve_category_tags_analyzer(included_category, yaml_data, resolved_cache, recursion_guard.copy()))
            else:
                match = re.search(r'\$(\w+)', item_str)
                if match:
                    ref_category_name = match.group(1); placeholder = match.group(0)
                    resolved_ref_tags = resolve_category_tags_analyzer(ref_category_name, yaml_data, resolved_cache, recursion_guard.copy())
                    if not resolved_ref_tags: pass # Optionally add literal item_str here
                    else:
                        for resolved_tag in resolved_ref_tags:
                            new_tag = item_str.replace(placeholder, str(resolved_tag).strip(), 1)
                            final_tags.add(new_tag)
                else: final_tags.add(item_str)
    elif isinstance(category_data, dict):
        if INCLUDE_DIRECTIVE in category_data:
            includes = category_data[INCLUDE_DIRECTIVE]; include_list = []
            if isinstance(includes, list): include_list = [str(inc).strip() for inc in includes if str(inc).strip()]
            elif isinstance(includes, str): include_list = [includes.strip()] if includes.strip() else []
            for included_category in include_list:
                final_tags.update(resolve_category_tags_analyzer(included_category, yaml_data, resolved_cache, recursion_guard.copy()))
        if TAGS_KEY in category_data and isinstance(category_data[TAGS_KEY], list):
             final_tags.update(str(tag).strip() for tag in category_data[TAGS_KEY] if str(tag).strip())
    resolved_cache[category_name] = final_tags
    return final_tags

def parse_tag_analyzer(tag, handle_weights=True):
    original_tag = str(tag).strip(); base_tag = original_tag
    if not handle_weights: return original_tag, base_tag
    patterns = [ r"^\s*\(\s*(.*?)\s*(?::\s*[\d.]+\s*)?\)\s*$", r"^\s*\[\s*(.*?)\s*\]\s*$", r"^\s*\{\s*(.*?)\s*\}\s*$" ]
    for pattern in patterns:
        match = re.match(pattern, original_tag)
        if match:
            base_tag = match.group(1).strip()
            nested_match = re.match(r"^\s*[\(\[\{](.*?)[\)\]\}]\s*$", base_tag)
            if nested_match: base_tag = nested_match.group(1).strip()
            return original_tag, base_tag
    return original_tag, base_tag.strip()

def clean_output_string_analyzer(text, delimiter=", "):
    if not text: return ""
    text = text.strip().strip(delimiter.strip()).strip()
    delimiter_pattern = r'\s*' + re.escape(delimiter.strip()) + r'\s*'
    text = re.sub(f'({delimiter_pattern})+', delimiter, text)
    if text.startswith(delimiter): text = text[len(delimiter):].lstrip()
    if text.endswith(delimiter.rstrip()): text = text[:-len(delimiter.rstrip())].rstrip()
    return text

# --- The Analyzer Node Class ---

class CategorizedPromptAnalyzer:
    """
    A ComfyUI node to analyze tag occurrences in a prompt based on specific
    tags or categories defined in a YAML file.
    """
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
                 "output_delimiter": ("STRING", {"default": ", "}), # For list outputs
                 "strip_whitespace": ("BOOLEAN", {"default": True}),
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

    def analyze_prompt(self, prompt, analyze_targets, category_definition_file,
                       input_delimiter=",", target_delimiter=",", output_delimiter=", ",
                       strip_whitespace=True, case_sensitive_matching=False,
                       handle_weights=True, match_underscores_spaces=True,
                       generate_detailed_output=False, generate_unmatched_output=False):

        # --- 1. Load & Resolve YAML ---
        resolved_category_tags = {} 
        raw_yaml_data = None
        yaml_path = find_yaml_file_analyzer(category_definition_file)

        if yaml_path and yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f: raw_yaml_data = yaml.safe_load(f)
                if not isinstance(raw_yaml_data, dict): raw_yaml_data = None
            except Exception as e: print(f"Error [Analyzer]: Loading YAML {yaml_path}: {e}")

        if raw_yaml_data:
            resolved_tags_cache = {}
            all_category_names = list(raw_yaml_data.keys())
            for category_name in all_category_names:
                 if str(category_name).strip() != INCLUDE_DIRECTIVE and str(category_name).strip() != TAGS_KEY:
                    # Resolve tags using the helper
                    resolved_tags_set = resolve_category_tags_analyzer(category_name, raw_yaml_data, resolved_tags_cache)
                    # Store resolved tags, applying case sensitivity NOW for matching later
                    normalized_category_name = str(category_name).strip() if case_sensitive_matching else str(category_name).strip().lower()
                    normalized_tags = set()
                    for tag in resolved_tags_set:
                         # Also normalize tags based on case sensitivity for matching
                         normalized_tags.add(tag if case_sensitive_matching else tag.lower())
                    resolved_category_tags[normalized_category_name] = normalized_tags
        # else: Warning already printed by find_yaml_file

        # --- 2. Parse & Process Targets ---
        targets_info = [] # List of tuples: (original_target, normalized_target, is_category, {normalized_tags_to_match})
        original_targets_list = [t.strip() for t in analyze_targets.split(target_delimiter) if t.strip()]

        for original_target in original_targets_list:
            normalized_target = original_target if case_sensitive_matching else original_target.lower()
            is_category = False
            normalized_tags_to_match = set()

            if normalized_target in resolved_category_tags:
                # It's a category target
                is_category = True
                normalized_tags_to_match = resolved_category_tags[normalized_target]
            else:
                # It's a literal target
                is_category = False
                # Generate variants for the literal target itself for matching
                literal_variants = {normalized_target}
                if match_underscores_spaces:
                    literal_variants.add(normalized_target.replace('_', ' '))
                    literal_variants.add(normalized_target.replace(' ', '_'))
                normalized_tags_to_match = literal_variants

            targets_info.append((original_target, normalized_target, is_category, normalized_tags_to_match))

        # --- 3. Parse Input Prompt ---
        input_tags_processed = [] # List of tuples: (original_tag, base_tag_normalized, {variants})
        all_input_tags_original = set()

        if prompt:
            raw_tags = prompt.split(input_delimiter)
            for raw_tag in raw_tags:
                tag_original = raw_tag.strip() if strip_whitespace else raw_tag
                if not tag_original: continue
                all_input_tags_original.add(tag_original)

                # Parse tag, get base form
                _, base_parsed = parse_tag_analyzer(tag_original, handle_weights)
                base_tag_normalized = base_parsed if case_sensitive_matching else base_parsed.lower()

                # Generate variants for matching
                variants = {base_tag_normalized}
                if match_underscores_spaces:
                    variants.add(base_tag_normalized.replace('_', ' '))
                    variants.add(base_tag_normalized.replace(' ', '_'))

                input_tags_processed.append((tag_original, base_tag_normalized, variants))


        # --- 4. Perform Counting ---
        counts = defaultdict(int) # original_target -> count
        details_data = defaultdict(list) # original_target -> list_of_matched_input_tags
        matched_input_originals_set = set()

        for tag_original, _, input_variants in input_tags_processed:
            tag_matched_at_least_once = False
            for original_target, normalized_target, is_category, target_match_set in targets_info:
                # Check if any input variant matches any tag in the target's match set
                found_match = False
                for variant in input_variants:
                    if variant in target_match_set:
                         found_match = True
                         break # Found a match for this input tag against this target

                if found_match:
                    counts[original_target] += 1
                    if generate_detailed_output:
                        details_data[original_target].append(tag_original)
                    matched_input_originals_set.add(tag_original)
                    tag_matched_at_least_once = True
            # Note: If an input tag matches multiple targets (e.g., literal and category),
            # it will correctly increment the count for *each* target it matches.


        # --- 5. Calculate Unmatched ---
        unmatched_tags_list = []
        if generate_unmatched_output:
            unmatched_tags_list = list(all_input_tags_original - matched_input_originals_set)


        # --- 6. Format Outputs ---
        summary_parts = []
        for original_target in original_targets_list: # Keep original order
            summary_parts.append(f"{original_target}: {counts[original_target]}")
        analysis_summary = output_delimiter.join(summary_parts)

        total_matched_count = sum(counts.values())

        details_str = ""
        if generate_detailed_output:
             detail_parts = []
             for original_target in original_targets_list:
                 matched_list_str = output_delimiter.join(details_data[original_target])
                 detail_parts.append(f"{original_target}: {counts[original_target]} [{matched_list_str}]")
             details_str = "\n".join(detail_parts) # Use newline for readability

        unmatched_tags_str = ""
        if generate_unmatched_output:
            unmatched_tags_str = output_delimiter.join(unmatched_tags_list)


        return (analysis_summary, total_matched_count, details_str, unmatched_tags_str)