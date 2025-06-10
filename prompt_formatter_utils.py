# /ComfyUI-Prompt-Formatter/prompt_formatter_utils.py

import yaml
import re
import sys
from pathlib import Path

# --- Dependency Check ---
try:
    import yaml
except ImportError:
    # This will be printed on the console when ComfyUI loads the nodes
    print("PyYAML is not installed. Please run install.py or install it manually.", file=sys.stderr)
    # Re-raise the error to prevent nodes from being registered if the dependency is missing
    raise ImportError("PyYAML is required for ComfyUI-Prompt-Formatter nodes.")

# --- Constants ---
INCLUDE_DIRECTIVE = "$include"
TAGS_KEY = "tags"

# --- Path Utilities ---

def get_node_directory():
    """Gets the directory path of the custom node pack."""
    return Path(__file__).parent

def find_yaml_file(filename: str, node_name: str = "Prompt Formatter"):
    """
    Finds a YAML file by checking for an absolute path, a path relative to the node,
    and a path within various possible 'input' directories.
    """
    if not filename:
        return None
        
    if Path(filename).is_absolute():
        if Path(filename).is_file(): return Path(filename)
        else:
            print(f"Warning [{node_name}]: Absolute path specified but not found: {filename}")
            return None
            
    node_dir = get_node_directory()
    relative_to_node = node_dir / filename
    if relative_to_node.is_file(): return relative_to_node
        
    try:
        search_dir = Path.cwd()
        # Look in standard ComfyUI input dir first
        input_dir_path = search_dir / 'input' / filename
        if input_dir_path.is_file(): return input_dir_path

        # Fallback search moving up from the node directory to find ComfyUI root
        search_dir = node_dir
        for _ in range(5):
            is_comfy_root = (search_dir / 'ComfyUI').exists() or (search_dir / 'main.py').exists()
            if is_comfy_root:
                input_dir_path = search_dir / 'input' / filename
                if input_dir_path.is_file(): return input_dir_path
                break
                
            parent = search_dir.parent
            if parent == search_dir: break
            search_dir = parent
    except Exception as e:
        print(f"Warning [{node_name}]: Error searching for ComfyUI input directory: {e}")
        
    print(f"Warning [{node_name}]: YAML file '{filename}' not found as absolute, relative to node, or in standard input directories.")
    return None

# --- String & Tag Processing ---

def clean_output_string(text: str, delimiter: str = ", "):
    """Cleans up the final output string by normalizing delimiters and trimming whitespace."""
    if not text: return ""
    text = text.strip().strip(delimiter.strip()).strip()
    delimiter_pattern = r'\s*' + re.escape(delimiter.strip()) + r'\s*'
    text = re.sub(f'({delimiter_pattern})+', delimiter, text)
    return text.strip(delimiter.strip()).strip()

def parse_tag(tag: str, handle_weights: bool = True):
    """
    Parses a tag to extract the base tag (without weights/emphasis).
    """
    original_tag = str(tag).strip()
    if not handle_weights: return original_tag, original_tag
        
    base_tag = original_tag
    patterns = [
        r"^\s*\(\s*(.*?)\s*(?::\s*[\d.]+\s*)?\)\s*$", # (tag:weight) or (tag)
        r"^\s*\[\s*(.*?)\s*\]\s*$",                  # [tag]
        r"^\s*\{\s*(.*?)\s*\}\s*$"                   # {tag}
    ]
    
    for pattern in patterns:
        match = re.match(pattern, original_tag)
        if match:
            base_tag = match.group(1).strip()
            nested_match = re.match(r"^\s*[\(\[\{](.*?)[\)\]\}]\s*$", base_tag)
            if nested_match: base_tag = nested_match.group(1).strip()
            return original_tag, base_tag
            
    return original_tag, base_tag.strip()

# --- YAML Category Resolution ---

def resolve_category_tags(category_name: str, yaml_data: dict, resolved_cache: dict, node_name: str = "Prompt Formatter", recursion_guard: set = None):
    """
    Recursively resolves tags for a category, handling includes and inline expansion.
    """
    category_name = str(category_name).strip()
    if recursion_guard is None: recursion_guard = set()
        
    if len(recursion_guard) > 20:
        print(f"Warning [{node_name}]: Recursion depth limit exceeded for '{category_name}'.")
        return set()
    if category_name in recursion_guard:
        print(f"Warning [{node_name}]: Circular dependency for category '{category_name}'.")
        return set()
    if category_name in resolved_cache: return resolved_cache[category_name]
    if category_name not in yaml_data: return set()

    recursion_guard.add(category_name)
    category_data = yaml_data[category_name]
    final_tags = set()

    if isinstance(category_data, list):
        for item in category_data:
            item_str = str(item).strip()
            if not item_str: continue

            is_full_include = item_str.startswith('$') and len(item_str) > 1 and ' ' not in item_str and item_str[1:].replace('_', '').isalnum()
            if is_full_include:
                final_tags.update(resolve_category_tags(item_str[1:], yaml_data, resolved_cache, node_name, recursion_guard.copy()))
            else:
                match = re.search(r'\$(\w+)', item_str)
                if match:
                    ref_cat_name = match.group(1)
                    resolved_ref_tags = resolve_category_tags(ref_cat_name, yaml_data, resolved_cache, node_name, recursion_guard.copy())
                    if not resolved_ref_tags:
                        print(f"Warning [{node_name}]: Inline reference ${ref_cat_name} in '{item_str}' is empty or not found.")
                    for r_tag in resolved_ref_tags:
                        final_tags.add(item_str.replace(match.group(0), str(r_tag).strip(), 1))
                else:
                    final_tags.add(item_str)
    elif isinstance(category_data, dict):
        if INCLUDE_DIRECTIVE in category_data:
            includes = category_data[INCLUDE_DIRECTIVE]
            include_list = [str(inc).strip() for inc in includes] if isinstance(includes, list) else [str(includes).strip()]
            for included_category in include_list:
                final_tags.update(resolve_category_tags(included_category, yaml_data, resolved_cache, node_name, recursion_guard.copy()))
        if TAGS_KEY in category_data and isinstance(category_data[TAGS_KEY], list):
             final_tags.update(str(tag).strip() for tag in category_data[TAGS_KEY] if str(tag).strip())
    else:
        print(f"Warning [{node_name}]: Category '{category_name}' type '{type(category_data).__name__}' is not a list or dict.")

    resolved_cache[category_name] = final_tags
    return final_tags