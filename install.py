# /ComfyUI-Prompt-Formatter/install.py

import subprocess
import sys
import os

def install_dependencies():
    print("...")
    print("...")
    print("Installing dependencies for ComfyUI-Prompt-Formatter")
    print("...")
    print("...")
    try:
        print("Installing PyYAML...")
        # Use pip directly from the Python executable path
        python_exe = sys.executable
        subprocess.check_call([python_exe, '-m', 'pip', 'install', 'PyYAML'])
        print("PyYAML installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing PyYAML: {e}")
        print("Please try installing PyYAML manually:")
        print(f"'{sys.executable}' -m pip install PyYAML")
    except Exception as e:
        print(f"An unexpected error occurred during installation: {e}")

# Check if run as main script
if __name__ == "__main__":
    install_dependencies()

    # Check if running in Colab or Paperspace to potentially avoid restart prompt
    if 'COLAB_GPU' in os.environ or 'PAPERSPACE_NOTEBOOK_ID' in os.environ:
         print("\nDependency installation complete. Please proceed.")
    else:
        # Basic prompt for non-automated environments
        print("\nDependency installation finished.")
        print("If ComfyUI is running, you may need to restart it for the changes to take effect.")