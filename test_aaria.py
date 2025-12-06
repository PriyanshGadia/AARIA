"""
AARIA - Comprehensive Test Suite v1.0
Tests for all core modules and integration
Update Notes: Initial deployment - Complete functional testing
"""

import pytest
import asyncio
import json
import os
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent / 'Backend'))

# ==================== FRONTAL CORE TESTS ====================
class TestFrontalCore:
    """Test suite for Frontal Core"""
    
    @pytest.mark.asyncio
    async def test_frontal_core_initialization(self):
        """Test frontal core initializes correctly"""
        from frontal_core import FrontalCore
        
        async def mock_verification():
            return True
        
        core = FrontalCore(mock_verification)
        
        assert core.core_id == "frontal_core_v1"
        assert len(core.neurons) > 0
        assert core.learning_enabled == True
    
    @pytest.mark.asyncio
    async def test_frontal_core_neurons(self):
        """Test frontal core neurons are properly connected"""
        from frontal_core import FrontalCore
        
        async def mock_verification():
            return True
        
        core = FrontalCore(mock_verification)
        
        # Check specific neurons exist
        assert "plan_strategic" in core.neurons
        assert "decide_analytical" in core.neurons
        assert "reason_logical" in core.neurons
        
        # Check connections
        strategic_neuron = core.neurons["plan_strategic"]
        assert len(strategic_neuron.connections) > 0
    
    @pytest.mark.asyncio
    async def test_frontal_core_status(self):
        """Test frontal core status retrieval"""
        from frontal_core import FrontalCore
        
        async def mock_verification():
            return True
        
        core = FrontalCore(mock_verification)
        status = await core.get_core_status()
        
        assert status["core_id"] == "frontal_core_v1"
        assert "neuron_count" in status
        assert status["status"] == "operational"

# ==================== MEMORY CORE TESTS ====================
class TestMemoryCore:
    """Test suite for Memory Core"""
    
    @pytest.mark.asyncio
    async def test_memory_core_initialization(self):
        """Test memory core initializes correctly"""
        from memory_core import MemoryCore
        
        async def mock_verification():
            return True
        
        # Use temporary database
        test_db_path = "/tmp/test_memory.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        
        core = MemoryCore(mock_verification, test_db_path)
        
        assert core.core_id == "memory_core_v1"
        assert len(core.neurons) > 0
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    
    @pytest.mark.asyncio
    async def test_encryption_initialization(self):
        """Test encryption system initializes"""
        from memory_core import EncryptionManager
        
        manager = EncryptionManager()
        salt = manager.initialize_encryption("test_passphrase_123")
        
        assert manager.active_cipher is not None
        assert len(salt) == 16
    
    @pytest.mark.asyncio
    async def test_encryption_decrypt_cycle(self):
        """Test encryption and decryption"""
        from memory_core import EncryptionManager
        
        manager = EncryptionManager()
        manager.initialize_encryption("test_passphrase_123")
        
        test_data = {"key": "value", "number": 42}
        encrypted = manager.encrypt_data(test_data)
        decrypted = manager.decrypt_data(encrypted)
        
        assert decrypted == test_data
    
    @pytest.mark.asyncio
    async def test_identity_container_creation(self):
        """Test identity container creation"""
        from memory_core import IdentityContainer, DataClassification
        
        container = IdentityContainer(
            identity_id="test_id_123",
            name="Test Person",
            classification=DataClassification.PRIVILEGED_ACCESS
        )
        
        assert container.identity_id == "test_id_123"
        assert container.name == "Test Person"
        
        # Test serialization
        data_dict = container.to_dict()
        assert "identity_id" in data_dict
        
        # Test deserialization
        restored = IdentityContainer.from_dict(data_dict)
        assert restored.identity_id == container.identity_id

# ==================== TEMPORAL CORE TESTS ====================
class TestTemporalCore:
    """Test suite for Temporal Core"""
    
    @pytest.mark.asyncio
    async def test_temporal_core_initialization(self):
        """Test temporal core initializes correctly"""
        from temporal_core import TemporalCore
        
        async def mock_verification():
            return True
        
        core = TemporalCore(mock_verification)
        
        assert core.core_id == "temporal_core_v1"
        assert len(core.neurons) > 0
        assert core.personality is not None
    
    @pytest.mark.asyncio
    async def test_personality_configuration(self):
        """Test personality configuration"""
        from temporal_core import TemporalCore
        
        async def mock_verification():
            return True
        
        core = TemporalCore(mock_verification)
        
        config = {
            "formality_level": 0.8,
            "verbosity": 0.6,
            "proactivity": 0.9
        }
        
        result = await core.configure_personality(config)
        
        assert result["status"] == "personality_configured"
        assert core.personality.formality_level == 0.8
    
    @pytest.mark.asyncio
    async def test_nlp_processing(self):
        """Test NLP processing"""
        from temporal_core import NaturalLanguageProcessor, PersonalityTraits
        
        personality = PersonalityTraits()
        nlp = NaturalLanguageProcessor(personality)
        
        processed = await nlp.process_input(
            "Can you please schedule a meeting tomorrow?",
            {}
        )
        
        assert "intent" in processed
        assert "entities" in processed
        assert "sentiment" in processed
    
    @pytest.mark.asyncio
    async def test_emotion_detection(self):
        """Test emotional state detection"""
        from temporal_core import TemporalCore
        
        async def mock_verification():
            return True
        
        core = TemporalCore(mock_verification)
        
        # Process urgent message
        result = await core.process_communication(
            "This is urgent! Need help immediately!",
            {}
        )
        
        assert result["status"] == "communication_processed"
        assert "emotional_context" in result

