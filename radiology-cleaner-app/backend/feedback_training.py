import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import threading
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class FeedbackTrainingManager:
    """Manages user feedback for active learning and model improvement"""
    
    def __init__(self, db_path: str = "radiology_cleaner.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_feedback_tables()
        
    def _init_feedback_tables(self):
        """Initialize feedback and training tables"""
        with sqlite3.connect(self.db_path) as conn:
            # User feedback table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_id TEXT,
                    organization TEXT,
                    original_exam_name TEXT NOT NULL,
                    original_modality TEXT,
                    predicted_clean_name TEXT NOT NULL,
                    predicted_confidence REAL,
                    feedback_type TEXT NOT NULL, -- 'correct', 'incorrect', 'suggestion'
                    corrected_clean_name TEXT,
                    user_confidence TEXT, -- 'high', 'medium', 'low'
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    processing_notes TEXT
                )
            ''')
            
            # Training patterns derived from feedback
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL, -- 'exact_match', 'fuzzy_pattern', 'organization_specific'
                    source_organization TEXT,
                    input_pattern TEXT NOT NULL,
                    target_nhs_name TEXT NOT NULL,
                    confidence_score REAL,
                    feedback_count INTEGER DEFAULT 1,
                    success_rate REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Organization-specific mappings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS organization_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization TEXT NOT NULL,
                    exam_code TEXT,
                    exam_name TEXT NOT NULL,
                    modality_code TEXT,
                    nhs_clean_name TEXT NOT NULL,
                    confidence_score REAL,
                    feedback_based BOOLEAN DEFAULT TRUE,
                    verified_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(organization, exam_name, modality_code)
                )
            ''')
            
            # Pattern performance tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pattern_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    input_text TEXT,
                    predicted_output TEXT,
                    user_feedback TEXT, -- 'correct', 'incorrect'
                    FOREIGN KEY (pattern_id) REFERENCES learned_patterns (id)
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_feedback_exam ON user_feedback(original_exam_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_patterns_input ON learned_patterns(input_pattern)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_org_mappings ON organization_mappings(organization, exam_name)')

    def submit_user_feedback(self, feedback_data: Dict) -> int:
        """Submit user feedback for a mapping result"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO user_feedback (
                    session_id, user_id, organization, original_exam_name, 
                    original_modality, predicted_clean_name, predicted_confidence,
                    feedback_type, corrected_clean_name, user_confidence, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                feedback_data.get('session_id'),
                feedback_data.get('user_id'),
                feedback_data.get('organization'),
                feedback_data['original_exam_name'],
                feedback_data.get('original_modality'),
                feedback_data['predicted_clean_name'],
                feedback_data.get('predicted_confidence'),
                feedback_data['feedback_type'],
                feedback_data.get('corrected_clean_name'),
                feedback_data.get('user_confidence'),
                feedback_data.get('notes')
            ))
            feedback_id = cursor.lastrowid
            
        # Process feedback immediately for high-confidence corrections
        if (feedback_data['feedback_type'] == 'incorrect' and 
            feedback_data.get('user_confidence') == 'high'):
            self._process_feedback_immediately(feedback_id)
            
        return feedback_id

    def _process_feedback_immediately(self, feedback_id: int):
        """Process high-confidence feedback immediately"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM user_feedback WHERE id = ? AND processed = FALSE
            ''', (feedback_id,))
            
            feedback = cursor.fetchone()
            if not feedback:
                return
                
            if feedback[8] == 'incorrect' and feedback[10]:  # feedback_type and corrected_clean_name
                # Create organization-specific mapping
                self._create_organization_mapping(
                    organization=feedback[3],
                    exam_name=feedback[4],
                    modality_code=feedback[5],
                    nhs_clean_name=feedback[10],
                    confidence_score=0.9 if feedback[11] == 'high' else 0.7
                )
                
                # Create learned pattern
                self._create_learned_pattern(
                    pattern_type='exact_match',
                    source_organization=feedback[3],
                    input_pattern=feedback[4],
                    target_nhs_name=feedback[10],
                    confidence_score=0.9 if feedback[11] == 'high' else 0.7
                )
                
                # Mark as processed
                conn.execute('''
                    UPDATE user_feedback SET processed = TRUE, 
                    processing_notes = 'Auto-processed: high confidence correction'
                    WHERE id = ?
                ''', (feedback_id,))

    def _create_organization_mapping(self, organization: str, exam_name: str, 
                                   modality_code: str, nhs_clean_name: str, 
                                   confidence_score: float):
        """Create or update organization-specific mapping"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO organization_mappings (
                    organization, exam_name, modality_code, nhs_clean_name, 
                    confidence_score, verified_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, 
                    COALESCE((SELECT verified_count + 1 FROM organization_mappings 
                             WHERE organization = ? AND exam_name = ? AND modality_code = ?), 1),
                    CURRENT_TIMESTAMP)
            ''', (organization, exam_name, modality_code, nhs_clean_name, confidence_score,
                  organization, exam_name, modality_code))

    def _create_learned_pattern(self, pattern_type: str, source_organization: str,
                              input_pattern: str, target_nhs_name: str, 
                              confidence_score: float):
        """Create learned pattern from feedback"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO learned_patterns (
                    pattern_type, source_organization, input_pattern, 
                    target_nhs_name, confidence_score, feedback_count, last_used
                ) VALUES (?, ?, ?, ?, ?, 
                    COALESCE((SELECT feedback_count + 1 FROM learned_patterns 
                             WHERE input_pattern = ? AND target_nhs_name = ?), 1),
                    CURRENT_TIMESTAMP)
            ''', (pattern_type, source_organization, input_pattern, target_nhs_name, 
                  confidence_score, input_pattern, target_nhs_name))

    def get_organization_mapping(self, organization: str, exam_name: str, 
                               modality_code: str) -> Optional[Dict]:
        """Get organization-specific mapping if exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM organization_mappings 
                WHERE organization = ? AND exam_name = ? AND modality_code = ?
                AND verified_count >= 2  -- Require at least 2 confirmations
                ORDER BY confidence_score DESC, verified_count DESC
                LIMIT 1
            ''', (organization, exam_name, modality_code))
            
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_learned_patterns(self, input_text: str, threshold: float = 0.7) -> List[Dict]:
        """Get learned patterns that match input text"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Exact matches first
            cursor = conn.execute('''
                SELECT * FROM learned_patterns 
                WHERE input_pattern = ? AND active = TRUE AND confidence_score >= ?
                ORDER BY confidence_score DESC, feedback_count DESC
            ''', (input_text, threshold))
            
            exact_matches = [dict(row) for row in cursor.fetchall()]
            
            # Fuzzy matches (basic - can be enhanced)
            cursor = conn.execute('''
                SELECT * FROM learned_patterns 
                WHERE input_pattern LIKE ? AND active = TRUE AND confidence_score >= ?
                ORDER BY confidence_score DESC, feedback_count DESC
                LIMIT 5
            ''', (f'%{input_text}%', threshold - 0.2))
            
            fuzzy_matches = [dict(row) for row in cursor.fetchall()]
            
            return exact_matches + fuzzy_matches

    def get_feedback_stats(self, days: int = 30) -> Dict:
        """Get feedback statistics for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    feedback_type,
                    COUNT(*) as count,
                    AVG(CASE WHEN predicted_confidence IS NOT NULL THEN predicted_confidence END) as avg_confidence
                FROM user_feedback 
                WHERE created_at > datetime('now', '-{} days')
                GROUP BY feedback_type
            '''.format(days))
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    'count': row[1],
                    'avg_confidence': row[2]
                }
            
            # Overall statistics
            cursor = conn.execute('''
                SELECT COUNT(*) as total_feedback,
                       SUM(CASE WHEN feedback_type = 'correct' THEN 1 ELSE 0 END) as correct_count,
                       COUNT(DISTINCT organization) as organizations_count
                FROM user_feedback 
                WHERE created_at > datetime('now', '-{} days')
            '''.format(days))
            
            overall = cursor.fetchone()
            stats['overall'] = {
                'total_feedback': overall[0],
                'accuracy_rate': overall[1] / overall[0] if overall[0] > 0 else 0,
                'organizations_providing_feedback': overall[2]
            }
            
            return stats

    def retrain_patterns(self):
        """Retrain patterns based on accumulated feedback"""
        with sqlite3.connect(self.db_path) as conn:
            # Update pattern success rates
            cursor = conn.execute('''
                UPDATE learned_patterns 
                SET success_rate = (
                    SELECT CAST(SUM(CASE WHEN user_feedback = 'correct' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)
                    FROM pattern_performance 
                    WHERE pattern_id = learned_patterns.id
                )
                WHERE id IN (SELECT DISTINCT pattern_id FROM pattern_performance)
            ''')
            
            # Deactivate patterns with low success rates
            conn.execute('''
                UPDATE learned_patterns 
                SET active = FALSE 
                WHERE success_rate < 0.3 AND feedback_count >= 5
            ''')
            
            # Mark processed feedback
            conn.execute('''
                UPDATE user_feedback 
                SET processed = TRUE,
                    processing_notes = 'Processed in batch retraining'
                WHERE processed = FALSE AND feedback_type IN ('correct', 'incorrect')
            ''')

