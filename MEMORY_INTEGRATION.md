# AARIA Memory Integration - Conversation Persistence

## Overview

AARIA now features a **centralized encrypted memory storage system** that maintains conversation history across sessions, creating a persistent "hive mind" independent of which LLM backend is used.

## Key Features

### 1. **Conversation Persistence**
- Every conversation turn (user input + AI response) is automatically stored in the encrypted Memory Core
- Conversations are tagged with metadata (intent, timestamp, LLM provider)
- Stored at `owner_confidential` tier for maximum security

### 2. **Contextual Memory Recall**
- Before generating each response, AARIA loads the last 3-5 conversation turns from memory
- Conversation history is included in the LLM system prompt
- Enables the LLM to maintain context and continuity

### 3. **LLM-Independent Memory**
- Memories are stored in AARIA's Memory Core, not in the LLM
- You can switch between Ollama, Gemini, GPT, or any other LLM
- Conversation context persists regardless of which backend is active

### 4. **Hierarchical Encrypted Storage**
- All memories are encrypted using AES-256-GCM
- Data segregation: Root Database → Owner Confidential → Access Data → Public Data
- Conversation data stored at "Owner Confidential" level

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Input                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Temporal Core                           │
│  ┌────────────────────────────────────────────┐    │
│  │ 1. Load recent conversation history        │    │
│  │    from Memory Core (last 3-5 turns)       │    │
│  └────────────────────────────────────────────┘    │
│                   │                                  │
│                   ▼                                  │
│  ┌────────────────────────────────────────────┐    │
│  │ 2. Build system prompt with:                │    │
│  │    - Personality traits                     │    │
│  │    - Conversation history                   │    │
│  │    - Current context                        │    │
│  └────────────────────────────────────────────┘    │
│                   │                                  │
│                   ▼                                  │
│  ┌────────────────────────────────────────────┐    │
│  │ 3. Send to LLM Gateway                      │    │
│  │    (Ollama/Gemini/GPT/etc.)                 │    │
│  └────────────────────────────────────────────┘    │
│                   │                                  │
│                   ▼                                  │
│  ┌────────────────────────────────────────────┐    │
│  │ 4. Store conversation turn in Memory Core   │    │
│  │    - User message                           │    │
│  │    - AI response                            │    │
│  │    - Metadata (intent, timestamp)           │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Memory Core                             │
│                                                      │
│  Encrypted Storage (.aaria_config.db)              │
│  ┌──────────────────────────────────────────┐     │
│  │  Conversation History (Owner Confidential) │     │
│  │  - Turn 1: User + AI                       │     │
│  │  - Turn 2: User + AI                       │     │
│  │  - Turn 3: User + AI                       │     │
│  │  ...                                        │     │
│  └──────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
```

### Code Flow

1. **Loading Memory** (`temporal_core.py` → `_generate_response()`)
   ```python
   # Retrieve recent conversation memories
   history_result = await self.memory_core.execute_command(
       "search_memories",
       {
           "query": {"tags": ["conversation", "recent"]},
           "max_results": 5,
           "access_level": "owner_root"
       }
   )
   ```

2. **Including Context in Prompt**
   ```python
   system_prompt = f"You are AARIA, a personal AI assistant. "
   system_prompt += f"Your personality: [traits]"
   system_prompt += conversation_history  # Recent turns appended
   ```

3. **Storing Conversation** 
   ```python
   await self.memory_core.execute_command(
       "store_memory",
       {
           "data": {
               "user_message": user_input,
               "ai_response": llm_response.text,
               "timestamp": datetime.now().isoformat(),
               "intent": intent
           },
           "tags": ["conversation", "recent", f"intent_{intent}"],
           "tier": "owner_confidential"
       }
   )
   ```

## Configuration

### Automatic Setup

Memory integration is **automatically enabled** when AARIA boots:

```python
# In stem.py
self.temporal.neural_network.set_memory_core(self.memory)
logger.info("Temporal Core connected to Memory Core for conversation persistence")
```

No additional configuration required!

### Memory Retention Policy

Default retention (configurable in `memory_core.py`):
- **Owner Confidential Data**: Permanent
- **Privileged Data**: 90 days
- **Public Data**: 30 days
- **Temporal Cache**: 7 days

Conversation data is stored as "Owner Confidential" and persists permanently.

## Benefits

### 1. **True Continuity**
```
Session 1:
You: My name is John
AARIA: Nice to meet you, John!

