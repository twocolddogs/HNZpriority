#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Centralized Configuration Manager for Radiology Cleaner App

This module provides a singleton ConfigManager class that loads configuration
from config.yaml and environment variables, with fallback to sensible defaults.
It serves as a single point of access for all configuration needs across the application.
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Union, List, cast
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Singleton configuration manager that loads settings from config.yaml
    and environment variables, with fallback to sensible defaults.
    """
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance of ConfigManager exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration manager if not already initialized."""
        if self._initialized:
            return
            
        # Initialize configuration dictionary
        self.config: Dict[str, Any] = {}
        
        # Default configuration values
        self.defaults = {
            'api': {
                'port': 10000,
                'host': '0.0.0.0',
                'debug': False,
                'workers': 4
            },
            'preprocessing': {
                'medical_abbreviations': {
                    'abd': 'abdomen',
                    'abdo': 'abdomen',
                    'br': 'breast',
                    'csp': 'cervical spine',
                    'tsp': 'thoracic spine',
                    'lsp': 'lumbar spine',
                    # Add more defaults as needed
                },
                'anatomy_synonyms': {}
            },
            'scoring': {
                'retriever_top_k': 25,
                'weights_component': {
                    'anatomy': 0.35, 
                    'modality': 0.25, 
                    'laterality': 0.15, 
                    'contrast': 0.15, 
                    'technique': 0.10
                },
                'weights_final': {
                    'component': 0.55, 
                    'semantic': 0.35, 
                    'frequency': 0.10
                },
                'interventional_bonus': 0.15,
                'interventional_penalty': -0.20,
                'specificity_penalty_weight': 0.05,
                'exact_match_bonus': 0.25,
                'synonym_match_bonus': 0.15,
                'context_match_bonus': 0.10,
                'contrast_mismatch_score': 0.3,
                'contrast_null_score': 0.7
            },
            'modality_similarity': {
                'CT': {'XA': 0.1},
                'MRI': {'CT': 0.1},
                'XR': {'CT': 0.1, 'Fluoroscopy': 0.3},
                'US': {'MRI': 0.1},
                'NM': {'PET': 0.4},
                'PET': {'NM': 0.4},
                'Fluoroscopy': {'XR': 0.3}
            },
            'context_scoring': {
                'emergency_keywords': ['emergency', 'urgent', 'stat', 'trauma'],
                'emergency_bonus': 0.10,
                'screening_keywords': ['screening', 'routine', 'surveillance'],
                'screening_bonus': 0.10,
                'intervention_keywords': ['biopsy', 'drainage', 'aspiration', 'ablation'],
                'intervention_bonus': 0.15,
                'pregnancy_keywords': ['pregnancy', 'obstetric', 'fetal', 'prenatal'],
                'pregnancy_bonus': 0.10,
                'paediatric_keywords': ['paediatric', 'pediatric', 'child', 'infant', 'neonatal'],
                'paediatric_bonus': 0.10
            },
            'cache': {
                'enabled': True,
                'max_size': 10000,
                'ttl_seconds': 86400,  # 24 hours
                'use_r2': False,
                'r2_bucket': 'radiology-embeddings',
                'r2_region': 'auto'
            },
            'nlp': {
                'default_model': 'default',
                'batch_size': 25,
                'batch_delay': 0.5,
                'timeout': 120,
                'retry_attempts': 3,
                'retry_delay': 2.0
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            }
        }
        
        # Load configuration from file
        self._load_config_file()
        
        # Override with environment variables
        self._load_env_variables()
        
        # Mark as initialized
        self._initialized = True
        logger.info("Configuration manager initialized successfully")
    
    def _load_config_file(self) -> None:
        """Load configuration from config.yaml file."""
        try:
            # Find config.yaml in the current directory or parent directories
            base_dir = Path(__file__).parent
            config_path = base_dir / 'config.yaml'
            
            if not config_path.exists():
                # Try one level up
                config_path = base_dir.parent / 'config.yaml'
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        logger.info(f"Loaded configuration from {config_path}")
                        self.config = loaded_config
                    else:
                        logger.warning(f"Config file {config_path} is empty, using defaults")
                        self.config = self.defaults
            else:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                self.config = self.defaults
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}", exc_info=True)
            logger.warning("Using default configuration values")
            self.config = self.defaults
    
    def _load_env_variables(self) -> None:
        """Override configuration with environment variables."""
        # API configuration
        if port := os.environ.get('API_PORT'):
            self._set_nested_value(['api', 'port'], int(port))
        
        if host := os.environ.get('API_HOST'):
            self._set_nested_value(['api', 'host'], host)
        
        if debug := os.environ.get('API_DEBUG'):
            self._set_nested_value(['api', 'debug'], debug.lower() in ('true', '1', 'yes'))
        
        if workers := os.environ.get('API_WORKERS'):
            self._set_nested_value(['api', 'workers'], int(workers))
        
        # NLP configuration
        if model := os.environ.get('NLP_DEFAULT_MODEL'):
            self._set_nested_value(['nlp', 'default_model'], model)
        
        if batch_size := os.environ.get('NLP_BATCH_SIZE'):
            self._set_nested_value(['nlp', 'batch_size'], int(batch_size))
        
        # Cache configuration
        if cache_enabled := os.environ.get('CACHE_ENABLED'):
            self._set_nested_value(['cache', 'enabled'], cache_enabled.lower() in ('true', '1', 'yes'))
        
        if r2_enabled := os.environ.get('USE_R2_CACHE'):
            self._set_nested_value(['cache', 'use_r2'], r2_enabled.lower() in ('true', '1', 'yes'))
        
        if r2_bucket := os.environ.get('R2_BUCKET'):
            self._set_nested_value(['cache', 'r2_bucket'], r2_bucket)
        
        # Logging configuration
        if log_level := os.environ.get('LOG_LEVEL'):
            self._set_nested_value(['logging', 'level'], log_level)
    
    def _set_nested_value(self, path: List[str], value: Any) -> None:
        """Set a nested value in the configuration dictionary."""
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _get_nested_value(self, path: List[str], default: Any = None) -> Any:
        """Get a nested value from the configuration dictionary."""
        current = self.config
        try:
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError):
            # Check in defaults
            current = self.defaults
            try:
                for key in path:
                    current = current[key]
                return current
            except (KeyError, TypeError):
                return default
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path to the configuration value (e.g., 'api.port')
            default: Default value to return if the path is not found
            
        Returns:
            The configuration value or the default value if not found
        """
        keys = path.split('.')
        return self._get_nested_value(keys, default)
    
    def set(self, path: str, value: Any) -> None:
        """
        Set a configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path to the configuration value (e.g., 'api.port')
            value: Value to set
        """
        keys = path.split('.')
        self._set_nested_value(keys, value)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Name of the configuration section
            
        Returns:
            Dictionary containing the configuration section or empty dict if not found
        """
        result = self.get(section, {})
        if not result and section in self.defaults:
            return self.defaults[section]
        return result
    
    def reload(self) -> None:
        """Reload configuration from file and environment variables."""
        self._load_config_file()
        self._load_env_variables()
        logger.info("Configuration reloaded")
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access to configuration values."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting of configuration values."""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key) is not None


# Create a singleton instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """
    Get the singleton ConfigManager instance.
    
    Returns:
        The ConfigManager instance
    """
    return config
