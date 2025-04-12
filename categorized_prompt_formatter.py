# /ComfyUI-Prompt-Formatter/categorized_prompt_formatter.py

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
NODE_NAME = "Categorized Prompt Formatter"
NODE_REPO = "ComfyUI-Prompt-Formatter" 

# --- Helper Functions ---

def get_node_directory():
    """Gets the directory path of the current node."""
    # This assumes the script is directly inside the node's folder in custom_nodes
    return Path(__file__).parent

def find_yaml_file(filename):
    """Finds the YAML file, checking relative to node, inputs, and absolute."""
    if not filename:
        return None

    # 1. Check if it's an absolute path
    if Path(filename).is_absolute():
        if Path(filename).is_file():
            return Path(filename)
        else:
            print(f"Warning: Absolute path specified but not found: {filename}")
            return None 

    # 2. Check relative to the custom node's directory
    node_dir = get_node_directory()
    relative_to_node = node_dir / filename
    if relative_to_node.is_file():
        return relative_to_node

    # 3. Check relative to ComfyUI's input directory (common practice)
    #    Need to find the base ComfyUI directory first.
    #    This is a bit heuristic, go up until we find 'ComfyUI'.
    #    This might fail in unusual setups.
    try:
        current_dir = Path.cwd() # Usually ComfyUI base dir when run normally
        if (current_dir / 'input').exists():
             input_dir_path = current_dir / 'input' / filename
             if input_dir_path.is_file():
                 return input_dir_path
        # Fallback search upwards from node dir if cwd isn't reliable
        search_dir = node_dir
        for _ in range(5):
             if (search_dir / 'input').exists():
                 input_dir_path = search_dir / 'input' / filename
                 if input_dir_path.is_file():
                     return input_dir_path
             if (search_dir / 'ComfyUI').exists() or (search_dir / 'main.py').exists(): # Found potential base
                 if (search_dir / 'input').exists():
                     input_dir_path = search_dir / 'input' / filename
                     if input_dir_path.is_file():
                         return input_dir_path
                 break 
             parent = search_dir.parent
             if parent == search_dir: break 
             search_dir = parent

    except Exception as e:
        print(f"Warning: Error searching for ComfyUI input directory: {e}")


    print(f"Warning: YAML file '{filename}' not found as absolute, relative to node, or in input dir.")
    return None


def parse_tag(tag, handle_weights=True):
    """
    Parses a tag to extract the base tag and preserve the original form.
    Handles common weighting and emphasis syntax like (tag:1.2), [tag], {tag}.
    Returns (original_tag, base_tag).
    """
    original_tag = tag.strip()
    base_tag = original_tag

    if handle_weights:
        # More robust regex to handle variations and potential nesting (simple cases)
        # Pattern for (tag:weight) or (tag)
        match = re.match(r"^\s*\(\s*(.*?)\s*(?::\s*[\d.]+\s*)?\)\s*$", original_tag)
        if match:
            base_tag = match.group(1).strip()
            # Handle nested cases like ((tag)) - recursively call? Or just strip outer? Let's strip outer.
            nested_match = re.match(r"^\s*\(\s*(.*?)\s*\)\s*$", base_tag)
            if nested_match:
                 base_tag = nested_match.group(1).strip()
            return original_tag, base_tag

        # Pattern for [tag]
        match = re.match(r"^\s*\[\s*(.*?)\s*\]\s*$", original_tag)
        if match:
            base_tag = match.group(1).strip()
            # Handle nested [[tag]]
            nested_match = re.match(r"^\s*\[\s*(.*?)\s*\]\s*$", base_tag)
            if nested_match:
                 base_tag = nested_match.group(1).strip()
            return original_tag, base_tag

        # Pattern for {tag}
        match = re.match(r"^\s*\{\s*(.*?)\s*\}\s*$", original_tag)
        if match:
            base_tag = match.group(1).strip()
             # Handle nested {{tag}}
            nested_match = re.match(r"^\s*\{\s*(.*?)\s*\}\s*$", base_tag)
            if nested_match:
                 base_tag = nested_match.group(1).strip()
            return original_tag, base_tag

    # If no specific weight/emphasis pattern matched, return the stripped original
    return original_tag, base_tag.strip()


def clean_output_string(text, delimiter=", "):
    """Cleans up the final output string."""
    if not text:
        return ""
    # Remove leading/trailing whitespace and delimiters
    text = text.strip().strip(delimiter.strip()).strip()
    # Replace multiple delimiters (and surrounding whitespace) with a single one
    delimiter_pattern = r'\s*' + re.escape(delimiter.strip()) + r'\s*'
    text = re.sub(f'({delimiter_pattern})+', delimiter, text)
    return text

# --- The Node Class ---

