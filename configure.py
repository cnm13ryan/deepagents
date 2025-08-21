#!/usr/bin/env python3
"""
DeepAgents Configuration Helper

This script provides an interactive way to configure DeepAgents for different providers.
It creates the necessary .env files with the right settings.
"""

import os
import sys
from pathlib import Path

def get_repo_root():
    """Find the repository root directory."""
    current = Path(__file__).parent.absolute()
    while current != current.parent:
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path(__file__).parent.absolute()

def create_env_file(path, content):
    """Create or update an .env file with the given content."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        f.write(content)
    
    print(f"✓ Created {path}")

def configure_ollama():
    """Configure for Ollama provider."""
    print("\n📋 Configuring Ollama...")
    
    # Get available models if ollama is installed
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print("\nAvailable Ollama models:")
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    print(f"  - {model_name}")
            print()
    except:
        pass
    
    default_model = "qwen3:4b-thinking-2507-q4_K_M"
    model = input(f"Enter Ollama model name (default: {default_model}): ").strip()
    if not model:
        model = default_model
    
    base_url = input("Enter Ollama base URL (default: http://localhost:11434, press Enter to skip): ").strip()
    
    env_content = f"# Ollama Configuration\n"
    env_content += f"DEEPAGENTS_MODEL_PROVIDER=ollama\n"
    env_content += f"OLLAMA_MODEL_NAME={model}\n"
    if base_url:
        env_content += f"OLLAMA_BASE_URL={base_url}\n"
    
    return env_content

def configure_lm_studio():
    """Configure for LM-Studio provider.

    Prompts for the base URL first, then queries that URL for available
    models and allows the user to select one, or enter a custom name.
    """
    print("\n📋 Configuring LM-Studio...")

    # Prompt for base URL first
    base_url = input(
        "Enter LM-Studio base URL (default: http://localhost:1234/v1): "
    ).strip()
    if not base_url:
        base_url = "http://localhost:1234/v1"

    # Try to fetch available models from the provided base URL
    available_models = []
    try:
        import requests  # local import; optional dependency
        models_endpoint = f"{base_url.rstrip('/')}" + "/models"
        response = requests.get(models_endpoint, timeout=3)
        if response.status_code == 200:
            models_data = response.json()
            for model in models_data.get("data", []) or []:
                mid = model.get("id")
                if mid:
                    available_models.append(mid)
    except Exception:
        # Non-fatal; proceed without model listing
        pass

    # Ask user to choose a model
    default_model = "qwen/qwen3-4b-thinking-2507"
    chosen_model = ""
    if available_models:
        print("\nAvailable LM-Studio models:")
        for idx, mid in enumerate(available_models, start=1):
            print(f"  {idx}. {mid}")
        print()
        selection = input(
            "Select a model by number or type a name "
            f"(default: {available_models[0]}): "
        ).strip()
        if not selection:
            chosen_model = available_models[0]
        else:
            if selection.isdigit():
                sel_idx = int(selection)
                if 1 <= sel_idx <= len(available_models):
                    chosen_model = available_models[sel_idx - 1]
            if not chosen_model:
                # Treat input as a direct model name
                chosen_model = selection
    else:
        print(
            "\n⚠️  Could not retrieve models from the provided URL. "
            "You may still enter a model name manually."
        )
        chosen_model = input(
            f"Enter model name (default: {default_model}): "
        ).strip() or default_model

    env_content = f"# LM-Studio Configuration\n"
    env_content += f"DEEPAGENTS_MODEL_PROVIDER=lm-studio\n"
    env_content += f"LM_STUDIO_BASE_URL={base_url}\n"
    env_content += f"LM_STUDIO_API_KEY=lm-studio\n"
    env_content += f"LM_STUDIO_MODEL_NAME={chosen_model or default_model}\n"

    return env_content

def configure_tavily():
    """Configure Tavily search (optional)."""
    print("\n📋 Configuring Web Search (Optional)...")
    print("Tavily provides web search capabilities to the research agent.")
    
    use_tavily = input("Enable Tavily web search? (y/N): ").strip().lower()
    if use_tavily in ['y', 'yes']:
        api_key = input("Enter your Tavily API key: ").strip()
        if api_key:
            return f"\n# Tavily Web Search\nTAVILY_API_KEY={api_key}\n"
    
    return "\n# Tavily Web Search (disabled)\n# TAVILY_API_KEY=your_key_here\n"

def configure_google():
    """Interactively configure Google Programmable Search (optional).

    Prompts for the Custom Search Engine ID first, then the API key.
    """
    print("\n🔧 Configuring Google Custom Search (Optional)...")
    print(
        "Google Custom Search provides web search capabilities to the research agent.\n"
        "You must supply both a Custom Search Engine ID (CSE ID) and an API key."
    )

    use_google = input("Enable Google web search? (y/N): ").strip().lower()
    if use_google in {"y", "yes"}:
        cse_id = input("Enter your Google Custom Search Engine ID: ").strip()
        api_key = input("Enter your Google API key: ").strip()
        if api_key and cse_id:
            return (
                "\n# Google Web Search\n"
                f"GOOGLE_CSE_ID={cse_id}\n"
                f"GOOGLE_API_KEY={api_key}\n"
            )

    return (
        "\n# Google Web Search (disabled)\n"
        "# GOOGLE_CSE_ID=your_cse_id_here\n"
        "# GOOGLE_API_KEY=your_key_here\n"
    )

def main():
    """Main configuration process."""
    print("🧠🤖 DeepAgents Configuration Helper")
    print("=====================================")
    print()
    print("This script will help you configure DeepAgents for local usage.")
    print("It supports Ollama and LM-Studio as local model providers.")
    print()
    
    # Choose provider
    print("Available providers:")
    print("1. Ollama (recommended for beginners)")
    print("2. LM-Studio (OpenAI-compatible API)")
    print()
    
    choice = input("Choose provider (1 or 2): ").strip()
    
    if choice == "1":
        env_content = configure_ollama()
    elif choice == "2":
        env_content = configure_lm_studio()
    else:
        print("❌ Invalid choice. Exiting.")
        sys.exit(1)
    
    # Append optional search provider configuration
    env_content += configure_tavily()
    env_content += configure_google()
    
    # Create .env files
    repo_root = get_repo_root()
    research_dir = repo_root / "examples" / "research"
    
    print(f"\n📁 Creating configuration files...")
    
    # Create both root and research .env files
    create_env_file(repo_root / ".env", env_content)
    create_env_file(research_dir / ".env", env_content)
    
    print(f"\n✅ Configuration complete!")
    print(f"\nNext steps:")
    print(f"1. Install dependencies: uv sync")
    print(f"2. Run the research agent:")
    print(f"   • CLI: uv run python examples/research/run_local.py \"Your research question\"")
    print(f"   • Studio: cd examples/research && langgraph dev")
    print(f"\nConfiguration files created:")
    print(f"  - {repo_root / '.env'}")
    print(f"  - {research_dir / '.env'}")

if __name__ == "__main__":
    main()
