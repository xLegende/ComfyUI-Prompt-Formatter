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
    # Consider adding instructions or a more robust check here
    # For now, we assume it's installed if this point is reached without error

# --- Constants ---
NODE_NAME = "Categorized Prompt Formatter"
NODE_REPO = "ComfyUI-Prompt-Formatter" # For finding relative paths
INCLUDE_DIRECTIVE = "$include" # Define the directive key
TAGS_KEY = "tags" # Optional key for direct tags within an include dict

# --- Helper Functions ---

def get_node_directory():
    """Gets the directory path of the current node."""
    return Path(__file__).parent

def find_yaml_file(filename):
    """Finds the YAML file, checking relative to node, inputs, and absolute."""
    if not filename:
        return None
    if Path(filename).is_absolute():
        if Path(filename).is_file(): return Path(filename)
        else: print(f"Warning: Absolute path specified but not found: {filename}"); return None
    node_dir = get_node_directory()
    relative_to_node = node_dir / filename
    if relative_to_node.is_file(): return relative_to_node
    try:
        current_dir = Path.cwd()
        if (current_dir / 'input').exists():
             input_dir_path = current_dir / 'input' / filename
             if input_dir_path.is_file(): return input_dir_path
        search_dir = node_dir
        for _ in range(5):
             if (search_dir / 'input').exists():
                 input_dir_path = search_dir / 'input' / filename
                 if input_dir_path.is_file(): return input_dir_path
             if (search_dir / 'ComfyUI').exists() or (search_dir / 'main.py').exists():
                 if (search_dir / 'input').exists():
                     input_dir_path = search_dir / 'input' / filename
                     if input_dir_path.is_file(): return input_dir_path
                 break
             parent = search_dir.parent
             if parent == search_dir: break
             search_dir = parent
    except Exception as e: print(f"Warning: Error searching for ComfyUI input directory: {e}")
    print(f"Warning: YAML file '{filename}' not found as absolute, relative to node, or in input dir.")
    return None

def parse_tag(tag, handle_weights=True):
    """ Parses a tag to extract the base tag and preserve the original form. """
    original_tag = str(tag).strip() # Ensure string type
    base_tag = original_tag
    if not handle_weights: return original_tag, base_tag
    patterns = [
        r"^\s*\(\s*(.*?)\s*(?::\s*[\d.]+\s*)?\)\s*$", # (tag:weight) or (tag)
        r"^\s*\[\s*(.*?)\s*\]\s*$", # [tag]
        r"^\s*\{\s*(.*?)\s*\}\s*$"  # {tag}
    ]
    for pattern in patterns:
        match = re.match(pattern, original_tag)
        if match:
            base_tag = match.group(1).strip()
            # Handle simple nesting like ((tag))
            nested_match = re.match(r"^\s*[\(\[\{](.*?)[\)\]\}]\s*$", base_tag)
            if nested_match:
                 base_tag = nested_match.group(1).strip()
            return original_tag, base_tag
    return original_tag, base_tag.strip() # Return stripped original if no pattern matched


def clean_output_string(text, delimiter=", "):
    """Cleans up the final output string."""
    if not text: return ""
    text = text.strip().strip(delimiter.strip()).strip()
    delimiter_pattern = r'\s*' + re.escape(delimiter.strip()) + r'\s*'
    text = re.sub(f'({delimiter_pattern})+', delimiter, text)
    # Remove delimiter if it's the very start or end after replacements
    if text.startswith(delimiter): text = text[len(delimiter):].lstrip()
    if text.endswith(delimiter.rstrip()): text = text[:-len(delimiter.rstrip())].rstrip()
    return text

