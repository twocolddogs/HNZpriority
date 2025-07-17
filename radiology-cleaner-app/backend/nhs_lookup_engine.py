# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (R2-INTEGRATED & TUNED)
# =============================================================================
# This version integrates Cloudflare R2 and includes final tuning of the 
# scoring logic to prioritize exact matches and better handle specificity.
# =============================================================================

import json
import logging
import re
import os
import pickle
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
from typing import TYPE_CHECKING

# Core application components
from nlp_processor import NLPProcessor
from context_detection import detect_interventional_procedure_terms
from r2_cache_manager import R2CacheManager
from cache_version import get_current_cache_version

if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser'):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor
        self.semantic_parser = semantic_parser
        
        self.r2_manager = R2CacheManager()
        
        # --- SCORING WEIGHTS (TUNED) ---
        self.weights_component = { 'anatomy': 0.50, 'modality': 0.20, 'laterality': 0.10, 'contrast': 0.10, 'technique': 0.10 }
        self.weights_final = { 'component': 0.6, 'semantic': 0.4 }
        self.interventional_bonus = 0.25
        self.interventional_penalty = -0.50  # Increased penalty
        self.specificity_penalty_weight = 0.10 # Increased penalty
        self.exact_match_bonus = 0.50 # Significant bonus for exact matches
        
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data()
        # Defer embedding loading until specific model is requested
        self._embeddings_loaded = False

        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to', 'is', 'from',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'dexa', 'dect', 'computed', 'tomography',
            'magnetic', 'resonance', 'ultrasound', 'radiograph', 'scan', 'scans', 'imaging', 'image', 'mammo', 'mammogram',
            'left', 'right', 'bilateral', 'lt', 'rt', 'bilat', 'both', 'contrast', 'iv', 'gadolinium', 'gad', 'c+', 'c-',
            'procedure', 'examination', 'study', 'protocol', 'view', 'views', 'projection',
            'series', 'ap', 'pa', 'lat', 'oblique', 'guidance', 'guided', 'body', 'whole',
            'artery', 'vein', 'joint', 'spine', 'tract', 'system', 'time', 'delayed', 'immediate', 'phase', 'early', 'late'
        }
        logger.info("NHSLookupEngine initialized with R2 integration and TUNED component-driven matching.")

    def _load_nhs_data(self):
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries from {self.nhs_json_path}")
        except Exception as e:
            logger.error(f"Failed to load NHS data: {e}", exc_info=True)
            raise

    def _build_lookup_tables(self):
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                self.snomed_lookup[str(snomed_id)] = entry
        logger.info(f"Built SNOMED lookup table with {len(self.snomed_lookup)} entries")

    def _preprocess_and_parse_nhs_data(self):
        if not self.semantic_parser:
            raise RuntimeError("Semantic Parser required for NHS data preprocessing")
        from preprocessing import get_preprocessor
        preprocessor = get_preprocessor()
        if not preprocessor:
            raise RuntimeError("Preprocessor not initialized before NHS engine.")
        
        for entry in self.nhs_data:
            snomed_fsn = entry.get("snomed_fsn", "").strip()
            primary_name = entry.get("primary_source_name", "").strip()
            
            text_to_process = snomed_fsn if snomed_fsn else primary_name
            if not text_to_process: continue

            text_to_process = re.sub(r'\s*\((procedure|qualifier value)\)$', '', text_to_process, flags=re.I).strip()
            preprocessed_text = preprocessor.preprocess(text_to_process)
            entry["_source_text_for_embedding"] = preprocessed_text
            entry["_interventional_terms"] = detect_interventional_procedure_terms(preprocessed_text)
            entry['_parsed_components'] = self.semantic_parser.parse_exam_name(preprocessed_text, 'Other')

    def _get_local_cache_path(self) -> str:
        cache_dir = os.environ.get('RENDER_DISK_PATH', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        model_key = self.nlp_processor.model_key
        data_hash = self._get_data_hash()
        return os.path.join(cache_dir, f'nhs_embeddings_{model_key}_{data_hash}.pkl')
    
    def _get_data_hash(self) -> str:
        """Generate a stable hash based on NHS file content only."""
        # NOTE: We don't include processing file changes (cache_version) for embedding cache
        # because embeddings should only be invalidated when NHS data changes, not processing logic
        # The cache_version tracking is intended for speeding up evaluation runs
        
        # Use file content hash instead of modification time for consistency across environments
        try:
            with open(self.nhs_json_path, 'rb') as f:
                nhs_content = f.read()
            return hashlib.sha256(nhs_content).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Error reading NHS file for hash: {e}")
            # Fallback to a default hash if file reading fails
            return hashlib.sha256(b"nhs_fallback").hexdigest()[:16]

    def _apply_embeddings_to_data(self, embeddings_dict: Dict):
        for entry in self.nhs_data:
            source_text = entry.get("_source_text_for_embedding")
            if source_text in embeddings_dict:
                entry["_embedding"] = embeddings_dict[source_text]
        logger.info(f"Applied {len(embeddings_dict)} embeddings to NHS data.")
        
    def _load_or_compute_embeddings(self, allow_recompute: bool = False):
        model_key = self.nlp_processor.model_key
        data_hash = self._get_data_hash()
        
        if not allow_recompute:
            if self.r2_manager.is_available():
                cache_data = self.r2_manager.download_cache(model_key, data_hash)
                if cache_data:
                    self._apply_embeddings_to_data(cache_data['embeddings'])
                    return
            
            local_cache_path = self._get_local_cache_path()
            if os.path.exists(local_cache_path):
                logger.info(f"Loading cache from local path: {local_cache_path}")
                with open(local_cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                if cache_data.get('cache_metadata', {}).get('data_hash') == data_hash:
                    self._apply_embeddings_to_data(cache_data['embeddings'])
                    if self.r2_manager.is_available() and not self.r2_manager.cache_exists(model_key, data_hash):
                        logger.info("Uploading local cache to R2...")
                        self.r2_manager.upload_cache(cache_data, model_key, data_hash)
                    return

        logger.info(f"No valid cache found for model '{model_key}'. Computing new embeddings...")
        texts_to_embed = [e["_source_text_for_embedding"] for e in self.nhs_data if e.get("_source_text_for_embedding")]
        if not self.nlp_processor.is_available():
            logger.error("Cannot compute embeddings: NLP processor not available.")
            return

        embeddings = self.nlp_processor.batch_get_embeddings(texts_to_embed, chunk_size=50)
        text_to_embedding = dict(zip(texts_to_embed, embeddings))
        
        self._apply_embeddings_to_data(text_to_embedding)

        cache_data = {
            'cache_metadata': {
                'udid': str(uuid.uuid4()),
                'model_key': model_key,
                'hf_model_name': self.nlp_processor.hf_model_name,
                'data_hash': data_hash,
                'created_date': datetime.now(timezone.utc).isoformat(),
                'total_embeddings': len(text_to_embedding)
            },
            'embeddings': text_to_embedding
        }

        local_cache_path = self._get_local_cache_path()
        logger.info(f"Saving new cache to local path: {local_cache_path}")
        with open(local_cache_path, 'wb') as f:
            pickle.dump(cache_data, f)

        if self.r2_manager.is_available():
            logger.info("Uploading new cache to R2...")
            self.r2_manager.upload_cache(cache_data, model_key, data_hash)
        
        logger.info(f"Computed and cached {len(text_to_embedding)} embeddings for model '{model_key}'.")
		
		
    def find_bilateral_peer(self, specific_entry: Dict) -> Optional[Dict]:
        """
        Finds a bilateral peer for a given specific (e.g., 'left' or 'right') entry
        by comparing core parsed components, not raw strings.
        """
        specific_components = specific_entry.get('_parsed_components')
        if not specific_components:
            return None

        # Define the target signature, excluding laterality
        target_modality = specific_components.get('modality')
        target_anatomy = set(specific_components.get('anatomy', []))
        target_contrast = (specific_components.get('contrast') or [None])[0]
        target_techniques = set(specific_components.get('technique', []))

        for entry in self.nhs_data:
            entry_components = entry.get('_parsed_components')
            if not entry_components:
                continue
            
            # 1. Must be a bilateral entry
            entry_laterality = (entry_components.get('laterality') or [None])[0]
            if entry_laterality != 'bilateral':
                continue

            # 2. Compare the core components for a structural match
            if entry_components.get('modality') == target_modality and \
               set(entry_components.get('anatomy', [])) == target_anatomy and \
               (entry_components.get('contrast') or [None])[0] == target_contrast and \
               set(entry_components.get('technique', [])) == target_techniques:
                return entry  # Found a perfect structural peer that is bilateral

        return None

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False) -> Dict:
        model_name = getattr(nlp_proc, 'model_key', 'default').split('/')[-1]
        source_name = f'UNIFIED_MATCH_V14_TUNED_{model_name.upper()}'
        
        detected_interventional_terms = best_match.get('_interventional_terms', [])
        is_interventional = bool(detected_interventional_terms)
        is_diagnostic = not is_interventional

        clean_name = best_match.get('primary_source_name', '')
        if strip_laterality_from_name:
            clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)$', '', clean_name, flags=re.I).strip()
        
        return {
            'clean_name': clean_name,
            'snomed_id': best_match.get('snomed_concept_id', ''),
            'snomed_fsn': best_match.get('snomed_fsn', ''),
            'snomed_laterality_concept_id': best_match.get('snomed_laterality_concept_id', ''),
            'snomed_laterality_fsn': best_match.get('snomed_laterality_fsn', ''),
            'is_diagnostic': is_diagnostic,
            'is_interventional': is_interventional,
            'detected_interventional_terms': detected_interventional_terms,
            'confidence': min(confidence, 1.0),
            'source': source_name,
            'anatomy': extracted_input_components.get('anatomy', []),
            'laterality': extracted_input_components.get('laterality', []),
            'contrast': extracted_input_components.get('contrast', []),
            'modality': extracted_input_components.get('modality', []),
            'technique': extracted_input_components.get('technique', []),
        }

    ### TUNED SCORING FUNCTION ###
    def _calculate_match_score(self, input_exam_text, input_components, nhs_entry, semantic_score, interventional_score, specificity_penalty):
        """Calculates a balanced score based on component and semantic alignment."""
        nhs_components = nhs_entry.get('_parsed_components', {})
        
        # 1. Calculate Anatomy Score (Jaccard Similarity)
        input_anatomy = set(input_components.get('anatomy', []))
        nhs_anatomy = set(nhs_components.get('anatomy', []))
        if not input_anatomy and not nhs_anatomy:
            anatomy_score = 1.0
        elif not input_anatomy and nhs_anatomy:
             anatomy_score = 0.0
        else:
            intersection = len(input_anatomy.intersection(nhs_anatomy))
            union = len(input_anatomy.union(nhs_anatomy))
            anatomy_score = intersection / union if union > 0 else 0.0

        # 2. Calculate other component scores
        modality_score = 1.0 if input_components.get('modality') == nhs_components.get('modality') else 0.0
        
        input_lat = (input_components.get('laterality') or [None])[0]
        nhs_lat = (nhs_components.get('laterality') or [None])[0]
        if input_lat and nhs_lat:
            laterality_score = 1.0 if input_lat == nhs_lat else 0.0
        else:
            laterality_score = 0.5

        input_con = (input_components.get('contrast') or [None])[0]
        nhs_con = (nhs_components.get('contrast') or [None])[0]
        if input_con and nhs_con:
            contrast_score = 1.0 if input_con == nhs_con else 0.0
        elif input_con and not nhs_con: # Penalize if input has contrast but candidate doesn't
            contrast_score = 0.1
        else: # Neutral if input has no contrast or both are unspecified
            contrast_score = 0.5

        input_tech = set(input_components.get('technique', []))
        nhs_tech = set(nhs_components.get('technique', []))
        tech_union = len(input_tech.union(nhs_tech))
        technique_score = len(input_tech.intersection(nhs_tech)) / tech_union if tech_union > 0 else 1.0
        
        # 3. Calculate weighted component score
        component_score = (
            self.weights_component['anatomy'] * anatomy_score +
            self.weights_component['modality'] * modality_score +
            self.weights_component['laterality'] * laterality_score +
            self.weights_component['contrast'] * contrast_score +
            self.weights_component['technique'] * technique_score
        )
        
        # 4. Calculate final balanced score
        final_score = (
            self.weights_final['component'] * component_score +
            self.weights_final['semantic'] * semantic_score
        )
        
        # 5. Apply bonuses and penalties
        final_score += interventional_score
        final_score -= specificity_penalty
        
        # NEW: Add a bonus for an exact match on the primary name
        if input_exam_text.strip().lower() == nhs_entry.get('primary_source_name', '').lower():
            final_score += self.exact_match_bonus
            
        return max(0, final_score)

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        best_match, highest_confidence = None, 0.0
        nlp_proc = custom_nlp_processor or self.nlp_processor

        if not nlp_proc or not nlp_proc.is_available():
            return {'error': 'NLP Processor not available', 'confidence': 0.0}

        # Load embeddings on-demand for the requested model
        if not self._embeddings_loaded or self.nlp_processor.model_key != nlp_proc.model_key:
            logger.info(f"Loading embeddings for model '{nlp_proc.model_key}'...")
            
            # Temporarily swap the processor and load embeddings
            original_processor = self.nlp_processor
            self.nlp_processor = nlp_proc
            
            # Load embeddings for this specific model
            self._load_or_compute_embeddings()
            self._embeddings_loaded = True
            
            logger.info(f"Successfully loaded embeddings for model '{nlp_proc.model_key}'")
        
        input_embedding = nlp_proc.get_text_embedding(input_exam)
        if input_embedding is None:
            return {'error': 'Could not generate input embedding', 'confidence': 0.0}

        input_modality = extracted_input_components.get('modality')
        input_laterality = (extracted_input_components.get('laterality') or [None])[0]
        
        # Main Matching Loop
        for entry in self.nhs_data:
            nhs_embedding = entry.get("_embedding")
            nhs_components = entry.get("_parsed_components")
            if not nhs_components or nhs_embedding is None: continue

            # Gatekeeper Filters
            nhs_modality = nhs_components.get('modality')
            if input_modality and input_modality.lower() != 'other' and nhs_modality and input_modality.lower() != nhs_modality.lower():
                continue

            nhs_laterality = (nhs_components.get('laterality') or [None])[0]
            if input_laterality and nhs_laterality and input_laterality != nhs_laterality:
                continue
                
            # Scoring Logic
            semantic_sim = nlp_proc.calculate_semantic_similarity(input_embedding, nhs_embedding)
            fuzzy_score = fuzz.token_sort_ratio(input_exam.lower(), entry.get("_source_text_for_embedding", "").lower()) / 100.0
            semantic_score = (0.7 * semantic_sim) + (0.3 * fuzzy_score)

            input_interventional_terms = set(detect_interventional_procedure_terms(input_exam))
            nhs_interventional_terms = set(entry.get('_interventional_terms', []))
            interventional_score = 0
            if input_interventional_terms and nhs_interventional_terms:
                interventional_score = self.interventional_bonus
            elif input_interventional_terms and not nhs_interventional_terms:
                interventional_score = self.interventional_penalty
            elif not input_interventional_terms and nhs_interventional_terms:
                interventional_score = self.interventional_penalty / 2
            
            input_tokens = {w for w in input_exam.lower().split() if w not in self._specificity_stop_words}
            nhs_tokens = {w for w in entry.get("_source_text_for_embedding", "").lower().split() if w not in self._specificity_stop_words}
            extra_words_in_nhs = len(nhs_tokens - input_tokens)
            specificity_penalty = extra_words_in_nhs * self.specificity_penalty_weight
            
            current_score = self._calculate_match_score(
                input_exam_text=input_exam,
                input_components=extracted_input_components,
                nhs_entry=entry,
                semantic_score=semantic_score,
                interventional_score=interventional_score,
                specificity_penalty=specificity_penalty
            )
            
            if current_score > highest_confidence:
                highest_confidence, best_match = current_score, entry

        if best_match:
            best_match_parsed = best_match.get('_parsed_components', {})
            match_laterality = best_match_parsed.get('laterality', []) if best_match_parsed else []
            if not input_laterality and match_laterality and match_laterality[0] != 'bilateral':
                bilateral_peer = self.find_bilateral_peer(best_match)
                if bilateral_peer:
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, nlp_proc)
                else:
                    return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=True)
            return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc)
        
        return {'clean_name': input_exam, 'snomed_id': '', 'confidence': 0.0, 'source': 'NO_MATCH'}
        
    def validate_consistency(self):
        snomed_to_primary_names = defaultdict(set)
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                if primary_name := entry.get("primary_source_name"):
                    snomed_to_primary_names[snomed_id].add(primary_name)
        inconsistencies = {k: list(v) for k, v in snomed_to_primary_names.items() if len(v) > 1}
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple primary source names.")
        else:
            logger.info("NHS data consistency validation passed.")

    def requires_redeployment(self):
        # A simple placeholder. A real implementation would compare the
        # current NHS.json hash with a hash stored at startup.
        return False