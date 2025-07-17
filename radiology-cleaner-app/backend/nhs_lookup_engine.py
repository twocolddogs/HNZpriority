# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (R2-INTEGRATED VERSION)
# =============================================================================
# This version integrates Cloudflare R2 for persistent, remote caching of
# embeddings, making it suitable for ephemeral build/deployment environments.
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
        
        # Initialize the R2 Cache Manager
        self.r2_manager = R2CacheManager()
        
        # --- SCORING WEIGHTS (from previous correct version) ---
        self.weights_component = { 'anatomy': 0.50, 'modality': 0.20, 'laterality': 0.10, 'contrast': 0.10, 'technique': 0.10 }
        self.weights_final = { 'component': 0.6, 'semantic': 0.4 }
        self.interventional_bonus = 0.25
        self.interventional_penalty = -0.30
        self.specificity_penalty_weight = 0.05
        
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data()
        # This now handles the entire R2/local cache lifecycle
        self._load_or_compute_embeddings()

        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to', 'is', 'from',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'dexa', 'dect', 'computed', 'tomography',
            'magnetic', 'resonance', 'ultrasound', 'radiograph', 'scan', 'scans', 'imaging', 'image', 'mammo', 'mammogram',
            'left', 'right', 'bilateral', 'lt', 'rt', 'bilat', 'both', 'contrast', 'iv', 'gadolinium', 'gad', 'c+', 'c-',
            'procedure', 'examination', 'study', 'protocol', 'view', 'views', 'projection',
            'series', 'ap', 'pa', 'lat', 'oblique', 'guidance', 'guided', 'body', 'whole',
            'artery', 'vein', 'joint', 'spine', 'tract', 'system', 'time', 'delayed', 'immediate', 'phase', 'early', 'late'
        }
        logger.info("NHSLookupEngine initialized with R2 integration and component-driven matching.")

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
        # This function remains the same as the correct previous version
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

            # Fixed regex: use $ instead of comma and fix the pattern
            text_to_process = re.sub(r'\s*\((procedure|qualifier value)\)$', '', text_to_process, flags=re.I).strip()
            preprocessed_text = preprocessor.preprocess(text_to_process)
            entry["_source_text_for_embedding"] = preprocessed_text
            entry["_interventional_terms"] = detect_interventional_procedure_terms(preprocessed_text)
            entry['_parsed_components'] = self.semantic_parser.parse_exam_name(preprocessed_text, 'Other')

    def _get_local_cache_path(self) -> str:
        """Get the path for the LOCAL embeddings cache file."""
        # Use a persistent directory if available (e.g., on Render)
        cache_dir = os.environ.get('RENDER_DISK_PATH', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        # Include model and data hash in the local filename to prevent conflicts
        model_key = self.nlp_processor.model_key
        data_hash = self._get_data_hash()
        return os.path.join(cache_dir, f'nhs_embeddings_{model_key}_{data_hash}.pkl')
    
    def _get_data_hash(self) -> str:
        """Generate hash of the original NHS.json file content."""
        try:
            with open(self.nhs_json_path, 'rb') as f:
                file_content = f.read()
            return hashlib.sha256(file_content).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Failed to hash NHS file {self.nhs_json_path}: {e}")
            # Fallback to data hash (less reliable but better than nothing)
            data_str = json.dumps(self.nhs_data, sort_keys=True, default=str)
            return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _apply_embeddings_to_data(self, embeddings_dict: Dict):
        """Helper to map embeddings from a dictionary to the nhs_data list."""
        for entry in self.nhs_data:
            source_text = entry.get("_source_text_for_embedding")
            if source_text in embeddings_dict:
                entry["_embedding"] = embeddings_dict[source_text]
        logger.info(f"Applied {len(embeddings_dict)} embeddings to NHS data.")
        
    def _load_or_compute_embeddings(self, allow_recompute: bool = False):
        """
        Manages the embedding cache lifecycle with R2 and local fallback.
        1. Try to download from R2.
        2. If fail, try to load from local disk.
        3. If fail, compute, then upload to R2 and save to local disk.
        """
        model_key = self.nlp_processor.model_key
        data_hash = self._get_data_hash()
        
        # If we are not in a recompute-forcing build step, try loading first.
        if not allow_recompute:
            # 1. Try R2 first (production/staging environment)
            if self.r2_manager.is_available():
                cache_data = self.r2_manager.download_cache(model_key, data_hash)
                if cache_data:
                    self._apply_embeddings_to_data(cache_data['embeddings'])
                    return # Success from R2

            # 2. Try local cache next (local dev or persistent disk)
            local_cache_path = self._get_local_cache_path()
            if os.path.exists(local_cache_path):
                logger.info(f"Loading cache from local path: {local_cache_path}")
                try:
                    with open(local_cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    if cache_data.get('cache_metadata', {}).get('data_hash') == data_hash:
                        self._apply_embeddings_to_data(cache_data['embeddings'])
                        # If R2 is configured but cache was missing, upload it now
                        if self.r2_manager.is_available() and not self.r2_manager.cache_exists(model_key, data_hash):
                            logger.info("Uploading local cache to R2...")
                            self.r2_manager.upload_cache(cache_data, model_key, data_hash)
                        return # Success from local
                except Exception as e:
                    logger.warning(f"Failed to load local cache: {e}")

        # 3. If all else fails (or recompute is forced), compute from scratch
        logger.info(f"No valid cache found for model '{model_key}'. Computing new embeddings...")
        texts_to_embed = [e["_source_text_for_embedding"] for e in self.nhs_data if e.get("_source_text_for_embedding")]
        if not self.nlp_processor.is_available():
            logger.error("Cannot compute embeddings: NLP processor not available.")
            return

        embeddings = self.nlp_processor.batch_get_embeddings(texts_to_embed, chunk_size=50)
        text_to_embedding = dict(zip(texts_to_embed, embeddings))
        
        self._apply_embeddings_to_data(text_to_embedding)

        # 4. Create and save the new cache data
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

        # 5. Save to local disk and upload to R2
        local_cache_path = self._get_local_cache_path()
        logger.info(f"Saving new cache to local path: {local_cache_path}")
        try:
            with open(local_cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to save local cache: {e}")

        if self.r2_manager.is_available():
            logger.info("Uploading new cache to R2...")
            self.r2_manager.upload_cache(cache_data, model_key, data_hash)
        
        logger.info(f"Computed and cached {len(text_to_embedding)} embeddings for model '{model_key}'.")

    def find_bilateral_peer(self, specific_entry: Dict) -> Optional[Dict]:
        primary_name = specific_entry.get("primary_source_name")
        if not primary_name: return None
        base_name_pattern = re.compile(r'\s+(lt|rt|left|right)$', re.IGNORECASE)
        base_name = base_name_pattern.sub('', primary_name).strip()
        bilateral_pattern = re.compile(r'\s+(both|bilateral)$', re.IGNORECASE)
        for entry in self.nhs_data:
            entry_primary_name = entry.get("primary_source_name", "")
            if not bilateral_pattern.search(entry_primary_name): continue
            entry_base_name = bilateral_pattern.sub('', entry_primary_name).strip()
            if base_name.lower() == entry_base_name.lower():
                return entry
        return None

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False) -> Dict:
        model_name = getattr(nlp_proc, 'hf_model_name', 'default').split('/')[-1]
        source_name = f'UNIFIED_MATCH_V13_COMPONENT_{model_name.upper()}'
        
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
    
    def _calculate_match_score(self, input_components, nhs_components, semantic_score, interventional_score, specificity_penalty):
        """Calculates a balanced score based on component and semantic alignment."""
        
        # 1. Calculate Anatomy Score (Jaccard Similarity)
        input_anatomy = set(input_components.get('anatomy', []))
        nhs_anatomy = set(nhs_components.get('anatomy', []))
        if not input_anatomy and not nhs_anatomy:
            anatomy_score = 1.0 # Both have no anatomy specified, this is a match.
        elif not input_anatomy and nhs_anatomy:
             anatomy_score = 0.0 # Input is non-anatomic, but NHS entry is.
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
            laterality_score = 0.5 # No laterality specified on one or both, neutral score

        input_con = (input_components.get('contrast') or [None])[0]
        nhs_con = (nhs_components.get('contrast') or [None])[0]
        if input_con and nhs_con:
            contrast_score = 1.0 if input_con == nhs_con else 0.0
        else:
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
        
        return max(0, final_score)

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        best_match, highest_confidence = None, 0.0
        nlp_proc = custom_nlp_processor or self.nlp_processor

        if not nlp_proc or not nlp_proc.is_available():
            return {'error': 'NLP Processor not available', 'confidence': 0.0}

        # Ensure embeddings are available for the requested model
        if custom_nlp_processor and custom_nlp_processor != self.nlp_processor:
            # If using a different model, load its embeddings
            logger.info(f"Loading embeddings for different model '{nlp_proc.hf_model_name}'...")
            temp_engine = NHSLookupEngine(self.nhs_json_path, custom_nlp_processor, self.semantic_parser)
            # Use the temp engine's embedded data for this request
            nhs_data_to_use = temp_engine.nhs_data
        else:
            # Use the current engine's embedded data
            nhs_data_to_use = self.nhs_data
        
        input_embedding = nlp_proc.get_text_embedding(input_exam)
        if input_embedding is None:
            return {'error': 'Could not generate input embedding', 'confidence': 0.0}

        input_modality = extracted_input_components.get('modality')
        input_laterality = (extracted_input_components.get('laterality') or [None])[0]
        
        # --- Main Matching Loop ---
        for entry in nhs_data_to_use:
            nhs_embedding = entry.get("_embedding")
            nhs_components = entry.get("_parsed_components")
            if not nhs_components or nhs_embedding is None: continue

            # ================================================================
            # GATEKEEPER FILTERS (ESSENTIAL)
            # ================================================================
            nhs_modality = nhs_components.get('modality')
            if input_modality and input_modality.lower() != 'other' and nhs_modality and input_modality.lower() != nhs_modality.lower():
                continue

            nhs_laterality = (nhs_components.get('laterality') or [None])[0]
            if input_laterality and nhs_laterality and input_laterality != nhs_laterality:
                continue
                
            # ================================================================
            # SCORING LOGIC (REVISED)
            # ================================================================
            # 1. Calculate Semantic Score
            semantic_sim = nlp_proc.calculate_semantic_similarity(input_embedding, nhs_embedding)
            fuzzy_score = fuzz.token_sort_ratio(input_exam.lower(), entry.get("_source_text_for_embedding", "").lower()) / 100.0
            semantic_score = (0.7 * semantic_sim) + (0.3 * fuzzy_score)

            # 2. Calculate Interventional Score
            input_interventional_terms = set(detect_interventional_procedure_terms(input_exam))
            nhs_interventional_terms = set(entry.get('_interventional_terms', []))
            interventional_score = 0
            if input_interventional_terms and nhs_interventional_terms:
                interventional_score = self.interventional_bonus
            elif input_interventional_terms and not nhs_interventional_terms:
                interventional_score = self.interventional_penalty
            elif not input_interventional_terms and nhs_interventional_terms:
                interventional_score = self.interventional_penalty / 2 # Less penalty if input is diagnostic but NHS is interventional

            # 3. Calculate Specificity Penalty
            input_tokens = {w for w in input_exam.lower().split() if w not in self._specificity_stop_words}
            nhs_tokens = {w for w in entry.get("_source_text_for_embedding", "").lower().split() if w not in self._specificity_stop_words}
            extra_words_in_nhs = len(nhs_tokens - input_tokens)
            specificity_penalty = extra_words_in_nhs * self.specificity_penalty_weight
            
            # 4. Calculate the final, balanced score
            current_score = self._calculate_match_score(
                input_components=extracted_input_components,
                nhs_components=nhs_components,
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