class CategorizedPromptFormatter:
    """
    A ComfyUI node to categorize tags from an input prompt based on a YAML file
    and format them into a new prompt string using a template.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "category_definition_file": ("STRING", {"default": "prompt_categories.yaml"}),
                "output_template": ("STRING", {"multiline": True, "default": "<|quality|>, <|character_num|>, <|person_details|>, <|clothing|>, <|setting|>"}),
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

    def format_prompt(self, prompt, category_definition_file, output_template,
                      input_delimiter=",", output_delimiter=", ", strip_whitespace=True,
                      case_sensitive_matching=False, match_underscores_spaces=True, handle_weights=True,
                      disable_duplicates=False, unmatched_tag_handling="discard"):

        # --- 1. Load Category Definitions ---
        tag_to_categories_map = defaultdict(list)
        yaml_path = find_yaml_file(category_definition_file)

        if yaml_path and yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                if yaml_data:
                    for category, tags in yaml_data.items():
                        if isinstance(tags, list):
                            for tag in tags:
                                processed_tag = str(tag).strip()
                                if not case_sensitive_matching:
                                    processed_tag = processed_tag.lower()
                                if processed_tag:
                                    tag_to_categories_map[processed_tag].append(str(category).strip())
            except FileNotFoundError:
                print(f"Error: YAML file not found at resolved path: {yaml_path}")
                return ("", prompt) 
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file {yaml_path}: {e}")
                return ("", prompt)
            except Exception as e:
                 print(f"Error loading YAML file {yaml_path}: {e}")
                 return ("", prompt)
        else:
            print(f"Warning: Category definition file '{category_definition_file}' not found. Proceeding without categorization.")

        # --- 2. Parse Input Prompt & Categorize ---
        categorized_tags = defaultdict(list)
        all_input_tags_original = set()
        processed_input_tags = [] 

        if prompt:
            raw_tags = prompt.split(input_delimiter)
            for raw_tag in raw_tags:
                tag_original = raw_tag.strip() if strip_whitespace else raw_tag
                if not tag_original: continue

                all_input_tags_original.add(tag_original)
                original_parsed, base_parsed = parse_tag(tag_original, handle_weights)

                # Prepare the tag used for dictionary lookups (case normalization)
                lookup_key_base = base_parsed if case_sensitive_matching else base_parsed.lower()
                processed_input_tags.append((original_parsed, lookup_key_base)) 

        matched_original_tags = set()
        for original_tag, lookup_key_base in processed_input_tags:
            found_categories = None

            if match_underscores_spaces:
                # Generate variants for lookup
                variants_to_check = {
                    lookup_key_base,
                    lookup_key_base.replace('_', ' '),
                    lookup_key_base.replace(' ', '_')
                }
                # Check each variant against the map
                for variant in variants_to_check:
                    categories = tag_to_categories_map.get(variant)
                    if categories:
                        found_categories = categories
                        break #
            else:
                # Direct lookup if matching is disabled
                found_categories = tag_to_categories_map.get(lookup_key_base)

            # If categories were found 
            if found_categories:
                for category in found_categories:
                    categorized_tags[category].append(original_tag)
                matched_original_tags.add(original_tag) 

        # --- 3. Process Template ---
        formatted_output_string = "" # Will be built piece by piece
        placeholders = re.findall(r"<\|(.*?)\|>|", output_template)
        placeholders = [p for p in placeholders if p]

        # Track tags added to the output string to prevent duplicates if requested
        already_added_tags = set()
        # Track tags considered "used" by the template for rejection logic
        used_in_template_tags = set()

        result_parts = []
        last_end = 0
        for match in re.finditer(r"<\|(.*?)\|>|", output_template):
            placeholder_content = match.group(1)
            start, end = match.span()

            # Append the literal text segment before the placeholder
            result_parts.append(output_template[last_end:start])

            if placeholder_content:
                category_name = placeholder_content.strip()
                tags_for_category = categorized_tags.get(category_name, [])

                if tags_for_category:
                    # Mark all tags associated with this placeholder as 'used' by the template
                    # This happens *before* deduplication, as the template *did* reference them.
                    used_in_template_tags.update(tags_for_category)

                    tags_to_join = []
                    if disable_duplicates:
                        # Filter out tags already added
                        for tag in tags_for_category:
                            if tag not in already_added_tags:
                                tags_to_join.append(tag)
                                already_added_tags.add(tag) # Mark as added
                    else:
                        # Include all tags if duplicates are allowed
                        tags_to_join = tags_for_category

                    if tags_to_join:
                         joined_tags = output_delimiter.join(tags_to_join)
                         result_parts.append(joined_tags)

            last_end = end

        # Append any remaining literal text after the last placeholder
        result_parts.append(output_template[last_end:])

        formatted_output_string = "".join(result_parts)


        # --- 4. Handle Unmatched Tags ---
        rejected_tags_list = []
        if unmatched_tag_handling != "discard":
            # Find tags that were in the input but NOT marked as 'used' by the template placeholders
            rejected_tags_list = list(all_input_tags_original - used_in_template_tags)

        rejected_output_string = ""
        if rejected_tags_list:
            if unmatched_tag_handling == "append_end":
                # Ensure there's a delimiter if the main string isn't empty and doesn't end with one
                if formatted_output_string and not formatted_output_string.endswith(output_delimiter):
                     formatted_output_string += output_delimiter
                elif not formatted_output_string: # If main string is empty, don't start with delimiter
                     pass
                else: # Main string ends with delimiter, add space if needed
                     if not formatted_output_string.endswith(" "):
                         formatted_output_string += " "


                formatted_output_string += output_delimiter.join(rejected_tags_list)
            elif unmatched_tag_handling == "output_separately":
                rejected_output_string = output_delimiter.join(rejected_tags_list)

        # --- 5. Cleanup and Return ---
        final_formatted = clean_output_string(formatted_output_string, output_delimiter)
        final_rejected = clean_output_string(rejected_output_string, output_delimiter)


        return (final_formatted, final_rejected)