# ==================== STEM TESTS ====================
class TestSTEM:
    """Test suite for STEM integration"""
    
    @pytest.mark.asyncio
    async def test_stem_initialization(self):
        """Test STEM initializes correctly"""
        from stem import STEM
        
        # Use temporary config
        test_config_path = "/tmp/test_aaria_config.json"
        
        stem = STEM(test_config_path)
        
        assert stem.stem_id == "stem_v1"
        assert stem.config_manager is not None
        assert stem.auth_manager is not None
        assert stem.training_pipeline is not None
        
        # Cleanup
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
    
    @pytest.mark.asyncio
    async def test_configuration_management(self):
        """Test configuration manager"""
        from stem import ConfigurationManager
        
        test_config_path = "/tmp/test_config.json"
        
        config = ConfigurationManager(test_config_path)
        
        # Test get
        version = config.get("system.version")
        assert version is not None
        
        # Test set
        config.set("test.value", "test_data")
        assert config.get("test.value") == "test_data"
        
        # Cleanup
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
    
    @pytest.mark.asyncio
    async def test_authentication_system(self):
        """Test authentication manager"""
        from stem import AuthenticationManager, ConfigurationManager
        
        test_config_path = "/tmp/test_auth_config.json"
        config = ConfigurationManager(test_config_path)
        auth = AuthenticationManager(config)
        
        # Test authentication
        credentials = {
            "terminal_type": "private",
            "voiceprint": "test_voiceprint",
            "facial_data": "test_facial"
        }
        
        session = await auth.authenticate(credentials)
        
        assert session.session_id is not None
        assert session.auth_level is not None
        
        # Cleanup
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
    
    @pytest.mark.asyncio
    async def test_training_pipeline(self):
        """Test developmental training pipeline"""
        from stem import DevelopmentalTrainingPipeline, ConfigurationManager
        
        test_config_path = "/tmp/test_training_config.json"
        config = ConfigurationManager(test_config_path)
        pipeline = DevelopmentalTrainingPipeline(config)
        
        # Test skill acquisition
        await pipeline.record_skill_acquisition("basic_responses")
        assert "basic_responses" in pipeline.progress.skills_acquired
        
        # Test metric update
        await pipeline.update_training_metric("accuracy", 0.85)
        assert pipeline.progress.training_metrics["accuracy"] == 0.85
        
        # Test phase assessment
        assessment = await pipeline.assess_phase_completion()
        assert "status" in assessment
        assert "ready_for_next_phase" in assessment
        
        # Cleanup
        if os.path.exists(test_config_path):
            os.remove(test_config_path)

# ==================== INTEGRATION TESTS ====================
class TestIntegration:
    """Integration tests across multiple cores"""
    
    @pytest.mark.asyncio
    async def test_cross_core_data_flow(self):
        """Test data flowing between cores"""
        # This would test actual integration between cores
        # For now, we verify each core can be instantiated
        
        from frontal_core import FrontalCore
        from memory_core import MemoryCore
        from temporal_core import TemporalCore
        
        async def mock_verification():
            return True
        
        frontal = FrontalCore(mock_verification)
        memory = MemoryCore(mock_verification, "/tmp/test_integration.db")
        temporal = TemporalCore(mock_verification)
        
        assert frontal is not None
        assert memory is not None
        assert temporal is not None
        
        # Cleanup
        if os.path.exists("/tmp/test_integration.db"):
            os.remove("/tmp/test_integration.db")

# ==================== SECURITY TESTS ====================
class TestSecurity:
    """Security-focused tests"""
    
    @pytest.mark.asyncio
    async def test_no_hardcoded_credentials(self):
        """Verify no hardcoded credentials exist"""
        # This test reads source files and checks for common credential patterns
        backend_path = Path(__file__).parent / 'Backend'
        
        dangerous_patterns = [
            'password = "',
            'api_key = "',
            'secret = "',
            'token = "'
        ]
        
        for py_file in backend_path.glob('*.py'):
            content = py_file.read_text()
            for pattern in dangerous_patterns:
                # Allow configuration examples but not actual values
                if pattern in content:
                    # Check if it's in a comment or example
                    lines = content.split('\n')
                    for line in lines:
                        if pattern in line and not line.strip().startswith('#'):
                            # Further check - should be None or empty
                            if '= "' in line and not ('None' in line or '= ""' in line or 'encrypted' in line):
                                pytest.fail(f"Potential hardcoded credential in {py_file}: {line}")
    
    @pytest.mark.asyncio
    async def test_encryption_strength(self):
        """Test encryption uses strong algorithms"""
        from memory_core import EncryptionManager
        
        manager = EncryptionManager()
        salt = manager.initialize_encryption("test_pass_12345")
        
        # Verify salt is random and sufficient length
        assert len(salt) >= 16
        
        # Verify encryption works
        test_data = "sensitive data"
        encrypted = manager.encrypt_data(test_data)
        
        # Encrypted should be different from original
        assert encrypted != test_data.encode()
        
        # Should not be easily readable
        assert b"sensitive" not in encrypted

# ==================== RUN ALL TESTS ====================
if __name__ == "__main__":
    print("AARIA Comprehensive Test Suite v1.0")
    print("=" * 50)
    
    # Run pytest with verbose output
    pytest.main([__file__, "-v", "--tb=short", "-s"])
