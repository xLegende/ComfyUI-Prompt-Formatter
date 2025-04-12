# ComfyUI - Categorized Prompt Formatter Node

A custom node for ComfyUI that allows you to filter and restructure text prompts based on tag categories defined in a YAML file.

This node takes a standard comma-separated prompt, categorizes each tag according to your definitions, and then rebuilds the prompt based on a template you provide. It's useful for enforcing prompt structure, extracting specific concepts, or reordering elements dynamically.

![Example Node UI (Conceptual - Actual UI may vary slightly)](placeholder_image.png)

## Features

*   **YAML-based Categorization:** Define which tags belong to which categories in a simple `.yaml` file.
*   **Multi-Category Tags:** A single tag (e.g., "blue eyes") can belong to multiple categories (e.g., `eyes`, `person_details`).
*   **Template-Driven Output:** Structure your output prompt using placeholders like `<|category_name|>`.
*   **Flexible Delimiters:** Configure input and output delimiters.
*   **Weight/Emphasis Handling:** Attempts to preserve common syntax like `(tag:1.2)` and `[tag]` while using the base tag for categorization.
*   **Underscore/Space Matching:** Optionally treat tags like `red_eyes` and `red eyes` as equivalent during matching (while preserving original format in output).
*   **Duplicate Prevention:** Optionally prevent the same tag from appearing multiple times in the output, even if referenced by multiple categories in the template (first occurrence wins).
*   **Case Sensitivity Option:** Choose whether matching should be case-sensitive or not.
*   **Unmatched Tag Handling:** Decide whether to discard tags not used in the template, append them to the end, or output them separately.

## Installation

1.  Clone this repository into your `ComfyUI/custom_nodes/` directory:
    ```bash
    cd ComfyUI/custom_nodes/
    git clone https://github.com/xLegende/ComfyUI-Prompt-Formatter.git
    ```
	
2.  Install dependencies:
    *   Navigate to the node's directory: `cd ComfyUI-Prompt-Formatter`
    *   Run the install script using your ComfyUI Python environment:
        ```bash
        # Example using a virtual environment:
        # path/to/your/ComfyUI/python_env/bin/python install.py
        # Or if your system python is the one used by ComfyUI:
        python install.py
        ```
    *   This will install the `PyYAML` library if it's not already present.
3.  Restart ComfyUI.

The node "📝 Categorized Prompt Formatter" should now appear under the "text/filtering" category when you right-click or double-click on the ComfyUI canvas.

## Usage

1.  **Prepare your YAML file:**
    *   Create a `.yaml` file (e.g., `my_categories.yaml`) or modify the included `prompt_categories.yaml`.
    *   The format is:
        ```yaml
        category_name_1:
          - tag1
          - tag2
          - tag_shared
        category_name_2:
          - tag3
          - tag_shared # This tag now belongs to both categories
          - "(tag with weight:1.1)" # Define tags exactly as they might appear
        # ... etc
        ```
    *   Place this file somewhere ComfyUI can find it (e.g., in the `ComfyUI/input/` directory, or provide an absolute path, or place it in the `custom_nodes/ComfyUI-Prompt-Formatter/` folder).
2.  **Add the Node:** Add the "📝 Categorized Prompt Formatter" node to your workflow.
3.  **Connect Input:** Connect your source prompt string to the `prompt` input.
4.  **Configure Widgets:**
    *   `category_definition_file`: Enter the name (e.g., `my_categories.yaml`) or full path to your YAML file. The node will search relative to itself, in `ComfyUI/input/`, and absolute paths.
    *   `output_template`: Define your desired output structure using `<|category_name|>` placeholders. Example: `<|quality|>, <|character_num|>, <|eyes|>, <|clothing|>, <|setting|>`
    *   Adjust delimiters, case sensitivity, weight handling, and unmatched tag handling as needed.
	*   `match_underscores_spaces` (Boolean, default: True): If enabled, the node will try to match input tags against YAML definitions by checking variants with underscores swapped for spaces (e.g., input `red_eyes` can match YAML `red eyes`, and vice-versa). The original format of the input tag is kept for the output string.
5.  **Connect Output:** Connect the `formatted_prompt` output to the next node in your workflow (e.g., a CLIP Text Encode node). Use the optional `rejected_prompt` output for debugging or alternative workflows.

## Example

*   **Input Prompt:** `"masterpiece, 1girl, (red eyes:1.1), long hair, wearing a blue dress, outdoors, detailed background"`
*   **YAML (`prompt_categories.yaml` from this repo):** (Contains categories like `quality`, `character_num`, `eyes`, `hair_style`, `person_details`, `clothing`, `setting`)
*   **Output Template:** `<|quality|>, <|character_num|>, <|eyes|>, <|clothing|>, <|setting|>`
*   **Unmatched Handling:** `output_separately`

*   **Result (`formatted_prompt`):** `"masterpiece, 1girl, (red eyes:1.1), wearing a blue dress, outdoors"`
*   **Result (`rejected_prompt`):** `"long hair, detailed background"` (Because `<|hair_style|>` wasn't in the template, and "detailed background" might not be defined or its category wasn't used)

## Notes

*   The YAML file path finding tries to be robust, checking relative to the node, the ComfyUI `input` directory, and absolute paths. If it can't find the file, it will print a warning and proceed without categorization.
*   Weight handling uses regular expressions to parse common patterns. Very complex nested structures might not parse correctly. The base tag extracted is used for lookup.
*   If a tag belongs to multiple categories, and the template requests those multiple categories, the tag **will appear multiple times** in the output string by default.