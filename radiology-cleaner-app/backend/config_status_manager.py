#!/usr/bin/env python3

import json
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class ConfigStatusManager:
    """Manages the status of config upload and cache rebuild operations."""
    
    def __init__(self):
        self.status_file = Path(__file__).parent / 'config_rebuild_status.json'
        self.lock = threading.Lock()
    
    def set_status(self, status: str, message: str, progress: int = 0, details: Optional[Dict] = None):
        """Update the rebuild status."""
        with self.lock:
            status_data = {
                'status': status,  # 'idle', 'uploading', 'processing', 'rebuilding', 'complete', 'error'
                'message': message,
                'progress': progress,  # 0-100
                'timestamp': datetime.utcnow().isoformat(),
                'details': details or {}
            }
            
            try:
                with open(self.status_file, 'w') as f:
                    json.dump(status_data, f, indent=2)
            except Exception as e:
                print(f"Error writing status file: {e}")
    
    def get_status(self) -> Dict:
        """Get the current rebuild status."""
        with self.lock:
            try:
                if self.status_file.exists():
                    with open(self.status_file, 'r') as f:
                        return json.load(f)
                else:
                    return {
                        'status': 'idle',
                        'message': 'No rebuild in progress',
                        'progress': 0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'details': {}
                    }
            except Exception as e:
                print(f"Error reading status file: {e}")
                return {
                    'status': 'error',
                    'message': f'Error reading status: {e}',
                    'progress': 0,
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': {}
                }
    
    def set_uploading(self):
        """Set status to uploading config."""
        self.set_status('uploading', 'Uploading config.yaml to R2...', 10)
    
    def set_processing(self):
        """Set status to processing config."""
        self.set_status('processing', 'Processing configuration changes...', 20)
    
    def set_rebuilding(self, model_name: str, current: int = 1, total: int = 1):
        """Set status to rebuilding cache."""
        progress = 30 + int((current / total) * 60)  # 30-90% for cache rebuild
        message = f'Rebuilding cache for {model_name} ({current}/{total})...'
        details = {'current_model': model_name, 'models_current': current, 'models_total': total}
        self.set_status('rebuilding', message, progress, details)
    
    def set_complete(self):
        """Set status to complete."""
        self.set_status('complete', 'Cache rebuild complete - App ready to use!', 100)
    
    def set_error(self, error_msg: str):
        """Set status to error."""
        self.set_status('error', f'Error: {error_msg}', 0, {'error': error_msg})
    
    def set_idle(self):
        """Set status back to idle."""
        self.set_status('idle', 'No rebuild in progress', 0)

# Global instance
status_manager = ConfigStatusManager()