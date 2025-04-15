# /ComfyUI-Prompt-Formatter/categorized_random_prompt_formatter.py

import yaml
import re
import os
import sys
import random
from collections import defaultdict
from pathlib import Path

# --- Dependency Check ---
try:
    import yaml
except ImportError:
    print("PyYAML is not installed. Please run install.py or install it manually.", file=sys.stderr)

# --- Constants ---
NODE_NAME_RANDOM = "Categorized Random Prompt Formatter" # Specific name for this node
INCLUDE_DIRECTIVE = "$include"
TAGS_KEY = "tags"

# --- Helper Functions (Copied/Adapted from previous node) ---

def get_node_directory_random(): 
    """Gets the directory path of the current node."""
    return Path(__file__).parent

def find_yaml_file_random(filename):
    """Finds the YAML file (adapted naming)."""
    if not filename: return None
    if Path(filename).is_absolute():
        if Path(filename).is_file(): return Path(filename)
        else: print(f"Warning [RandomNode]: Absolute path specified but not found: {filename}"); return None
    node_dir = get_node_directory_random()
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
    except Exception as e: print(f"Warning [RandomNode]: Error searching for ComfyUI input directory: {e}")
    print(f"Warning [RandomNode]: YAML file '{filename}' not found as absolute, relative to node, or in input dir.")
    return None

def resolve_category_tags_random(category_name, yaml_data, resolved_cache, recursion_guard=None):
    """ Recursively resolves tags for a category (adapted naming). """
    category_name = str(category_name).strip()
    if recursion_guard is None: recursion_guard = set()
    if category_name in recursion_guard:
        print(f"Warning [RandomNode]: Circular dependency detected involving category '{category_name}'.")
        return set()
    if category_name in resolved_cache: return resolved_cache[category_name]
    if category_name not in yaml_data:
        print(f"Warning [RandomNode]: Included category '{category_name}' not found.")
        return set()
    recursion_guard.add(category_name)
    category_data = yaml_data[category_name]
    final_tags = set()
    if isinstance(category_data, list):
        final_tags.update(str(tag).strip() for tag in category_data if str(tag).strip())
    elif isinstance(category_data, dict):
        if INCLUDE_DIRECTIVE in category_data:
            includes = category_data[INCLUDE_DIRECTIVE]
            include_list = []
            if isinstance(includes, list): include_list = [str(inc).strip() for inc in includes if str(inc).strip()]
            elif isinstance(includes, str): include_list = [includes.strip()] if includes.strip() else []
            for included_category in include_list:
                final_tags.update(resolve_category_tags_random(included_category, yaml_data, resolved_cache, recursion_guard.copy()))
        if TAGS_KEY in category_data and isinstance(category_data[TAGS_KEY], list):
             final_tags.update(str(tag).strip() for tag in category_data[TAGS_KEY] if str(tag).strip())
    else:
        print(f"Warning [RandomNode]: Category '{category_name}' definition ignored (not list or dict).")
    resolved_cache[category_name] = final_tags
    return final_tags

def clean_output_string_random(text, delimiter=", "):
    """Cleans up the final output string (adapted naming)."""
    if not text: return ""
    text = text.strip().strip(delimiter.strip()).strip()
    delimiter_pattern = r'\s*' + re.escape(delimiter.strip()) + r'\s*'
    text = re.sub(f'({delimiter_pattern})+', delimiter, text)
    if text.startswith(delimiter): text = text[len(delimiter):].lstrip()
    if text.endswith(delimiter.rstrip()): text = text[:-len(delimiter.rstrip())].rstrip()
    return text

# --- The Random Node Class ---