# --- YAML Include Resolution Helper ---
def resolve_category_tags(category_name, yaml_data, resolved_cache, recursion_guard=None):
    """
    Recursively resolves tags for a category, handling $include directives.
    Returns a set of unique tags (strings) for the category.
    """
    category_name = str(category_name).strip() # Ensure consistent key type
    if recursion_guard is None:
        recursion_guard = set()
    if category_name in recursion_guard:
        print(f"Warning: Circular dependency detected involving category '{category_name}'. Skipping recursive include.")
        return set()
    if category_name in resolved_cache:
        return resolved_cache[category_name]
    if category_name not in yaml_data:
        print(f"Warning: Included category '{category_name}' not found in YAML data.")
        return set()

    recursion_guard.add(category_name) # Mark as visiting

    category_data = yaml_data[category_name]
    final_tags = set()

    if isinstance(category_data, list):
        # Simple list of tags
        final_tags.update(str(tag).strip() for tag in category_data if str(tag).strip())

    elif isinstance(category_data, dict):
        # Dictionary format, check for $include and direct tags
        # Check for $include directive first
        if INCLUDE_DIRECTIVE in category_data:
            includes = category_data[INCLUDE_DIRECTIVE]
            include_list = []
            if isinstance(includes, list):
                include_list = [str(inc).strip() for inc in includes if str(inc).strip()]
            elif isinstance(includes, str):
                 include_list = [includes.strip()] if includes.strip() else []

            for included_category in include_list:
                # Pass a copy of the guard to prevent siblings affecting each other's cycle detection
                final_tags.update(resolve_category_tags(included_category, yaml_data, resolved_cache, recursion_guard.copy()))

        # Check for direct tags (e.g., under 'tags:' key or others if structure allows)
        if TAGS_KEY in category_data and isinstance(category_data[TAGS_KEY], list):
             final_tags.update(str(tag).strip() for tag in category_data[TAGS_KEY] if str(tag).strip())
        # Optional: Handle case where dict has no $include or 'tags', maybe treat other keys?
        # else:
        #     print(f"Warning: Dict category '{category_name}' lacks '{INCLUDE_DIRECTIVE}' or '{TAGS_KEY}'. Tags ignored.")
        #     pass

    else:
        # Handle cases where a category definition is neither list nor dict (e.g., just a string)
        print(f"Warning: Category '{category_name}' definition is not a list or dictionary. Ignoring.")


    resolved_cache[category_name] = final_tags
    # No need to remove from recursion_guard here as we pass copies down

    return final_tags


# --- The Node Class ---

