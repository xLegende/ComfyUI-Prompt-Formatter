# /ComfyUI-Prompt-Formatter/wildcard_importer.py

import yaml
import os
import sys
from pathlib import Path

# --- Dependency Check ---
try:
    import yaml
except ImportError:
    print("PyYAML is not installed. Please run install.py or install it manually.", file=sys.stderr)

# --- Constants ---
NODE_NAME_IMPORTER = "Wildcard Importer"

# --- Helper Functions ---
def get_node_pack_directory():
    """Gets the directory path of this custom node pack."""
    return Path(__file__).parent

# --- The Importer Node Class ---
class WildcardImporter:
    @classmethod
    def INPUT_TYPES(cls):
        # Determine default wildcard directory path relative to this node pack
        default_wildcard_dir = get_node_pack_directory() / 'wildcards'
        
        return {
            "required": {
                "wildcard_directory": ("STRING", {"multiline": True, "default": str(default_wildcard_dir)}),
                "output_yaml_file": ("STRING", {"default": "imported_wildcards.yaml"}),
                "wildcards_to_import": ("STRING", {"default": "*"}),
                "write_mode": (["Overwrite", "Merge (Skip Existing Categories)", "Merge (Overwrite Existing Categories)", "Merge (Append Unique Tags)"], {"default": "Overwrite"}),
                "ignore_private_wildcards": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("output_yaml_path", "status_message", "files_processed_count")
    FUNCTION = "import_wildcards"
    CATEGORY = "text/utilities"

    def import_wildcards(self, wildcard_directory, output_yaml_file, wildcards_to_import, write_mode, ignore_private_wildcards):
        
        # --- 1. Path Handling & Validation ---
        wildcard_dir_path = Path(wildcard_directory)
        if not wildcard_dir_path.is_dir():
            status_msg = f"ERROR: Wildcard directory not found at '{wildcard_directory}'"
            print(f"[Importer] {status_msg}")
            return ("", status_msg, 0)

        # Determine output path relative to THIS node pack's directory
        output_dir = get_node_pack_directory()
        # Ensure the output filename is safe
        safe_output_filename = os.path.basename(output_yaml_file)
        output_path = output_dir / safe_output_filename

        # --- 2. Initialize YAML Data based on Write Mode ---
        yaml_data = {}
        if write_mode.startswith("Merge"):
            if output_path.exists():
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        existing_data = yaml.safe_load(f)
                        if isinstance(existing_data, dict):
                            yaml_data = existing_data
                        else:
                            print(f"Warning [Importer]: Existing YAML '{output_path}' is not a valid dictionary. Starting fresh.")
                except Exception as e:
                    status_msg = f"ERROR: Could not read existing YAML for merging: {e}"
                    print(f"[Importer] {status_msg}")
                    return ("", status_msg, 0)

        # --- 3. Identify and Filter Target Wildcards ---
        try:
            all_wildcards = list(wildcard_dir_path.rglob('*.txt'))
        except Exception as e:
            status_msg = f"ERROR: Could not scan wildcard directory: {e}"
            print(f"[Importer] {status_msg}")
            return ("", status_msg, 0)

        target_wildcards = []
        if wildcards_to_import.strip() == '*':
            target_wildcards = all_wildcards
        else:
            requested_names = {name.strip() for name in wildcards_to_import.split(',')}
            for wc_path in all_wildcards:
                if wc_path.stem in requested_names:
                    target_wildcards.append(wc_path)

        # --- 4. Process Wildcards and Populate YAML Data ---
        processed_count = 0
        total_tags_added = 0
        print(f"[Importer] Starting import. Mode: {write_mode}. Targets: {len(target_wildcards)} files.")

        for wildcard_path in target_wildcards:
            filename = wildcard_path.name
            if ignore_private_wildcards and filename.startswith('_'):
                continue

            category_name = wildcard_path.stem

            # Handle Merge (Skip) logic
            if write_mode == "Merge (Skip Existing Categories)" and category_name in yaml_data:
                continue

            try:
                with open(wildcard_path, 'r', encoding='utf-8', errors='ignore') as f:
                    wildcard_tags = {line.strip() for line in f if line.strip() and not line.strip().startswith('#')}
                
                if not wildcard_tags: continue

                # --- MERGE LOGIC ---
                if write_mode == "Merge (Append Unique Tags)" and category_name in yaml_data:
                    # Append unique tags to an existing category
                    existing_tags = set(yaml_data.get(category_name, []))
                    new_tags = list(existing_tags.union(wildcard_tags))
                    tags_added_this_run = len(new_tags) - len(existing_tags)
                    yaml_data[category_name] = new_tags
                    total_tags_added += tags_added_this_run
                else:
                    # Overwrite or create new category
                    yaml_data[category_name] = list(wildcard_tags)
                    total_tags_added += len(wildcard_tags)

                processed_count += 1

            except Exception as e:
                print(f"Warning [Importer]: Could not process file '{filename}': {e}")
                continue

        # --- 5. Write Output YAML File ---
        try:
            # Sort categories alphabetically for consistent output
            sorted_yaml_data = dict(sorted(yaml_data.items()))
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(sorted_yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            status_msg = f"Success! Processed {processed_count} wildcards. Added/updated {total_tags_added} tags in '{safe_output_filename}'."
            print(f"[Importer] {status_msg}")
        except Exception as e:
            status_msg = f"ERROR: Could not write to output file '{output_path}': {e}"
            print(f"[Importer] {status_msg}")
            return ("", status_msg, 0)

        return (str(output_path), status_msg, processed_count)