[System restart, switch from Ollama to Gemini]

Session 2:
You: What's my name?
AARIA: Your name is John! [Retrieved from memory]
```

### 2. **Context Across Conversations**
- AARIA remembers previous topics
- Can reference past discussions
- Maintains long-term relationships

### 3. **LLM Flexibility**
- Switch between Ollama (local) and cloud LLMs without losing context
- Experiment with different models while keeping history
- Upgrade models without data loss

### 4. **Privacy & Security**
- All memories encrypted with AES-256-GCM
- Biometric-derived encryption keys
- Data never leaves local system (except LLM API calls)

## Usage Examples

### Example 1: Name Persistence
```
You: Hi, I'm Sarah
AARIA: Hello Sarah! How can I help you today?

[Later, after restart]
You: Do you remember me?
AARIA: Yes, you're Sarah! What can I help you with?
```

### Example 2: Topic Continuity
```
You: I'm working on a Python project
AARIA: That's great! What kind of Python project?

You: It's a web scraper
AARIA: Web scraping with Python is powerful. Are you using BeautifulSoup?

[Later conversation]
You: Remember that project I mentioned?
AARIA: Yes, your Python web scraper! How's it going?
```

### Example 3: LLM Switching
```
# Using Ollama
You: I prefer spicy food
AARIA: [via Ollama] Good to know! I'll remember that.

# Switch to Gemini in llm.env
You: What kind of food do I like?
AARIA: [via Gemini] You mentioned you prefer spicy food!
```

## Memory Storage Format

### Conversation Turn Structure
```json
{
  "memory_id": "uuid-1234-5678",
  "tier": "owner_confidential",
  "data": {
    "user_message": "What's the weather?",
    "ai_response": "I don't have access to weather data, but...",
    "timestamp": "2025-12-07T18:00:00",
    "intent": "question"
  },
  "tags": ["conversation", "recent", "intent_question"],
  "metadata": {
    "type": "conversation_turn",
    "llm_provider": "local_ollama"
  },
  "created_at": "2025-12-07T18:00:00",
  "encryption_tier": "owner_confidential"
}
```

## Troubleshooting

### Memory Not Persisting

**Check 1: Memory Core initialized**
```bash
# Look for this in logs:
INFO - Memory Core started successfully
INFO - Temporal Core connected to Memory Core for conversation persistence
```

**Check 2: Database permissions**
```bash
ls -la Backend/.aaria_config.db
# Should be readable/writable
```

### Too Much History in Context

**Adjust history limit** in `temporal_core.py`:
```python
# Change limit from 5 to 3 for shorter context
"limit": 3,  # Number of recent conversation turns to load
```

### Clear Old Conversations

Memory Core will automatically manage retention based on policy. To manually clear:
```python
# In future updates, a clear_old_memories command will be available
```

## Future Enhancements

Planned improvements:
- [ ] Semantic search for relevant past conversations
- [ ] Identity profiles (remember details about people AARIA talks to)
- [ ] Topic-based memory clustering
- [ ] Memory summarization for very long conversations
- [ ] Selective memory forgetting based on importance
- [ ] Cross-device memory synchronization

## Technical Details

### Files Modified
- `temporal_core.py`: Added memory_core reference and integration
- `stem.py`: Connected Temporal Core to Memory Core

### Dependencies
- Existing Memory Core (already present)
- No new dependencies required

### Performance Impact
- Minimal: 1-2 memory lookups per conversation turn
- Encrypted storage operations are async
- Conversation history cached in memory

## Validation

Run the test suite:
```bash
cd Backend
python test_memory_integration.py
```

Expected output:
```
✓ Memory Integration Tests Passed

📋 Summary:
  • TemporalNeuralNetwork has memory_core reference
  • set_memory_core() method available
  • _generate_response() includes memory operations
  • Conversation history can be loaded and stored

🎯 Integration Complete:
  • AARIA will now remember conversations
  • Memories persist across sessions
  • LLM receives conversation context
  • Works with any LLM backend
```

---

**Status**: ✅ **IMPLEMENTED AND TESTED**

AARIA now has true memory persistence, creating a coherent "hive mind" that maintains context across sessions and LLM providers!
