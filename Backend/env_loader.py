"""
AARIA - Environment Loader v1.0
Primary Module: Loads API keys and configuration from .env files
Update Notes: Initial deployment - Secure .env file loading for API keys
Security Level: High - Loads sensitive data from external files, never commits to git
Architecture: Simple key-value parser with support for comments and empty lines
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class EnvironmentLoader:
    """Loads environment variables from .env files"""
    
    def __init__(self, env_file_path: Optional[str] = None):
        """
        Initialize environment loader
        
        Args:
            env_file_path: Path to .env file. If None, uses default location (config/llm.env)
        """
        if env_file_path is None:
            # Default location: config/llm.env (outside Backend directory for security)
            self.env_file_path = Path(__file__).parent.parent / "config" / "llm.env"
        else:
            self.env_file_path = Path(env_file_path)
        
        self.env_vars: Dict[str, str] = {}
        
    def load(self) -> Dict[str, str]:
        """
        Load environment variables from .env file
        
        Returns:
            Dictionary of environment variables loaded from file
        """
        if not self.env_file_path.exists():
            logger.debug(f"Environment file not found: {self.env_file_path}")
            logger.debug("Using system environment variables only")
            return {}
        
        logger.info(f"Loading environment variables from: {self.env_file_path}")
        
        try:
            with open(self.env_file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Strip whitespace
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Store in dict
                        self.env_vars[key] = value
                        
                        # Also set in os.environ so other code can access it
                        os.environ[key] = value
                        
                        logger.debug(f"✓ Loaded {key} from {self.env_file_path.name}")
                    else:
                        logger.warning(f"Invalid line {line_num} in {self.env_file_path}: {line}")
            
            logger.info(f"✓ Loaded {len(self.env_vars)} environment variable(s) from {self.env_file_path.name}")
            return self.env_vars
            
        except Exception as e:
            logger.error(f"Error loading environment file {self.env_file_path}: {str(e)}")
            return {}
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Value from .env file, system environment, or default
        """
        # Priority: .env file > system environment > default
        return self.env_vars.get(key) or os.getenv(key) or default
    
    def create_example_file(self, output_path: Optional[Path] = None):
        """
        Create an example .env file with template
        
        Args:
            output_path: Where to save the example file. If None, creates .env.example in same directory
        """
        if output_path is None:
            output_path = self.env_file_path.parent / ".env.example"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        example_content = """# AARIA LLM API Keys Configuration
# Copy this file to 'llm.env' and add your actual API keys
# 
# SECURITY WARNING: 
# - NEVER commit llm.env to git (it's in .gitignore)
# - Keep your API keys secure and private
# - Rotate keys regularly (every 90 days recommended)

# ==================== CLOUD LLM PROVIDERS ====================

# OpenAI (https://platform.openai.com/api-keys)
# Cost: ~$0.50-$30 per 1M tokens depending on model
# Models: gpt-3.5-turbo, gpt-4, gpt-4-turbo
# OPENAI_API_KEY=sk-your-openai-api-key-here

# Groq (https://console.groq.com/keys)
# Cost: FREE tier available, ultra-fast inference
# Models: llama3-70b-8192, mixtral-8x7b
# Recommended for free usage with excellent performance
GROQ_API_KEY=your-groq-api-key-here

# Google Gemini (https://makersuite.google.com/app/apikey)
# Cost: FREE tier (60 requests/min), then ~$0.50 per 1M tokens
# Models: gemini-pro, gemini-pro-vision
# GEMINI_API_KEY=your-gemini-api-key-here

# Anthropic Claude (https://console.anthropic.com/account/keys)
# Cost: ~$15 per 1M tokens
# Models: claude-3-sonnet, claude-3-opus
# ANTHROPIC_API_KEY=your-anthropic-api-key-here

# ==================== LOCAL LLM (NO API KEY NEEDED) ====================

# Ollama (https://ollama.ai)
# Cost: 100% FREE - runs locally on your machine
# Models: llama3, mistral, codellama, etc.
# Installation: 
#   curl https://ollama.ai/install.sh | sh  (Linux/Mac)
#   Download from ollama.ai/download (Windows)
# Then: ollama pull llama3:latest
# No configuration needed - automatically detected if running

# ==================== NOTES ====================

# Priority order (AARIA will use first available):
# 1. Groq (fastest, free tier)
# 2. OpenAI (most capable)
# 3. Gemini (balanced, free tier)
# 4. Anthropic (high quality)
# 5. Ollama (local fallback)

# You can set multiple keys and AARIA will automatically
# fall back if one provider fails or rate limits.

# To use this file:
# 1. Copy to: config/llm.env
# 2. Uncomment and add your actual API keys
# 3. Run AARIA - keys will be auto-detected
"""
        
        with open(output_path, 'w') as f:
            f.write(example_content)
        
        logger.info(f"✓ Created example environment file: {output_path}")
        print(f"\n✓ Created example file: {output_path}")
        print(f"  Copy to: {self.env_file_path}")
        print(f"  Then add your API keys and run AARIA")

# ==================== UTILITY FUNCTIONS ====================

def load_llm_environment() -> Dict[str, str]:
    """
    Load LLM API keys from environment file
    
    Returns:
        Dictionary of loaded environment variables
    """
    loader = EnvironmentLoader()
    return loader.load()

def create_env_example():
    """Create example .env file"""
    loader = EnvironmentLoader()
    loader.create_example_file()

# ==================== TESTING ====================
if __name__ == "__main__":
    print("=" * 60)
    print("AARIA Environment Loader Test")
    print("=" * 60)
    
    # Create example file
    create_env_example()
    
    # Try to load environment
    print("\nAttempting to load environment from config/llm.env...")
    env_vars = load_llm_environment()
    
    if env_vars:
        print(f"\n✓ Loaded {len(env_vars)} variable(s):")
        for key in env_vars.keys():
            # Don't print actual values for security
            print(f"  • {key}: {'*' * 20}")
    else:
        print("\n✗ No environment file found or no variables loaded")
        print(f"  Create one at: config/llm.env")
        print(f"  Use .env.example as template")
    
    # Test getting specific keys
    print("\nChecking for API keys...")
    keys_to_check = ["OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]
    
    loader = EnvironmentLoader()
    for key in keys_to_check:
        value = loader.get(key)
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {'Found' if value else 'Not found'}")
