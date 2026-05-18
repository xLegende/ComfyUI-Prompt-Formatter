# /ComfyUI-Prompt-Formatter/prompt_normalizer.py

import re

class PromptNormalizer:
    """
    A ComfyUI node to normalize prompts:
    - Normalizes brackets to their minimum matching pair
    - Removes excessive whitespace
    - Properly spaces commas, bracketing, and |
    - Converts nested brackets ((a)) to a single bracket weight (a:1.21)
    """
    NODE_NAME = "Prompt Normalizer"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "weight_step": ("FLOAT", {"default": 1.1, "min": 0.1, "max": 2.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("normalized_prompt",)
    FUNCTION = "normalize_prompt"
    CATEGORY = "text/utilities"

    def normalize_prompt(self, prompt, weight_step=1.1):
        if not prompt:
            return ("",)

        # 1. Clean up whitespace and spacing (brackets, pipes, multiple spacing)
        text = re.sub(r'\s+', ' ', prompt)
        text = re.sub(r'\s*\|\s*', '|', text)
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        text = re.sub(r'\[\s+', '[', text)
        text = re.sub(r'\s+\]', ']', text)
        
        # 2. Split by commas while tracking outer brackets to bypass internal splits
        tokens = []
        depth = 0
        current =[]
        for char in text:
            if char in '([{':
                depth += 1
                current.append(char)
            elif char in ')]}':
                depth -= 1
                current.append(char)
            elif char == ',' and depth <= 0:
                tokens.append("".join(current))
                current =[]
                depth = 0 # reset negative depth
            else:
                current.append(char)
        if current:
            tokens.append("".join(current))
            
        # 3. Process individual tags securely ensuring mathematical extraction
        processed_tokens =[]
        for token in tokens:
            tag = token.strip()
            if not tag:
                continue
                
            m = re.match(r'^([\[\(]+)(.*?)([\]\)]+)$', tag)
            if m:
                opens = m.group(1)
                content = m.group(2)
                closes = m.group(3)
                
                open_round = opens.count('(')
                close_round = closes.count(')')
                min_round = min(open_round, close_round)
                
                open_square = opens.count('[')
                close_square = closes.count(']')
                min_square = min(open_square, close_square)
                
                base_weight = 1.0
                text_content = content
                weight_m = re.search(r':([0-9.]+)\s*$', content)
                
                if weight_m:
                    try:
                        base_weight = float(weight_m.group(1))
                        text_content = content[:weight_m.start()].strip()
                        # Base webUI explicit weight consumes exactly one outer round bracket format syntax requirement
                        if min_round > 0:
                            min_round -= 1
                    except ValueError:
                        pass
                elif not content and (min_round > 0 or min_square > 0):
                     continue
                     
                if min_round == 0 and min_square == 0 and abs(base_weight - 1.0) < 1e-5:
                     processed_tokens.append(content.strip())
                     continue
                
                weight = base_weight * (weight_step ** min_round) * ((1.0 / weight_step) ** min_square)
                
                if abs(weight - 1.0) < 1e-5:
                    processed_tokens.append(text_content)
                else:
                    weight_str = f"{weight:.2f}".rstrip('0').rstrip('.')
                    if weight_str.endswith('.'):
                        weight_str = weight_str[:-1]
                    processed_tokens.append(f"({text_content}:{weight_str})")
            else:
                # Target un-bracketed or highly unbalanced remnants
                tag = re.sub(r'^([\[\(]+)', '', tag)
                tag = re.sub(r'([\]\)]+)$', '', tag)
                processed_tokens.append(tag)
                
        final_prompt = ", ".join(processed_tokens)
        return (final_prompt,)