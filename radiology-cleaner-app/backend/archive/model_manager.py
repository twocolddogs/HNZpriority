"""
Model Manager for handling ML model loading and management.
Eliminates circular dependencies and provides centralized model access.
"""

import os
import pickle
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ModelManager:
    """Centralized manager for ML models used in radiology parsing."""
    
    def __init__(self, model_directory: str = None):
        """
        Initialize the ModelManager.
        
        Args:
            model_directory: Directory containing model files. Defaults to current directory.
        """
        self.model_directory = model_directory or os.path.dirname(__file__)
        self.models = {}
        self.model_status = {}
        
    def load_ml_models(self) -> bool:
        """
        Load all ML models from disk.
        
        Returns:
            bool: True if models loaded successfully, False otherwise.
        """
        model_files = {
            'classifier': 'radiology_classifier.pkl',
            'vectorizer': 'radiology_vectorizer.pkl',
            'mlb': 'radiology_mlb.pkl'
        }
        
        all_loaded = True
        
        for model_name, filename in model_files.items():
            try:
                filepath = os.path.join(self.model_directory, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        self.models[model_name] = pickle.load(f)
                    self.model_status[model_name] = 'loaded'
                    logger.info(f"Successfully loaded {model_name} from {filename}")
                else:
                    logger.warning(f"Model file not found: {filepath}")
                    self.models[model_name] = None
                    self.model_status[model_name] = 'missing'
                    all_loaded = False
                    
            except Exception as e:
                logger.error(f"Failed to load {model_name} from {filename}: {e}")
                self.models[model_name] = None
                self.model_status[model_name] = 'error'
                all_loaded = False
        
        return all_loaded
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """
        Get a loaded model by name.
        
        Args:
            model_name: Name of the model to retrieve.
            
        Returns:
            The model object if loaded, None otherwise.
        """
        return self.models.get(model_name)
    
    def get_ml_predictions(self, exam_name: str) -> Optional[Dict[str, Any]]:
        """
        Get ML model predictions for all components.
        
        Args:
            exam_name: The exam name to predict on.
            
        Returns:
            Dictionary of predictions or None if models not available.
        """
        try:
            classifier = self.get_model('classifier')
            vectorizer = self.get_model('vectorizer')
            mlb = self.get_model('mlb')
            
            if not all([classifier, vectorizer, mlb]):
                return None
            
            # Vectorize the exam name
            X = vectorizer.transform([exam_name])
            
            # Get predictions
            predictions = classifier.predict(X)
            
            # Get probabilities if available
            try:
                probabilities = classifier.predict_proba(X)
            except:
                probabilities = None
            
            predicted_labels = mlb.inverse_transform(predictions)[0]
            
            # Organize predictions by category
            ml_predictions = {
                'anatomy': [],
                'modality': [],
                'laterality': None,
                'contrast': None,
                'gender_context': None,
                'confidence_scores': {}
            }
            
            for label in predicted_labels:
                if ':' not in label:
                    continue
                    
                category, value = label.split(':', 1)
                category = category.lower()
                
                if category == 'anatomy':
                    ml_predictions['anatomy'].append(value)
                elif category == 'modality':
                    ml_predictions['modality'].append(value)
                elif category == 'laterality':
                    ml_predictions['laterality'] = value.lower()
                elif category == 'contrast':
                    ml_predictions['contrast'] = value.lower().replace('with', 'with').replace('without', 'without')
                elif category == 'gender':
                    ml_predictions['gender_context'] = value.lower()
            
            return ml_predictions
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            return None
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available and loaded.
        
        Args:
            model_name: Name of the model to check.
            
        Returns:
            bool: True if model is loaded and available.
        """
        return (model_name in self.models and 
                self.models[model_name] is not None and 
                self.model_status.get(model_name) == 'loaded')
    
    def are_ml_models_available(self) -> bool:
        """
        Check if all required ML models are available.
        
        Returns:
            bool: True if all ML models are loaded.
        """
        required_models = ['classifier', 'vectorizer', 'mlb']
        return all(self.is_model_available(model) for model in required_models)
    
    def get_model_status(self) -> Dict[str, str]:
        """
        Get the status of all models.
        
        Returns:
            Dictionary mapping model names to their status.
        """
        return self.model_status.copy()
    
    def reload_models(self) -> bool:
        """
        Reload all models from disk.
        
        Returns:
            bool: True if models reloaded successfully.
        """
        logger.info("Reloading ML models...")
        self.models.clear()
        self.model_status.clear()
        return self.load_ml_models()