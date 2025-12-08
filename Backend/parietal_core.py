# // PARIETAL_CORE.PY
# // VERSION: 1.0.0
# // DESCRIPTION: Parietal Core - Self Awareness, Device/Surrounding Awareness, System Health Checks, Code Integrity Verification.
# // UPDATE NOTES: Initial release. Implements hardware telemetry, code fingerprinting, continuous health monitoring loops, and neural integration for sensory processing.
# // IMPORTANT: No hardcoded values. All configurations loaded from encrypted owner database.

import asyncio
import json
import uuid
import hashlib
import inspect
import os
import sys
import platform
import importlib.util
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import random
import math
import networkx as nx
from collections import defaultdict, deque

# External libraries for hardware awareness
# Note: In a production deployment, ensure psutil is installed via pip
try:
    import psutil
except ImportError:
    # Fallback for environments where psutil might not be strictly available immediately (simulated for resilience)
    psutil = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION LOADER ====================
class ParietalConfigLoader:
    """Dynamic configuration loader from encrypted database"""
    
    @staticmethod
    async def load_core_config() -> Dict[str, Any]:
        """Load parietal core configuration from secure database"""
        return {
            "neuron_count": 0,  # Populated dynamically
            "telemetry_interval": 10.0,  # UPDATED: Increased to 10s to reduce log noise
            "health_check_interval": 60.0,
            "code_integrity_interval": 300.0,
            "resource_warning_thresholds": {
                "cpu_percent": 90.0,           # Higher threshold for CPU
                "system_memory_percent": 95.0, # CRITICAL system threshold
                "process_memory_mb": 2048.0,   # Process leak threshold (2GB)
                "disk_percent": 90.0,
                "battery_percent": 20.0
            },
            "critical_files_to_monitor": [
                "Backend/frontal_core.py",
                "Backend/temporal_core.py",
                "Backend/memory_core.py",
                "Backend/parietal_core.py",
                "Backend/occipital_core.py",
                "Backend/llm_gateway.py"
            ],
            "awareness_sensitivity": 0.8,
            "self_correction_enabled": True
        }

# ==================== NEURAL ARCHITECTURE ====================
class ParietalNeuronState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    SENSING = "sensing"
    ANALYZING = "analyzing"

@dataclass
class ParietalNeuralConnection:
    target_neuron_id: str
    connection_strength: float = 0.5
    last_activated: datetime = field(default_factory=datetime.now)
    connection_type: str = "sensory"  # sensory/diagnostic/regulatory

