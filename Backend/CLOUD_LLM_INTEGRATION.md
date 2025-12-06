# Cloud LLM Integration Architecture for AARIA
## Version: 1.0.0
## Date: 2025-12-06

## Overview

Integrating cloud LLM (Large Language Model) services into AARIA requires careful architectural consideration to maintain the system's core principles of privacy, security, and owner sovereignty.

## Design Principles

1. **Privacy First**: Owner data must never leave the local system without explicit consent
2. **Hybrid Architecture**: Local processing for sensitive data, cloud for complex reasoning
3. **Fallback Capability**: System must function without cloud connectivity
4. **Cost Control**: Implement token usage monitoring and budget limits
5. **Model Agnostic**: Support multiple LLM providers (OpenAI, Anthropic, Local models)

## Recommended Architecture

### 1. LLM Abstraction Layer

Create a unified interface that can route requests to different LLM backends:

```python
class LLMProvider(Enum):
    LOCAL = "local"           # Local models (LLaMA, Mistral via Ollama)
    OPENAI = "openai"         # OpenAI GPT models
    ANTHROPIC = "anthropic"   # Claude models
    AZURE = "azure"           # Azure OpenAI
    
class LLMGateway:
    """Central gateway for all LLM interactions"""
    
    async def generate_response(
        self,
        prompt: str,
        provider: LLMProvider = LLMProvider.LOCAL,
        context: Dict[str, Any] = None,
        privacy_level: str = "confidential"
    ) -> Dict[str, Any]:
        """
        Generate response with privacy-aware routing
        
        Args:
            prompt: The prompt to send to the LLM
            provider: Which LLM provider to use
            context: Additional context (filtered based on privacy_level)
            privacy_level: "public", "confidential", "owner_only"
        """
        # Filter sensitive data based on privacy level
        sanitized_prompt = self._sanitize_prompt(prompt, privacy_level)
        
        # Route to appropriate provider
        if provider == LLMProvider.LOCAL:
            return await self._local_llm(sanitized_prompt, context)
        elif provider == LLMProvider.OPENAI:
            return await self._openai_llm(sanitized_prompt, context)
        # ... other providers
```

### 2. Integration Points

#### A. Frontal Core (Decision Making)
- Use cloud LLM for complex reasoning and planning
- Send only task descriptions, not personal data
- Example: "Generate a plan to organize files" vs. "Organize my files at C:/Personal/..."

#### B. Temporal Core (Conversation)
- Use cloud LLM for natural language understanding and generation
- Filter out personal identifiers, locations, financial data
- Maintain conversation context locally, send only sanitized turns

#### C. Memory Core (Knowledge Base)
- Keep all owner data local
- Use cloud LLM for semantic search and knowledge synthesis
- Send only public/general knowledge queries

### 3. Privacy-Aware Data Flow

```
User Input
    ↓
[Temporal Core - Local NLP]
    ↓
[Privacy Filter]
    ├─→ Sensitive Data → Local Processing Only
    └─→ General Data → Cloud LLM (optional)
            ↓
    [LLM Gateway]
            ↓
    [Response Filter]
            ↓
    [Temporal Core - Response Generation]
            ↓
    Output to User
```

### 4. Implementation Strategy

#### Phase 1: Local-First Foundation (CURRENT)
- ✅ All processing happens locally
- ✅ Basic NLP with NLTK
- ✅ Rule-based conversation
- ✅ No external dependencies

#### Phase 2: Hybrid Architecture (RECOMMENDED)
- Add LLMGateway class to Frontal Core
- Implement privacy filtering in Memory Core
- Add configuration for LLM provider selection
- Implement token usage tracking and budget limits

#### Phase 3: Enhanced Intelligence
- Use cloud LLM for complex reasoning
- Implement RAG (Retrieval-Augmented Generation) with local knowledge base
- Add semantic caching to reduce API calls
- Implement streaming responses for better UX

## Specific Integration Points

### 1. Frontal Core Enhancement

```python
# Add to frontal_core.py

class LLMEnhancedFrontalCore(FrontalCore):
    def __init__(self):
        super().__init__()
        self.llm_gateway = LLMGateway()
        self.use_cloud_llm = False  # Configurable
    
    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced decision making with optional cloud LLM"""
        
        # Local reasoning first
        local_decision = await super().make_decision(context)
        
        # If complex and cloud LLM enabled, enhance decision
        if self.use_cloud_llm and context.get("complexity", 0) > 0.7:
            # Sanitize context
            safe_context = self._sanitize_context(context)
            
            # Get enhanced reasoning from cloud LLM
            llm_response = await self.llm_gateway.generate_response(
                prompt=f"Analyze this decision: {safe_context}",
                provider=LLMProvider.OPENAI,
                privacy_level="public"
            )
            
            # Merge local and cloud decisions
            enhanced_decision = self._merge_decisions(
                local_decision, 
                llm_response
            )
            
            return enhanced_decision
        
        return local_decision
```