class CategorizedRandomPromptFormatter:
    """
    A ComfyUI node to generate random prompts by selecting tags from categories
    defined in a YAML file, based on a template and a seed.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "category_definition_file": ("STRING", {"default": "prompt_categories.yaml"}),
                "output_template": ("STRING", {
                    "multiline": True,
                    "default": "<|quality:1|>, <|character_num:1|>, <|person_details:3|>, <|clothing:1|>, <|setting:1|>, <|style:1|>"
                }),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}),
            },
            "optional": {
                 "output_delimiter": ("STRING", {"default": ", "}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("random_prompt", "used_seed")
    FUNCTION = "generate_prompt"
    CATEGORY = "text/generation" 

    def generate_prompt(self, category_definition_file, output_template, seed,
                      output_delimiter=", ",
                      ):

        # --- 1. Handle Seed ---
        if seed == -1:
            used_seed = random.randint(0, 0xffffffffffffffff)
        else:
            used_seed = seed
        # Initialize a dedicated random number generator for this execution
        rng = random.Random(used_seed)

        # --- 2. Load & Resolve Category Definitions ---
        resolved_categories = {} # Store category_name -> set_of_tags
        yaml_path = find_yaml_file_random(category_definition_file)
        raw_yaml_data = None

        if yaml_path and yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    raw_yaml_data = yaml.safe_load(f)
                if not isinstance(raw_yaml_data, dict):
                     print(f"Warning [RandomNode]: YAML file '{yaml_path}' is not a dictionary. Cannot process.")
                     raw_yaml_data = None
            except Exception as e:
                 print(f"Error [RandomNode]: Loading YAML file {yaml_path}: {e}")

        if raw_yaml_data:
            resolved_tags_cache = {}
            all_category_names = list(raw_yaml_data.keys())
            for category_name in all_category_names:
                 if str(category_name).strip() != INCLUDE_DIRECTIVE and str(category_name).strip() != TAGS_KEY:
                    # Resolve tags for each category using the helper
                    resolved_categories[str(category_name).strip()] = resolve_category_tags_random(
                        category_name, raw_yaml_data, resolved_tags_cache
                    )
        else:
            print(f"Warning [RandomNode]: Category file '{category_definition_file}' not found or empty. Cannot generate prompt.")
            return ("", used_seed) # Return empty if no categories loaded

        # --- 3. Process Template and Generate Random Tags ---
        # Regex to capture category name (group 1) and optional count (group 2)
        # Only positive counts are meaningful here. Default count is 1.
        placeholder_regex = r"<\|([^:]+?)(?::(\d+))?\|>"

        generated_prompt_string = ""
        result_parts = []
        last_end = 0

        for match in re.finditer(placeholder_regex, output_template):
            category_name = match.group(1).strip()
            count_str = match.group(2) # Optional count N
            start, end = match.span()

            # Append literal text before placeholder
            result_parts.append(output_template[last_end:start])

            # Determine the number of tags to pick (default 1)
            num_to_pick = 1 # Default
            if count_str:
                try:
                    count = int(count_str)
                    if count >= 0: # Allow 0 to explicitly pick none
                       num_to_pick = count
                    else:
                        print(f"Warning [RandomNode]: Negative count '{count_str}' for category '{category_name}' invalid. Defaulting to 1.")
                        num_to_pick = 1 # Default to 1 if negative
                except ValueError:
                    print(f"Warning [RandomNode]: Invalid count format '{count_str}' for category '{category_name}'. Defaulting to 1.")
                    num_to_pick = 1

            tags_to_join = []
            if num_to_pick > 0:
                # Get the set of available tags for this category
                available_tags_set = resolved_categories.get(category_name)

                if available_tags_set and len(available_tags_set) > 0:
                    # Ensure we don't try to sample more tags than available
                    actual_num_to_sample = min(num_to_pick, len(available_tags_set))

                    # Convert set to list for sampling, then sample using the seeded RNG
                    tags_to_join = rng.sample(list(available_tags_set), actual_num_to_sample)
                elif not available_tags_set:
                     print(f"Warning [RandomNode]: Category '{category_name}' requested in template but not found in YAML.")


            # Join the randomly selected tags
            if tags_to_join:
                joined_tags = output_delimiter.join(tags_to_join)
                result_parts.append(joined_tags)
            # If num_to_pick was 0 or category empty/not found, nothing is appended for this placeholder

            last_end = end

        # Append any remaining literal text
        result_parts.append(output_template[last_end:])
        generated_prompt_string = "".join(result_parts)

        # --- 4. Cleanup and Return ---
        final_prompt = clean_output_string_random(generated_prompt_string, output_delimiter)

        return (final_prompt, used_seed)