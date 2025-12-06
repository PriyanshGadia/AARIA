#!/usr/bin/env python3
"""
AARIA - Environment Setup Demo
Shows how to configure API keys using config/llm.env file
"""

import sys
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

from env_loader import EnvironmentLoader, create_env_example

def main():
    print("=" * 70)
    print("AARIA LLM Configuration Setup")
    print("=" * 70)
    
    # Check if .env.example exists, create if not
    example_path = Path("config/.env.example")
    if not example_path.exists():
        print("\n📝 Creating example configuration file...")
        create_env_example()
    else:
        print(f"\n✓ Example file exists: {example_path}")
    
    # Check if llm.env exists
    env_path = Path("config/llm.env")
    if not env_path.exists():
        print(f"\n⚠️  Configuration file not found: {env_path}")
        print("\n📋 To set up your API keys:")
        print(f"   1. Copy the example: cp {example_path} {env_path}")
        print(f"   2. Edit {env_path} and add your actual API keys")
        print(f"   3. Run AARIA: python Backend/stem.py")
        print(f"\n💡 Tip: Get a free Groq API key at https://console.groq.com/")
    else:
        print(f"\n✓ Configuration file found: {env_path}")
        
        # Load and check what's configured
        print("\n🔍 Checking configured API keys...")
        loader = EnvironmentLoader()
        env_vars = loader.load()
        
        if env_vars:
            print(f"\n✓ Loaded {len(env_vars)} API key(s):")
            
            # Check each provider
            providers = {
                "OPENAI_API_KEY": "OpenAI (GPT-3.5, GPT-4)",
                "GROQ_API_KEY": "Groq (Llama3, ultra-fast, FREE)",
                "GEMINI_API_KEY": "Google Gemini (FREE tier)",
                "ANTHROPIC_API_KEY": "Anthropic Claude"
            }
            
            configured = []
            for key, description in providers.items():
                value = loader.get(key)
                if value:
                    configured.append(description.split("(")[0].strip())
                    # Show partial key for verification
                    masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                    print(f"   ✓ {description}")
                    print(f"     Key: {masked}")
            
            if configured:
                print(f"\n🎉 Ready to use: {', '.join(configured)}")
                print("\n▶️  Run AARIA: python Backend/stem.py")
            else:
                print("\n⚠️  No valid API keys found in config/llm.env")
                print("   Add your keys to the file and try again")
        else:
            print("\n⚠️  No API keys loaded from config/llm.env")
            print("   Make sure the file contains valid KEY=value lines")
    
    # Check for Ollama
    print("\n🖥️  Local Ollama Status:")
    print("   To use 100% FREE local AI (no API key needed):")
    print("   1. Install: curl https://ollama.ai/install.sh | sh")
    print("   2. Pull model: ollama pull llama3:latest")
    print("   3. AARIA will auto-detect and use it")
    
    print("\n" + "=" * 70)
    print("Setup complete! See config/README.md for more details.")
    print("=" * 70)

if __name__ == "__main__":
    main()