class FeedbackEnhancedPreprocessor:
    """Enhanced preprocessor that learns from user feedback"""
    
    def __init__(self, base_preprocessor, feedback_manager):
        self.base_preprocessor = base_preprocessor
        self.feedback_manager = feedback_manager
    
    def preprocess_exam_name(self, exam_name: str, modality_code: str = None, 
                           organization: str = None) -> Dict:
        """Enhanced preprocessing with feedback-based learning"""
        
        # Step 1: Check for organization-specific mapping
        if organization:
            org_mapping = self.feedback_manager.get_organization_mapping(
                organization, exam_name, modality_code
            )
            if org_mapping:
                return self._create_result_from_org_mapping(org_mapping, exam_name)
        
        # Step 2: Check learned patterns
        learned_patterns = self.feedback_manager.get_learned_patterns(exam_name)
        if learned_patterns:
            best_pattern = learned_patterns[0]
            if best_pattern['confidence_score'] > 0.8:
                return self._create_result_from_pattern(best_pattern, exam_name)
        
        # Step 3: Fall back to base preprocessor
        result = self.base_preprocessor.preprocess_exam_name(exam_name, modality_code)
        
        # Step 4: Add learning metadata
        result['learning_metadata'] = {
            'has_org_mapping': bool(organization and org_mapping),
            'has_learned_patterns': bool(learned_patterns),
            'pattern_confidence': learned_patterns[0]['confidence_score'] if learned_patterns else 0,
            'base_confidence': result.get('confidence', 0)
        }
        
        return result
    
    def _create_result_from_org_mapping(self, org_mapping: Dict, exam_name: str) -> Dict:
        """Create result from organization-specific mapping"""
        return {
            'components': {
                'original': exam_name,
                'modality': org_mapping.get('modality_code'),
                'anatomy': [],  # Can be enhanced
            },
            'best_match': {
                'clean_name': org_mapping['nhs_clean_name'],
                'snomed_data': {}  # Can be looked up from NHS authority
            },
            'confidence': org_mapping['confidence_score'],
            'source': 'organization_mapping',
            'verified_count': org_mapping['verified_count']
        }
    
    def _create_result_from_pattern(self, pattern: Dict, exam_name: str) -> Dict:
        """Create result from learned pattern"""
        return {
            'components': {
                'original': exam_name,
                'modality': None,  # Extract from pattern if needed
                'anatomy': [],
            },
            'best_match': {
                'clean_name': pattern['target_nhs_name'],
                'snomed_data': {}
            },
            'confidence': pattern['confidence_score'],
            'source': 'learned_pattern',
            'pattern_type': pattern['pattern_type'],
            'feedback_count': pattern['feedback_count']
        }