class CategorizedPromptFormatter:
    """
    A ComfyUI node to categorize tags from an input prompt based on a YAML file
    (supporting $include directives) and format them using a template.
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
                      case_sensitive_matching=False, handle_weights=True,
                      match_underscores_spaces=True, disable_duplicates=False,
                      unmatched_tag_handling="discard"):

        # --- 1. Load & Resolve Category Definitions ---
        tag_to_categories_map = defaultdict(list)
        yaml_path = find_yaml_file(category_definition_file)
        raw_yaml_data = None

        if yaml_path and yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    raw_yaml_data = yaml.safe_load(f)
                if not isinstance(raw_yaml_data, dict):
                     print(f"Warning: YAML file '{yaml_path}' does not contain a dictionary at the top level. Cannot process categories.")
                     raw_yaml_data = None # Treat as empty
            except FileNotFoundError:
                print(f"Error: YAML file not found at resolved path: {yaml_path}")
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file {yaml_path}: {e}")
            except Exception as e:
                 print(f"Error loading YAML file {yaml_path}: {e}")

        if raw_yaml_data:
            resolved_tags_cache = {}
            all_category_names = list(raw_yaml_data.keys())

            # Resolve all categories first using the helper function
            for category_name in all_category_names:
                 # Don't try to resolve the directive key itself if used at top level
                 if str(category_name).strip() != INCLUDE_DIRECTIVE and str(category_name).strip() != TAGS_KEY:
                    resolve_category_tags(category_name, raw_yaml_data, resolved_tags_cache)

            # Build the final tag -> [categories] map from the resolved cache
            for category_name, resolved_tags_set in resolved_tags_cache.items():
                for tag in resolved_tags_set: # Tags are already stripped strings here
                    processed_tag_key = tag if case_sensitive_matching else tag.lower()
                    if processed_tag_key: # Ensure not empty after potential lowercasing
                        # A tag belongs to the category under which it was resolved
                        # (This includes parent categories that included it)
                        tag_to_categories_map[processed_tag_key].append(category_name)

            # Deduplicate the list of categories for each tag 
            for tag_key in tag_to_categories_map:
                tag_to_categories_map[tag_key] = list(set(tag_to_categories_map[tag_key]))

        else:
            print(f"Warning: Category definition file '{category_definition_file}' not found or empty/invalid. Proceeding without categorization.")
            # tag_to_categories_map remains empty

        # --- 2. Parse Input Prompt & Categorize ---
        categorized_tags = defaultdict(list)
        all_input_tags_original = set()
        processed_input_tags = [] # Store (original_tag, base_tag for matching)

        if prompt:
            raw_tags = prompt.split(input_delimiter)
            for raw_tag in raw_tags:
                tag_original = raw_tag.strip() if strip_whitespace else raw_tag
                if not tag_original: continue

                all_input_tags_original.add(tag_original)
                original_parsed, base_parsed = parse_tag(tag_original, handle_weights)

                # Prepare the key used for dictionary lookups
                lookup_key_base = base_parsed if case_sensitive_matching else base_parsed.lower()
                processed_input_tags.append((original_parsed, lookup_key_base))

        matched_original_tags = set()
        for original_tag, lookup_key_base in processed_input_tags:
            found_categories = None
            variants_to_check = {lookup_key_base} # Start with the base lookup key

            if match_underscores_spaces:
                # Generate variants only if needed
                underscore_variant = lookup_key_base.replace(' ', '_')
                space_variant = lookup_key_base.replace('_', ' ')
                if underscore_variant != lookup_key_base: variants_to_check.add(underscore_variant)
                if space_variant != lookup_key_base: variants_to_check.add(space_variant)

            # Check each variant against the map
            for variant in variants_to_check:
                categories = tag_to_categories_map.get(variant)
                if categories:
                    found_categories = categories
                    break # Found a match, stop checking variants for this tag

            if found_categories:
                for category in found_categories:
                    # Append the ORIGINAL tag (with weights etc.) to the list for each category it maps to
                    categorized_tags[category].append(original_tag)
                matched_original_tags.add(original_tag) # Mark the ORIGINAL tag as matched

        # --- 3. Process Template ---
        formatted_output_string = ""
        already_added_tags = set()
        used_in_template_tags = set() # Tracks tags referenced by template (before dedup)

        result_parts = []
        last_end = 0
        for match in re.finditer(r"<\|(.*?)\|>|", output_template):
            placeholder_content = match.group(1)
            start, end = match.span()
            result_parts.append(output_template[last_end:start])

            if placeholder_content:
                category_name = placeholder_content.strip()
                # Use the categorized_tags dict built earlier
                tags_for_category = categorized_tags.get(category_name, [])

                if tags_for_category:
                    # Mark all tags associated with this placeholder as 'used' by the template
                    used_in_template_tags.update(tags_for_category)

                    tags_to_join = []
                    if disable_duplicates:
                        for tag in tags_for_category:
                            if tag not in already_added_tags:
                                tags_to_join.append(tag)
                                already_added_tags.add(tag) # Mark as added
                    else:
                        tags_to_join = tags_for_category
                        # already_added_tags.update(tags_to_join) # Optional

                    if tags_to_join:
                         joined_tags = output_delimiter.join(tags_to_join)
                         result_parts.append(joined_tags)

            last_end = end
        result_parts.append(output_template[last_end:])
        formatted_output_string = "".join(result_parts)


        # --- 4. Handle Unmatched Tags ---
        # This section remains the same
        rejected_tags_list = []
        if unmatched_tag_handling != "discard":
            rejected_tags_list = list(all_input_tags_original - used_in_template_tags)

        rejected_output_string = ""
        if rejected_tags_list:
            rejected_output_string = output_delimiter.join(rejected_tags_list)
            if unmatched_tag_handling == "append_end":
                if formatted_output_string and not formatted_output_string.rstrip().endswith(output_delimiter.strip()):
                     # Add delimiter only if needed and formatted string isn't empty
                     formatted_output_string += output_delimiter
                elif not formatted_output_string:
                     pass # Avoid leading delimiter if formatted is empty
                # Append rejected tags
                formatted_output_string += rejected_output_string
                rejected_output_string = "" # Clear rejected as it was appended


        # --- 5. Cleanup and Return ---
        final_formatted = clean_output_string(formatted_output_string, output_delimiter)
        final_rejected = clean_output_string(rejected_output_string, output_delimiter)

        return (final_formatted, final_rejected)