### 2. Temporal Core Enhancement

```python
# Add to temporal_core.py

class LLMEnhancedTemporalCore(TemporalCore):
    def __init__(self):
        super().__init__()
        self.llm_gateway = LLMGateway()
    
    async def process_text_input(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process with optional cloud LLM enhancement"""
        
        # Local NLP analysis
        nlp_analysis = self.nlp_pipeline.detect_intent(text)
        
        # Use cloud LLM for complex queries
        if nlp_analysis["primary_intent"] == "question" and context.get("use_cloud_llm"):
            # Generate enhanced response
            response = await self.llm_gateway.generate_response(
                prompt=text,
                provider=LLMProvider.OPENAI,
                context={"conversation_history": context.get("recent_turns", [])},
                privacy_level="confidential"
            )
            
            return {
                "success": True,
                "nlp_analysis": nlp_analysis,
                "response_generation": {
                    "generated_response": response["text"],
                    "provider": "cloud_llm",
                    "confidence": response["confidence"]
                }
            }
        
        # Fall back to local processing
        return await super().process_text_input(text, context)
```

## Security Considerations

1. **API Key Management**
   - Store API keys in encrypted config database
   - Support key rotation
   - Never log API keys

2. **Data Sanitization**
   - Remove personal identifiers (names, addresses, phone numbers)
   - Strip file paths and system information
   - Filter sensitive keywords

3. **Audit Trail**
   - Log all cloud LLM requests (without sensitive data)
   - Track token usage and costs
   - Monitor for data leakage

4. **User Consent**
   - Require explicit permission for cloud processing
   - Allow per-request opt-in/opt-out
   - Display clear indicators when cloud LLM is active

## Configuration Example

```python
# Add to secure_config_db.py defaults

llm_config = {
    "enabled": False,  # Disabled by default
    "default_provider": "local",
    "providers": {
        "openai": {
            "api_key": None,  # Set via environment variable
            "model": "gpt-4-turbo-preview",
            "max_tokens": 1000,
            "temperature": 0.7
        },
        "anthropic": {
            "api_key": None,
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000
        },
        "local": {
            "model": "llama2",
            "endpoint": "http://localhost:11434"  # Ollama
        }
    },
    "privacy_filters": {
        "strip_pii": True,
        "strip_file_paths": True,
        "allowed_topics": ["general", "technology", "science"]
    },
    "budget": {
        "max_tokens_per_day": 100000,
        "max_cost_per_month": 50.0  # USD
    }
}
```

## Cost Estimation

**OpenAI GPT-4 Turbo:**
- Input: $10 per 1M tokens
- Output: $30 per 1M tokens
- Average conversation: ~1000 tokens
- 100 conversations/day = ~$4/month

**Anthropic Claude:**
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- More cost-effective for high-volume use

**Local LLM (Recommended for Privacy):**
- No API costs
- Requires GPU (RTX 3060 12GB minimum)
- Models: LLaMA 2, Mistral, Phi-2

## Recommended Approach

1. **Start with Local LLM** using Ollama
   - Install Ollama: `curl https://ollama.ai/install.sh | sh`
   - Pull model: `ollama pull llama2`
   - No privacy concerns, no costs

2. **Add Cloud LLM as Optional Enhancement**
   - For complex reasoning only
   - With strict privacy filtering
   - With user consent

3. **Implement Hybrid Strategy**
   - Local: 80% of queries (fast, private, free)
   - Cloud: 20% of queries (complex reasoning)

## Next Steps

To implement cloud LLM integration:

1. Create `Backend/llm_gateway.py` with the LLMGateway class
2. Add LLM configuration to secure_config_db.py
3. Implement privacy filters in `Backend/privacy_filter.py`
4. Add LLM provider clients (OpenAI, Anthropic, Ollama)
5. Update Frontal and Temporal cores with optional LLM enhancement
6. Add token usage tracking and budget enforcement
7. Create comprehensive tests for privacy filters

## References

- OpenAI API: https://platform.openai.com/docs/api-reference
- Anthropic API: https://docs.anthropic.com/claude/reference
- Ollama (Local LLM): https://ollama.ai/
- LangChain (LLM orchestration): https://python.langchain.com/