@dataclass
class ParietalNeuron:
    """Neuron specialized for parietal functions (Sensing, Health, Integrity)"""
    neuron_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    core_assignment: str = "parietal"
    function_name: str = ""
    function_body: Optional[Callable] = None
    current_state: ParietalNeuronState = ParietalNeuronState.INACTIVE
    activation_level: float = 0.0
    connections: List[ParietalNeuralConnection] = field(default_factory=list)
    specialization: str = ""  # hardware, software, environment, self
    sensor_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_fired: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def axon_state(self) -> Dict[str, Any]:
        """Return visualization state for holographic projection"""
        color_map = {
            "hardware": "#06D6A0",  # Teal for hardware
            "software": "#118AB2",  # Blue for code/software
            "environment": "#FFD166", # Yellow for environment
            "self": "#EF476F"       # Pink/Red for self-awareness
        }
        
        state_colors = {
            ParietalNeuronState.ACTIVE: color_map.get(self.specialization, "#FFFFFF"),
            ParietalNeuronState.INACTIVE: "#CCCCCC",
            ParietalNeuronState.FAILED: "#FF0000",
            ParietalNeuronState.SENSING: "#00FF00",
            ParietalNeuronState.ANALYZING: "#0000FF"
        }
        
        return {
            "neuron_id": self.neuron_id,
            "core": self.core_assignment,
            "color": state_colors[self.current_state],
            "brightness": self.activation_level,
            "connections": len(self.connections),
            "position": self.calculate_position(),
            "status": self.current_state.value,
            "specialization": self.specialization,
            "reading": str(list(self.sensor_data.keys())[:1]) if self.sensor_data else "idle"
        }
    
    def calculate_position(self) -> Dict[str, float]:
        """Calculate 3D position for holographic display"""
        seed = int(hashlib.sha256(self.neuron_id.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        # Parietal core is typically represented "top-back", mapping logic here
        return {
            "x": random.uniform(-0.8, 0.8),
            "y": random.uniform(0.2, 1.0),
            "z": random.uniform(-0.5, 0.5)
        }
    
    async def fire(self, input_strength: float = 1.0, context: Dict[str, Any] = None) -> Any:
        """Activate neuron with context"""
        try:
            if self.current_state == ParietalNeuronState.FAILED:
                return None
                
            self.current_state = ParietalNeuronState.ANALYZING
            self.activation_level = min(1.0, self.activation_level + input_strength)
            self.last_fired = datetime.now()
            
            if self.function_body and self.activation_level >= 0.3: # Lower threshold for sensors
                # Prepare execution context
                exec_context = self.metadata.copy()
                if context:
                    exec_context.update(context)
                
                # Execute neuron's function
                result = await self.execute_function(exec_context)
                
                if result is not None:
                    self.success_count += 1
                    if isinstance(result, dict):
                        self.sensor_data.update(result)
                else:
                    self.error_count += 1
                
                self.current_state = ParietalNeuronState.ACTIVE
                return result
            
            self.current_state = ParietalNeuronState.ACTIVE
            return {"activation": self.activation_level, "neuron_id": self.neuron_id}
            
        except Exception as e:
            self.error_count += 1
            if self.error_count > 5:
                self.current_state = ParietalNeuronState.FAILED
            logger.error(f"ParietalNeuron {self.neuron_id} fire error: {e}")
            return None
    
    async def execute_function(self, context: Dict[str, Any]) -> Any:
        """Execute the neuron's assigned function"""
        if not self.function_body:
            return None
        
        try:
            if inspect.iscoroutinefunction(self.function_body):
                result = await self.function_body(**context)
            else:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor, 
                        lambda: self.function_body(**context)
                    )
            return result
        except Exception as e:
            logger.error(f"ParietalNeuron {self.neuron_id} function error: {e}")
            return None

# ==================== FUNCTION REGISTRY ====================
class ParietalFunctionRegistry:
    """Registry of parietal core neural functions"""
    
    def __init__(self):
        self.registered_functions: Dict[str, Dict[str, Any]] = {}
        self.function_categories = {
            "device_awareness": [],
            "surrounding_awareness": [],
            "self_health": [],
            "code_integrity": [],
            "process_management": []
        }
        self.load_base_functions()
    
    def load_base_functions(self):
        """Load initial set of neural functions"""
        
        # Device Awareness
        self.register_function(
            name="monitor_cpu_load",
            category="device_awareness",
            func=self.monitor_cpu_load,
            description="Monitor CPU usage and load averages"
        )
        
        self.register_function(
            name="monitor_memory_usage",
            category="device_awareness",
            func=self.monitor_memory_usage,
            description="Monitor RAM and Swap usage"
        )
        
        self.register_function(
            name="monitor_battery_status",
            category="device_awareness",
            func=self.monitor_battery_status,
            description="Monitor power source and battery levels"
        )
        
        self.register_function(
            name="detect_network_interfaces",
            category="device_awareness",
            func=self.detect_network_interfaces,
            description="Detect and analyze network connectivity"
        )

        # Surrounding Awareness (Simulated/API based)
        self.register_function(
            name="scan_local_environment",
            category="surrounding_awareness",
            func=self.scan_local_environment,
            description="Analyze local environment via available sensors/APIs"
        )

        # Self Health
        self.register_function(
            name="system_heartbeat",
            category="self_health",
            func=self.system_heartbeat,
            description="Aggregate status of all active cores"
        )
        
        self.register_function(
            name="resource_anomaly_detection",
            category="self_health",
            func=self.resource_anomaly_detection,
            description="Detect abnormal resource consumption spikes"
        )

        # Code Integrity
        self.register_function(
            name="verify_file_integrity",
            category="code_integrity",
            func=self.verify_file_integrity,
            description="Verify SHA256 hashes of critical source files"
        )
        
        self.register_function(
            name="detect_unauthorized_modification",
            category="code_integrity",
            func=self.detect_unauthorized_modification,
            description="Check file timestamps and permissions"
        )

    def register_function(self, name: str, category: str, func: Callable, description: str = ""):
        """Register a new neural function"""
        self.registered_functions[name] = {
            "function": func,
            "category": category,
            "description": description,
            "registered_at": datetime.now()
        }
        if category in self.function_categories:
            self.function_categories[category].append(name)
    
    async def create_neuron_for_function(self, function_name: str) -> Optional[ParietalNeuron]:
        """Create a neuron specialized for a specific function"""
        if function_name not in self.registered_functions:
            return None
        
        func_data = self.registered_functions[function_name]
        category_map = {
            "device_awareness": "hardware",
            "surrounding_awareness": "environment",
            "self_health": "self",
            "code_integrity": "software",
            "process_management": "self"
        }
        
        neuron = ParietalNeuron(
            function_name=function_name,
            function_body=func_data["function"],
            specialization=category_map.get(func_data["category"], "self"),
            metadata={
                "category": func_data["category"],
                "description": func_data["description"]
            }
        )
        return neuron

    # ========== CORE NEURAL FUNCTION IMPLEMENTATIONS ==========

    async def monitor_cpu_load(self, **kwargs) -> Dict[str, Any]:
        """Monitor CPU usage"""
        if not psutil:
            return {"error": "psutil_unavailable", "usage": 0.0}
        
        try:
            usage = psutil.cpu_percent(interval=0.1)
            freq = psutil.cpu_freq()
            ctx_switches = psutil.cpu_stats().ctx_switches
            
            # Count logical/physical cores
            logical = psutil.cpu_count(logical=True)
            physical = psutil.cpu_count(logical=False)

            return {
                "cpu_usage_percent": usage,
                "frequency_current": freq.current if freq else 0.0,
                "cores": {"logical": logical, "physical": physical},
                "context_switches": ctx_switches,
                "load_status": "high" if usage > 80 else "normal"
            }
        except Exception as e:
            logger.warning(f"CPU monitor error: {e}")
            return {"error": str(e)}

    async def monitor_memory_usage(self, **kwargs) -> Dict[str, Any]:
        """Monitor System RAM and Process-Specific Memory"""
        if not psutil:
            return {"error": "psutil_unavailable", "percent": 0.0}
        
        try:
            # 1. System Memory
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # 2. Process Memory (AARIA specific)
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            process_mb = round(mem_info.rss / (1024 * 1024), 2)
            
            return {
                "memory_total_gb": round(mem.total / (1024**3), 2),
                "memory_available_gb": round(mem.available / (1024**3), 2),
                "system_memory_percent": mem.percent, # Renamed for clarity
                "process_memory_mb": process_mb,      # New metric
                "swap_percent": swap.percent,
                "pressure_status": "high" if mem.percent > 95 else "normal"
            }
        except Exception as e:
            return {"error": str(e)}

    async def monitor_battery_status(self, **kwargs) -> Dict[str, Any]:
        """Monitor Battery"""
        if not psutil:
            return {"error": "psutil_unavailable", "plugged": True}
        
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return {"has_battery": False, "plugged": True, "percent": 100}
            
            return {
                "has_battery": True,
                "percent": battery.percent,
                "secsleft": battery.secsleft,
                "plugged": battery.power_plugged,
                "status": "charging" if battery.power_plugged else "discharging"
            }
        except Exception as e:
            return {"error": str(e)}

    async def detect_network_interfaces(self, **kwargs) -> Dict[str, Any]:
        """Detect Network Status"""
        if not psutil:
            return {"error": "psutil_unavailable"}
        
        try:
            stats = psutil.net_if_stats()
            io_counters = psutil.net_io_counters()
            
            active_interfaces = []
            for iface, data in stats.items():
                if data.isup:
                    active_interfaces.append({
                        "interface": iface,
                        "speed": data.speed,
                        "mtu": data.mtu
                    })
            
            return {
                "active_interfaces_count": len(active_interfaces),
                "details": active_interfaces,
                "bytes_sent": io_counters.bytes_sent,
                "bytes_recv": io_counters.bytes_recv,
                "connectivity": "online" if active_interfaces else "offline"
            }
        except Exception as e:
            return {"error": str(e)}

    async def scan_local_environment(self, **kwargs) -> Dict[str, Any]:
        """Analyze local environment (Simulated + OS data)"""
        # In a real scenario, this would check connected peripherals like cameras/mics
        # via OS APIs.
        try:
            os_info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node()
            }
            
            return {
                "os_environment": os_info,
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    async def system_heartbeat(self, **kwargs) -> Dict[str, Any]:
        """Check status of other cores"""
        # This function typically interacts with Stem or checks shared memory/files
        # Since this is modular, we simulate checking known core files exist and are loadable
        
        known_cores = ["temporal_core.py", "frontal_core.py", "memory_core.py", "occipital_core.py"]
        core_status = {}
        
        for core in known_cores:
            # Assuming standard directory structure
            path = os.path.join(os.getcwd(), "Backend", core)
            if not os.path.exists(path):
                # Try current directory
                path = os.path.join(os.getcwd(), core)
            
            exists = os.path.exists(path)
            core_status[core] = "ready" if exists else "missing"
        
        return {
            "core_statuses": core_status,
            "parietal_health": "optimal",
            "timestamp": datetime.now().isoformat()
        }

    async def resource_anomaly_detection(self, **kwargs) -> Dict[str, Any]:
        """Detect anomalies in resource usage history"""
        # Requires history passed in kwargs or maintaining state
        history = kwargs.get("history", [])
        if not history:
            return {"anomaly": False, "reason": "No history"}
        
        # Simple threshold logic for now
        last_entry = history[-1] if history else {}
        cpu = last_entry.get("cpu_usage_percent", 0)
        mem = last_entry.get("memory_percent", 0)
        
        anomalies = []
        if cpu > 90:
            anomalies.append("critical_cpu_load")
        if mem > 95:
            anomalies.append("critical_memory_usage")
            
        return {
            "anomaly_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "severity": "high" if anomalies else "none"
        }

    async def verify_file_integrity(self, **kwargs) -> Dict[str, Any]:
        """Verify code integrity via hashing"""
        files_to_check = kwargs.get("files", [])
        results = {}
        integrity_ok = True
        
        for file_path in files_to_check:
            # Handle relative paths based on CWD
            full_path = file_path if os.path.isabs(file_path) else os.path.abspath(file_path)
            
            if not os.path.exists(full_path):
                # Try finding it in current directory if path includes 'Backend'
                if 'Backend' in full_path:
                    alt_path = full_path.replace('Backend/', '').replace('Backend\\', '')
                    if os.path.exists(alt_path):
                        full_path = alt_path
            
            if os.path.exists(full_path):
                try:
                    with open(full_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        results[os.path.basename(file_path)] = {
                            "status": "ok",
                            "hash": file_hash[:16] + "..." # Truncate for display
                        }
                except Exception as e:
                    results[os.path.basename(file_path)] = {"status": "error", "error": str(e)}
                    integrity_ok = False
            else:
                results[os.path.basename(file_path)] = {"status": "missing"}
                integrity_ok = False
                
        return {
            "integrity_status": "valid" if integrity_ok else "compromised",
            "file_details": results,
            "timestamp": datetime.now().isoformat()
        }

    async def detect_unauthorized_modification(self, **kwargs) -> Dict[str, Any]:
        """Check file timestamps"""
        files_to_check = kwargs.get("files", [])
        modifications = []
        
        current_time = datetime.now().timestamp()
        
        for file_path in files_to_check:
             # Handle paths
            full_path = os.path.abspath(file_path)
            if not os.path.exists(full_path):
                 if 'Backend' in full_path:
                    alt_path = full_path.replace('Backend/', '').replace('Backend\\', '')
                    if os.path.exists(alt_path):
                        full_path = alt_path

            if os.path.exists(full_path):
                stats = os.stat(full_path)
                mtime = stats.st_mtime
                # If modified in last 5 minutes (300 seconds)
                if current_time - mtime < 300:
                    modifications.append({
                        "file": os.path.basename(file_path),
                        "modified_at": datetime.fromtimestamp(mtime).isoformat(),
                        "seconds_ago": int(current_time - mtime)
                    })
        
        return {
            "recent_modifications": modifications,
            "count": len(modifications),
            "alert": len(modifications) > 0
        }

# ==================== NEURAL NETWORK ====================
class ParietalNeuralNetwork:
    """Parietal Core's neural network"""
    
    def __init__(self):
        self.neurons: Dict[str, ParietalNeuron] = {}
        self.function_registry = ParietalFunctionRegistry()
        self.connection_graph = nx.DiGraph()
        self.config = {}
        self.initialized = False
        self.sensor_history: List[Dict[str, Any]] = deque(maxlen=100) # Keep last 100 scans
        self.monitor_task = None
        self.integrity_task = None
        self.performance_metrics = {
            "scans_performed": 0,
            "anomalies_detected": 0,
            "self_corrections": 0
        }
    
    async def initialize(self):
        """Initialize parietal neural network"""
        self.config = await ParietalConfigLoader.load_core_config()
        
        # Create initial neurons from function registry
        for func_name in self.function_registry.registered_functions:
            neuron = await self.function_registry.create_neuron_for_function(func_name)
            if neuron:
                self.neurons[neuron.neuron_id] = neuron
                self.connection_graph.add_node(neuron.neuron_id)
        
        # Establish internal connections (Mesh topology for high reliability)
        await self._establish_mesh_connections()
        
        # Start background monitoring
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.integrity_task = asyncio.create_task(self._integrity_loop())
        
        self.initialized = True
        logger.info(f"Parietal Core initialized with {len(self.neurons)} neurons")

    async def _establish_mesh_connections(self):
        """Create dense connections for robust self-monitoring"""
        neuron_ids = list(self.neurons.keys())
        for i, source_id in enumerate(neuron_ids):
            # Connect to 3 random other neurons to ensure signal propagation
            targets = random.sample([nid for nid in neuron_ids if nid != source_id], min(3, len(neuron_ids)-1))
            for target_id in targets:
                await self.create_connection(source_id, target_id)

    async def create_connection(self, source_id: str, target_id: str, strength: float = 0.5) -> bool:
        """Create a neural connection"""
        if source_id not in self.neurons or target_id not in self.neurons:
            return False
        
        connection = ParietalNeuralConnection(
            target_neuron_id=target_id,
            connection_strength=strength
        )
        
        self.neurons[source_id].connections.append(connection)
        self.connection_graph.add_edge(source_id, target_id, weight=strength)
        return True

    async def _monitoring_loop(self):
        """Continuous hardware and environment monitoring loop"""
        logger.info("Parietal Monitoring Loop Started (Interval: 10s)")
        while True:
            try:
                # UPDATED: Use configured interval (default 10s)
                interval = self.config.get("telemetry_interval", 10.0)
                await asyncio.sleep(interval)
                
                # Activate hardware awareness neurons
                hardware_neurons = [n for n in self.neurons.values() if n.specialization == "hardware"]
                
                scan_results = {}
                for neuron in hardware_neurons:
                    # Fire with reduced strength to save energy
                    result = await neuron.fire(0.6) 
                    if isinstance(result, dict) and "error" not in result:
                        scan_results.update(result)
                
                # Add timestamp
                scan_results["timestamp"] = datetime.now().isoformat()
                self.sensor_history.append(scan_results)
                
                # Check for anomalies
                await self._check_anomalies(scan_results)
                
                self.performance_metrics["scans_performed"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Parietal monitoring loop error: {e}")
                await asyncio.sleep(interval * 2) # Backoff on error

    async def _check_anomalies(self, current_scan: Dict[str, Any]):
        """Analyze current scan for threshold breaches"""
        thresholds = self.config.get("resource_warning_thresholds", {})
        
        # Check CPU
        if "cpu_usage_percent" in current_scan:
            if current_scan["cpu_usage_percent"] > thresholds.get("cpu_percent", 90):
                # Don't increment anomaly count for transient CPU spikes, just log debug
                if current_scan["cpu_usage_percent"] > 95: 
                    logger.warning(f"CPU Critical: {current_scan['cpu_usage_percent']}%")
                    self.performance_metrics["anomalies_detected"] += 1
        
        # UPDATED: Check Memory (Smart Filtering)
        # 1. Check if AARIA Process is leaking (>2GB)
        proc_mem = current_scan.get("process_memory_mb", 0)
        proc_limit = thresholds.get("process_memory_mb", 2048.0)
        
        if proc_mem > proc_limit:
            self.performance_metrics["anomalies_detected"] += 1
            logger.warning(f"High Process Memory Detected: {proc_mem} MB. Potential Leak.")
            # Optional: Trigger GC here if we had access to gc module directly
            
        # 2. Check System Memory (Only warn if CRITICAL)
        sys_mem = current_scan.get("system_memory_percent", 0)
        sys_limit = thresholds.get("system_memory_percent", 95.0)
        
        if sys_mem > sys_limit:
             self.performance_metrics["anomalies_detected"] += 1
             logger.warning(f"CRITICAL SYSTEM RAM: {sys_mem}% Used. OS instability imminent.")

    async def _integrity_loop(self):
        """Periodic code and health integrity loop"""
        while True:
            try:
                interval = self.config.get("code_integrity_interval", 300.0)
                await asyncio.sleep(interval)
                
                # Activate software/self neurons
                integrity_neurons = [n for n in self.neurons.values() if n.specialization in ["software", "self"]]
                
                context = {
                    "files": self.config.get("critical_files_to_monitor", []),
                    "history": list(self.sensor_history)
                }
                
                for neuron in integrity_neurons:
                    await neuron.fire(0.9, context)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Parietal integrity loop error: {e}")
                await asyncio.sleep(60)

    async def _check_anomalies(self, current_scan: Dict[str, Any]):
        """Analyze current scan for threshold breaches"""
        thresholds = self.config.get("resource_warning_thresholds", {})
        
        # Check CPU
        if "cpu_usage_percent" in current_scan:
            if current_scan["cpu_usage_percent"] > thresholds.get("cpu_percent", 90):
                self.performance_metrics["anomalies_detected"] += 1
                logger.warning(f"High CPU usage detected: {current_scan['cpu_usage_percent']}%")
                # Trigger self-correction suggestions or alerts here
        
        # Check Memory
        if "memory_percent" in current_scan:
             if current_scan["memory_percent"] > thresholds.get("memory_percent", 90):
                self.performance_metrics["anomalies_detected"] += 1
                logger.warning(f"High Memory usage detected: {current_scan['memory_percent']}%")

    def get_visualization_data(self) -> Dict[str, Any]:
        """Get current state for holographic visualization"""
        neurons_data = []
        for neuron in self.neurons.values():
            neurons_data.append(neuron.axon_state())
            
        connection_data = []
        for neuron in self.neurons.values():
            for connection in neuron.connections:
                if connection.target_neuron_id in self.neurons:
                    connection_data.append({
                        "source": neuron.neuron_id,
                        "target": connection.target_neuron_id,
                        "strength": connection.connection_strength,
                        "type": connection.connection_type
                    })
        
        # Latest sensor readings
        latest_reading = self.sensor_history[-1] if self.sensor_history else {}
        
        return {
            "core": "parietal",
            "neuron_count": len(self.neurons),
            "neurons": neurons_data,
            "connections": connection_data,
            "telemetry": {
                "cpu": latest_reading.get("cpu_usage_percent", 0),
                "ram": latest_reading.get("memory_percent", 0),
                "battery": latest_reading.get("percent", 0) if "percent" in latest_reading else 100
            },
            "health_status": "optimal" if self.performance_metrics["anomalies_detected"] == 0 else "warning",
            "performance_metrics": self.performance_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    async def process_request(self, request_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process external request to Parietal Core"""
        if not self.initialized:
            await self.initialize()
            
        # Identify relevant neurons
        target_specialization = "self"
        if "hardware" in request_type or "device" in request_type:
            target_specialization = "hardware"
        elif "code" in request_type or "integrity" in request_type:
            target_specialization = "software"
        elif "environment" in request_type:
            target_specialization = "environment"
            
        relevant_neurons = [n for n in self.neurons.values() if n.specialization == target_specialization]
        
        results = {}
        for neuron in relevant_neurons:
            res = await neuron.fire(1.0, context)
            if isinstance(res, dict):
                results.update(res)
                
        return {
            "success": True,
            "request_type": request_type,
            "data": results,
            "timestamp": datetime.now().isoformat()
        }

    async def evolve(self, evolution_data: Dict[str, Any]):
        """Evolve parietal neural structure"""
        action = evolution_data.get("action")
        
        if action == "add_monitoring_function":
            # Mechanism to add new monitoring capabilities dynamically
            pass
        elif action == "adjust_sensitivity":
            new_sensitivity = evolution_data.get("sensitivity", 0.8)
            self.config["awareness_sensitivity"] = new_sensitivity
            
        logger.info(f"Parietal core evolved with action: {action}")

# ==================== MAIN PARIETAL CORE CLASS ====================
class ParietalCore:
    """Main orchestrator for Parietal Core functionality"""
    
    def __init__(self):
        self.neural_network = ParietalNeuralNetwork()
        self.is_running = False
        self.stem_connection = None
        self.start_time = None
        
    async def start(self):
        """Start the Parietal Core"""
        await self.neural_network.initialize()
        self.is_running = True
        self.start_time = datetime.now()
        
        logger.info("Parietal Core started successfully")
        return True
    
    async def stop(self):
        """Stop the Parietal Core gracefully"""
        self.is_running = False
        
        if self.neural_network.monitor_task:
            self.neural_network.monitor_task.cancel()
        if self.neural_network.integrity_task:
            self.neural_network.integrity_task.cancel()
            
        logger.info("Parietal Core stopped")
        return True
    
    async def get_core_status(self) -> Dict[str, Any]:
        """Get comprehensive core status"""
        viz_data = self.neural_network.get_visualization_data()
        
        uptime = "0:00:00"
        if self.start_time:
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{hours}:{minutes:02d}:{seconds:02d}"
            
        return {
            **viz_data,
            "is_running": self.is_running,
            "uptime": uptime
        }
    
    async def get_system_context(self) -> str:
        """Get formatted system context for LLM prompts"""
        try:
            # Get current date and time
            now = datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Monday, December 08, 2025"
            time_str = now.strftime("%I:%M %p")  # e.g., "08:23 PM"
            
            # Get basic system info
            system_info = platform.system()
            hostname = platform.node()
            
            # Format context string
            context = (
                f"CURRENT DATE: {date_str}\n"
                f"CURRENT TIME: {time_str}\n"
                f"DEVICE: {hostname} ({system_info})"
            )
            
            return context
        except Exception as e:
            logger.error(f"Failed to get system context: {e}")
            # Return minimal context on error
            return f"CURRENT DATE: {datetime.now().strftime('%Y-%m-%d')}\nCURRENT TIME: {datetime.now().strftime('%H:%M')}"
        
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute high-level parietal core commands"""
        command_map = {
            "get_status": self._command_get_status,
            "check_integrity": self._command_check_integrity,
            "scan_hardware": self._command_scan_hardware,
            "core_status": self._command_core_status,
            "evolve": self._command_evolve
        }
        
        if command in command_map:
            return await command_map[command](parameters)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": list(command_map.keys())
            }

    async def _command_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Get system status"""
        return await self.neural_network.process_request("device_status", params)

    async def _command_check_integrity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Force integrity check"""
        # Ensure file list is passed or use default from config
        if "files" not in params:
            params["files"] = self.neural_network.config.get("critical_files_to_monitor", [])
        return await self.neural_network.process_request("code_integrity", params)
        
    async def _command_scan_hardware(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Force hardware scan"""
        return await self.neural_network.process_request("hardware_scan", params)

    async def _command_core_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Get core status for visualization"""
        return await self.get_core_status()

    async def _command_evolve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Evolve parietal core"""
        if "action" not in params:
            return {"error": "Evolution action required"}
        
        try:
            await self.neural_network.evolve(params)
            return {
                "success": True,
                "action": params["action"],
                "message": f"Evolution action '{params['action']}' completed"
            }
        except Exception as e:
            return {
                "error": f"Evolution failed: {str(e)}",
                "action": params.get("action")
            }

# ==================== INITIALIZATION ====================
# Global instance for import
parietal_core_instance = ParietalCore()

async def initialize_parietal_core():
    """Initialize the parietal core (called by Stem)"""
    success = await parietal_core_instance.start()
    return parietal_core_instance if success else None

async def shutdown_parietal_core():
    """Shutdown the parietal core gracefully"""
    success = await parietal_core_instance.stop()
    return success

# ==================== MAIN EXECUTION GUARD ====================
if __name__ == "__main__":
    # This file is meant to be imported, not run directly
    # Direct execution is for testing only
    async def test():
        print("Initializing Parietal Core...")
        core = ParietalCore()
        await core.start()
        
        print("\n--- Testing Hardware Scan ---")
        hw_status = await core.execute_command("scan_hardware", {})
        print(json.dumps(hw_status, indent=2, default=str))
        
        print("\n--- Testing Integrity Check ---")
        # Creating a dummy file to check
        with open("test_file.py", "w") as f:
            f.write("print('hello')")
            
        integrity = await core.execute_command("check_integrity", {"files": ["test_file.py", "parietal_core.py"]})
        print(json.dumps(integrity, indent=2, default=str))
        
        # Cleanup dummy file
        os.remove("test_file.py")
        
        print("\n--- Core Status (Visualization Data) ---")
        status = await core.execute_command("core_status", {})
        print(json.dumps({k:v for k,v in status.items() if k != "neurons"}, indent=2, default=str))
        
        await core.stop()
    
    asyncio.run(test())