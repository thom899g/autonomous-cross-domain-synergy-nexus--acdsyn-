"""
ACDSYN Configuration Management
Centralized configuration with environment-aware settings and validation
"""
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import logging

@dataclass
class FirebaseConfig:
    """Firebase configuration with validation"""
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    
    @classmethod
    def from_env(cls) -> Optional['FirebaseConfig']:
        """Load Firebase config from environment variables"""
        try:
            # In production, use service account JSON
            # For local development, use environment variables
            import json
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            
            if service_account_path and Path(service_account_path).exists():
                with open(service_account_path, 'r') as f:
                    creds = json.load(f)
                    return cls(
                        project_id=creds.get('project_id'),
                        private_key_id=creds.get('private_key_id'),
                        private_key=creds.get('private_key'),
                        client_email=creds.get('client_email'),
                        client_id=creds.get('client_id')
                    )
            
            # Fallback to environment variables
            return cls(
                project_id=os.getenv("FIREBASE_PROJECT_ID", ""),
                private_key_id=os.getenv("FIREBASE_PRIVATE_KEY_ID", ""),
                private_key=os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                client_email=os.getenv("FIREBASE_CLIENT_EMAIL", ""),
                client_id=os.getenv("FIREBASE_CLIENT_ID", "")
            )
        except Exception as e:
            logging.warning(f"Firebase config loading failed: {e}")
            return None

@dataclass
class MLConfig:
    """Machine Learning configuration"""
    synergy_threshold: float = 0.7
    min_samples_per_domain: int = 10
    embedding_dimension: int = 128
    batch_size: int = 32
    learning_rate: float = 0.001
    epochs: int = 100
    
    @property
    def is_valid(self) -> bool:
        """Validate ML configuration"""
        return (
            0 <= self.synergy_threshold <= 1 and
            self.min_samples_per_domain > 0 and
            self.embedding_dimension > 0
        )

@dataclass
class SystemConfig:
    """System-wide configuration"""
    # Execution
    execution_mode: str = "adaptive"  # adaptive, conservative, aggressive
    max_concurrent_tasks: int = 5
    heartbeat_interval: int = 60  # seconds
    
    # Logging
    log_level: str = "INFO"
    log_retention_days: int = 30
    
    # Evolution
    evolution_cycle_hours: int = 24
    mutation_rate: float = 0.1
    survival_threshold: float = 0.8
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        valid_modes = ["adaptive", "conservative", "aggressive"]
        if self.execution_mode not in valid_modes:
            raise ValueError(f"Invalid execution mode. Must be one of {valid_modes}")
        
        if not (0 <= self.mutation_rate <= 1):
            raise ValueError("Mutation rate must be between 0 and 1")

class ConfigManager:
    """Singleton configuration manager"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize configuration from multiple sources"""
        self.firebase = FirebaseConfig.from_env()
        self.ml = MLConfig()
        self.system = SystemConfig()
        
        # Load environment-specific overrides
        self._load_environment_overrides()
    
    def _load_environment_overrides(self):
        """Override config from environment variables"""
        # System overrides
        mode = os.getenv("ACDSYN_EXECUTION_MODE")
        if mode in ["adaptive", "conservative", "aggressive"]:
            self.system.execution_mode = mode
        
        # ML overrides
        threshold = os.getenv("ACDSYN_SYNERGY_THRESHOLD")
        if threshold:
            try:
                self.ml.synergy_threshold = float(threshold)
            except ValueError:
                logging.warning(f"Invalid synergy threshold: {threshold}")
    
    def validate(self) -> bool:
        """Validate entire configuration"""
        try:
            # Check Firebase (optional but recommended)
            if self.firebase is None:
                logging.warning("Firebase configuration not found. Some features will be disabled.")
            
            # Check ML config
            if not self.ml.is_valid:
                logging.error("Invalid ML configuration")
                return False
            
            # Check system config
            self.system.__post_init__()  # This will raise ValueError if invalid
            
            return True
            
        except Exception as e:
            logging.error(f"Configuration validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary"""
        return {
            "firebase": {
                "project_id": self.firebase.project_id if self.firebase else None,
                "client_email": self.firebase.client_email if self.firebase else None
            },
            "ml": {
                "synergy_th