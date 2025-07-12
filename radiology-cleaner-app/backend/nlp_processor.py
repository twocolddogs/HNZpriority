# nlp_processor.py

import spacy
import medspacy
from collections import defaultdict
import logging
from spacy.matcher import Matcher
from gensim.models import KeyedVectors
import numpy as np # Added for vector operations
from typing import Optional # Added for type hinting

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    A dedicated processor for loading the spaCy/medspacy model and extracting
    clinical entities from text. This component is designed to be loaded once
    and reused across requests.
    """
    def __init__(self, model_name="en_core_sci_sm", word_embedding_path=None):
        self.nlp = None
        self.model_name = model_name
        self.matcher = None
        self.word_vectors = None # New attribute for word embeddings
        self.word_embedding_path = word_embedding_path # Path to embedding file
        self._load_model()
        self._load_word_embeddings() # New method call

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
            
            # Set up matcher for rule-based entity extraction
            self.matcher = Matcher(self.nlp.vocab)
            self._add_patterns()
            
            logger.info("NLP Processor initialized successfully.")

        except OSError:
            logger.error(f"Could not load spaCy model '{self.model_name}'.")
            logger.error("Please ensure you have downloaded it by running:")
            logger.error(f"python -m spacy download {self.model_name}")
            self.nlp = None
        except Exception as e:
            logger.error(f"An unexpected error occurred during NLP model loading: {e}")
            self.nlp = None

    def _load_word_embeddings(self):
        """Loads pre-trained word embeddings."""
        if self.word_embedding_path:
            try:
                logger.info(f"Loading word embeddings from: {self.word_embedding_path}...")
                # Assuming a Word2Vec format (e.g., BioWordVec)
                self.word_vectors = KeyedVectors.load_word2vec_format(self.word_embedding_path, binary=False)
                logger.info("Word embeddings loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load word embeddings from {self.word_embedding_path}: {e}")
                self.word_vectors = None
        else:
            logger.info("No word embedding path provided. Semantic similarity will not be used.")

    def get_text_embedding(self, text: str) -> Optional[list]:
        """
        Generates a vector embedding for a given text by averaging word vectors.
        """
        if not self.word_vectors:
            return None

        vectors = []
        # Tokenize the text using spaCy's tokenizer
        doc = self.nlp.make_doc(text.lower())
        for token in doc:
            if token.text in self.word_vectors:
                vectors.append(self.word_vectors[token.text])
        
        if vectors:
            # Average the word vectors to get a sentence/text vector
            return list(np.mean(vectors, axis=0))
        return None

    def calculate_semantic_similarity(self, vec1: list, vec2: list) -> float:
        """Calculates cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        # Convert to numpy arrays for efficient calculation
        n_vec1 = np.array(vec1)
        n_vec2 = np.array(vec2)
        
        # Cosine similarity formula
        similarity = np.dot(n_vec1, n_vec2) / (np.linalg.norm(n_vec1) * np.linalg.norm(n_vec2))
        return float(similarity) # Ensure float return type

    def _add_patterns(self):
        """Add rule-based patterns for medical entity extraction."""
        # Modality patterns
        modality_patterns = [
            [{"LOWER": {"IN": ["ct", "computed", "tomography"]}}],
            [{"LOWER": {"IN": ["mr", "mri", "magnetic", "resonance"]}}],
            [{"LOWER": {"IN": ["xr", "x-ray", "radiography", "plain", "film"]}}],
            [{"LOWER": {"IN": ["us", "ultrasound", "sonography"]}}],
            [{"LOWER": {"IN": ["nm", "nuclear", "medicine"]}}],
            [{"LOWER": {"IN": ["mamm", "mammography", "mammogram"]}}],
            [{"LOWER": {"IN": ["dexa", "dxa", "bone", "density"]}}],
            [{"LOWER": {"IN": ["fluoro", "fluoroscopy"]}}]
        ]
        
        # Contrast patterns
        contrast_patterns = [
            [{"LOWER": {"IN": ["enhanced", "contrast", "iv", "c+", "gadolinium", "gad"]}}],
            [{"LOWER": {"IN": ["unenhanced", "non-contrast", "c-", "plain", "without"]}}],
            [{"TEXT": {"REGEX": r"w/?o|with|w/"}}],
            [{"TEXT": {"REGEX": r"w/o|without"}}]
        ]
        
        # Laterality patterns
        laterality_patterns = [
            [{"LOWER": {"IN": ["left", "lt", "l"]}}],
            [{"LOWER": {"IN": ["right", "rt", "r"]}}],
            [{"LOWER": {"IN": ["bilateral", "bilat", "both"]}}]
        ]
        
        # Anatomy patterns - common radiology anatomy terms
        anatomy_patterns = [
            [{"LOWER": {"IN": ["head", "brain", "skull", "cranium"]}}],
            [{"LOWER": {"IN": ["chest", "thorax", "lung", "lungs"]}}],
            [{"LOWER": {"IN": ["abdomen", "belly", "stomach"]}}],
            [{"LOWER": {"IN": ["pelvis", "pelvic", "hip", "hips"]}}],
            [{"LOWER": {"IN": ["spine", "spinal", "vertebral"]}}],
            [{"LOWER": {"IN": ["cervical", "neck", "c-spine"]}}],
            [{"LOWER": {"IN": ["thoracic", "t-spine", "dorsal"]}}],
            [{"LOWER": {"IN": ["lumbar", "l-spine", "lower"]}}],
            [{"LOWER": {"IN": ["sacral", "sacrum", "coccyx"]}}],
            [{"LOWER": {"IN": ["knee", "knees", "patella"]}}],
            [{"LOWER": {"IN": ["shoulder", "shoulders", "scapula"]}}],
            [{"LOWER": {"IN": ["elbow", "elbows", "forearm"]}}],
            [{"LOWER": {"IN": ["wrist", "wrists", "hand", "hands"]}}],
            [{"LOWER": {"IN": ["ankle", "ankles", "foot", "feet"]}}],
            [{"LOWER": {"IN": ["femur", "tibia", "fibula"]}}],
            [{"LOWER": {"IN": ["radius", "ulna", "humerus"]}}]
        ]
        
        # Add patterns to matcher
        self.matcher.add("MODALITY", modality_patterns)
        self.matcher.add("CONTRAST", contrast_patterns)
        self.matcher.add("LATERALITY", laterality_patterns)
        self.matcher.add("ANATOMY", anatomy_patterns)

    def extract_entities(self, text: str) -> dict:
        """
        Processes a given text and extracts named entities, grouping them by label.
        
        Args:
            text (str): The radiology exam name or text to process.

        Returns:
            dict: A dictionary where keys are entity labels (e.g., 'ANATOMY')
                  and values are lists of the extracted entity texts.
        """
        if not self.nlp or not self.matcher:
            logger.warning("NLP model is not available. Skipping entity extraction.")
            return {}

        doc = self.nlp(text)
        entities = defaultdict(list)
        
        # Extract entities using the medical model (for anatomy primarily)
        model_entities = set()
        for ent in doc.ents:
            model_entities.add(ent.label_)
            # Look for medical/anatomical entities - be more flexible with entity types
            if ent.label_ in ['ANATOMICAL_SYSTEM', 'BODY_SUBSTANCE', 'BODY_PART', 'DIRECTION', 
                             'ORGAN', 'TISSUE', 'CELL', 'ORGANISM_SUBSTANCE']:
                if ent.label_ == 'DIRECTION':
                    entities['LATERALITY'].append(ent.text.lower())
                else:
                    entities['ANATOMY'].append(ent.text.lower())
        
        # Extract entities using rule-based patterns
        matches = self.matcher(doc)
        pattern_entities = set()
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span = doc[start:end]
            pattern_entities.add(label)
            entities[label].append(span.text.lower())
            
        # Log what we found
        found_types = list(model_entities) + list(pattern_entities)
        if found_types:
            logger.info(f"Found entity types in '{text}': model={model_entities}, patterns={pattern_entities}")
        else:
            logger.info(f"No entities found in '{text}'")
        
        # Remove duplicates and return
        for key in entities:
            entities[key] = list(set(entities[key]))
            
        return dict(entities)
