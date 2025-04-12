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
    # Optionally, try to run install.py automatically if possible,
    # but this can be complex depending on environment. Best to rely on user action.
    # raise ImportError("PyYAML is required but not installed. Run install.py.") from None

# --- Constants ---
NODE_NAME = "Categorized Prompt Formatter"
NODE_REPO = "ComfyUI-Prompt-Formatter" # For finding relative paths

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
            return None # Explicit absolute path not found

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
        for _ in range(5): # Limit search depth
             if (search_dir / 'input').exists():
                 input_dir_path = search_dir / 'input' / filename
                 if input_dir_path.is_file():
                     return input_dir_path
             if (search_dir / 'ComfyUI').exists() or (search_dir / 'main.py').exists(): # Found potential base
                 if (search_dir / 'input').exists():
                     input_dir_path = search_dir / 'input' / filename
                     if input_dir_path.is_file():
                         return input_dir_path
                 break # Stop searching up
             parent = search_dir.parent
             if parent == search_dir: break # Reached root
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
                 "unmatched_tag_handling": (["discard", "append_end", "output_separately"], {"default": "discard"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("formatted_prompt", "rejected_prompt")
    FUNCTION = "format_prompt"
    CATEGORY = "text/filtering" # Or your preferred category

    def format_prompt(self, prompt, category_definition_file, output_template,
                      input_delimiter=",", output_delimiter=", ", strip_whitespace=True,
                      case_sensitive_matching=False, handle_weights=True,
                      unmatched_tag_handling="discard"):

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
                                processed_tag = str(tag).strip() # Ensure string and strip
                                if not case_sensitive_matching:
                                    processed_tag = processed_tag.lower()
                                if processed_tag: # Avoid empty tags
                                    tag_to_categories_map[processed_tag].append(str(category).strip())
            except FileNotFoundError:
                print(f"Error: YAML file not found at resolved path: {yaml_path}")
                # Return empty prompts or raise an error? Let's return empty.
                return ("", prompt) # Return original prompt as rejected if file fails
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file {yaml_path}: {e}")
                return ("", prompt)
            except Exception as e:
                 print(f"Error loading YAML file {yaml_path}: {e}")
                 return ("", prompt)
        else:
            print(f"Warning: Category definition file '{category_definition_file}' not found. Proceeding without categorization.")
            # If no categories, all tags will be unmatched

        # --- 2. Parse Input Prompt & Categorize ---
        categorized_tags = defaultdict(list)
        all_input_tags_original = set()
        processed_input_tags = [] # Store (original_tag, base_tag)

        if prompt:
            raw_tags = prompt.split(input_delimiter)
            for raw_tag in raw_tags:
                tag_original = raw_tag.strip() if strip_whitespace else raw_tag
                if not tag_original: continue # Skip empty tags resulting from split

                all_input_tags_original.add(tag_original)
                original_parsed, base_parsed = parse_tag(tag_original, handle_weights)

                lookup_tag = base_parsed if not case_sensitive_matching else base_parsed.lower()
                processed_input_tags.append((original_parsed, lookup_tag))


        matched_original_tags = set()
        for original_tag, lookup_tag in processed_input_tags:
            categories = tag_to_categories_map.get(lookup_tag)
            if categories:
                for category in categories:
                    categorized_tags[category].append(original_tag)
                matched_original_tags.add(original_tag) # Mark as matched if found in *any* category

        # --- 3. Process Template ---
        formatted_output_string = output_template
        placeholders = re.findall(r"<\|(.*?)\|>|", output_template) # Find placeholders like <|name|>
        placeholders = [p for p in placeholders if p] # Filter out empty strings from regex artifact

        used_in_template_tags = set()

        # Use a temporary string builder approach to avoid issues with replacing overlapping parts
        result_parts = []
        last_end = 0
        for match in re.finditer(r"<\|(.*?)\|>|", output_template):
            placeholder_content = match.group(1)
            start, end = match.span()

            # Append the text segment before the placeholder
            result_parts.append(output_template[last_end:start])

            if placeholder_content:
                category_name = placeholder_content.strip()
                tags_for_category = categorized_tags.get(category_name, [])
                if tags_for_category:
                    joined_tags = output_delimiter.join(tags_for_category)
                    result_parts.append(joined_tags)
                    used_in_template_tags.update(tags_for_category) # Keep track of used tags
                # If category not found or has no tags, effectively replaces with empty string
            else:
                 # Append the matched placeholder itself if it wasn't valid (shouldn't happen with this regex but safer)
                 result_parts.append(match.group(0))


            last_end = end

        # Append any remaining text after the last placeholder
        result_parts.append(output_template[last_end:])

        formatted_output_string = "".join(result_parts)


        # --- 4. Handle Unmatched Tags ---
        rejected_tags_list = []
        if unmatched_tag_handling != "discard":
            # Find tags that were in the input but *not* used in the template substitution
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