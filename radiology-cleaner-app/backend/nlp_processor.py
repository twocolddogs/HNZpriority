# nlp_processor.py

import spacy
import medspacy
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    A dedicated processor for loading the spaCy/medspacy model and extracting
    clinical entities from text. This component is designed to be loaded once
    and reused across requests.
    """
    def __init__(self, model_name="en_core_sci_sm"):
        self.nlp = None
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """Loads the spaCy model and adds the medspacy pipeline."""
        try:
            logger.info(f"Loading spaCy model: {self.model_name}...")
            self.nlp = spacy.load(self.model_name)
            logger.info("Model loaded successfully.")
            
            # medspacy provides context analysis (negation, etc.), which can be useful
            # for more advanced parsing in the future.
            logger.info("Adding medspacy context pipe...")
            self.nlp.add_pipe("medspacy_context", config={"rules": "default"})
            logger.info("NLP Processor initialized successfully.")

        except OSError:
            logger.error(f"Could not load spaCy model '{self.model_name}'.")
            logger.error("Please ensure you have downloaded it by running:")
            logger.error(f"python -m spacy download {self.model_name}")
            self.nlp = None
        except Exception as e:
            logger.error(f"An unexpected error occurred during NLP model loading: {e}")
            self.nlp = None

    def extract_entities(self, text: str) -> dict:
        """
        Processes a given text and extracts named entities, grouping them by label.
        
        Args:
            text (str): The radiology exam name or text to process.

        Returns:
            dict: A dictionary where keys are entity labels (e.g., 'ANATOMY')
                  and values are lists of the extracted entity texts.
        """
        if not self.nlp:
            logger.warning("NLP model is not available. Skipping entity extraction.")
            return {}

        doc = self.nlp(text)
        entities = defaultdict(list)
        
        # Log all entity types found for debugging
        all_entity_types = set()
        for ent in doc.ents:
            all_entity_types.add(ent.label_)
            
        if all_entity_types:
            logger.info(f"Found entity types in '{text}': {all_entity_types}")
        else:
            logger.info(f"No entities found in '{text}'")
        
        for ent in doc.ents:
            # We are primarily interested in anatomical and directional entities
            if ent.label_ in ['ANATOMICAL_SYSTEM', 'BODY_SUBSTANCE', 'BODY_PART', 'DIRECTION']:
                # Standardize labels for consistency
                label = 'ANATOMY' if ent.label_ != 'DIRECTION' else 'DIRECTION'
                entities[label].append(ent.text)
                
        return dict(entities)
