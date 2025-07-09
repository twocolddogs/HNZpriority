from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import json
import hashlib
from contextlib import contextmanager
import threading
import csv
import io

class DatabaseManager:
    """
    Database manager for caching, feedback, and configuration storage.
    Uses SQLite for simplicity and portability.
    """
    
    def __init__(self, db_path: str = "radiology_cleaner.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            # Cache table for parsed results
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_hash TEXT UNIQUE NOT NULL,
                    input_data TEXT NOT NULL,
                    output_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            ''')
            
            # Feedback table for user corrections
            conn.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    original_exam_name TEXT NOT NULL,
                    original_mapping TEXT NOT NULL,
                    corrected_mapping TEXT NOT NULL,
                    confidence_level TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # General suggestions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS general_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    user_name TEXT,
                    suggestion_text TEXT NOT NULL,
                    confidence_level TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    processed_rules TEXT
                )
            ''')
            
            # Configuration table for settings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS configuration (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Equivalence groups table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS equivalence_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT UNIQUE NOT NULL,
                    canonical_name TEXT NOT NULL,
                    members TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # System comparison results
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comparison_id TEXT UNIQUE NOT NULL,
                    systems TEXT NOT NULL,
                    comparison_results TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance metrics
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    processing_time_ms INTEGER NOT NULL,
                    input_size INTEGER NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_hash ON cache(input_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_feedback_exam ON feedback(original_exam_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_config_key ON configuration(key)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_equiv_group ON equivalence_groups(group_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_comparison_id ON system_comparisons(comparison_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_perf_endpoint ON performance_metrics(endpoint)')

            # SNOMED reference table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS snomed_reference (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snomed_concept_id INTEGER,
                    snomed_fsn TEXT,
                    snomed_laterality_concept_id INTEGER,
                    snomed_laterality_fsn TEXT,
                    is_diagnostic BOOLEAN,
                    is_interventional BOOLEAN,
                    clean_name TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_snomed_clean_name ON snomed_reference(clean_name)')

            # Abbreviations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS abbreviations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    abbreviation TEXT UNIQUE NOT NULL,
                    full_text TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_abbreviation ON abbreviations(abbreviation)')
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper locking."""
        with self.lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def get_cached_result(self, input_data: Dict) -> Optional[Dict]:
        """Get cached parsing result."""
        input_hash = self._hash_input(input_data)
        
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT output_data FROM cache WHERE input_hash = ?',
                (input_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update access statistics
                conn.execute('''
                    UPDATE cache 
                    SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                    WHERE input_hash = ?
                ''', (input_hash,))
                
                return json.loads(row['output_data'])
            
            return None
    
    def cache_result(self, input_data: Dict, output_data: Dict):
        """Cache a parsing result."""
        input_hash = self._hash_input(input_data)
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO cache (input_hash, input_data, output_data)
                VALUES (?, ?, ?)
            ''', (input_hash, json.dumps(input_data), json.dumps(output_data)))
    
    def submit_feedback(self, feedback_data: Dict) -> int:
        """Submit user feedback for correction."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO feedback (
                    user_id, original_exam_name, original_mapping, 
                    corrected_mapping, confidence_level, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                feedback_data.get('user_id'),
                feedback_data['original_exam_name'],
                json.dumps(feedback_data['original_mapping']),
                json.dumps(feedback_data['corrected_mapping']),
                feedback_data['confidence_level'],
                feedback_data.get('notes')
            ))
            return cursor.lastrowid
    
    def submit_general_feedback(self, feedback_data: Dict) -> int:
        """Submit general feedback suggestion."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO general_feedback (
                    user_id, user_name, suggestion_text, confidence_level, category, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                feedback_data.get('user_id'),
                feedback_data.get('user_name'),
                feedback_data['suggestion_text'],
                feedback_data['confidence_level'],
                feedback_data.get('category', 'general'),
                feedback_data.get('notes')
            ))
            return cursor.lastrowid
    
    def get_feedback_data(self, status: str = 'pending') -> List[Dict]:
        """Get feedback data for training."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM feedback WHERE status = ? ORDER BY created_at DESC',
                (status,)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'original_exam_name': row['original_exam_name'],
                    'original_mapping': json.loads(row['original_mapping']),
                    'corrected_mapping': json.loads(row['corrected_mapping']),
                    'confidence_level': row['confidence_level'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'status': row['status']
                })
            
            return results
    
    def get_general_feedback_data(self, status: str = 'pending') -> List[Dict]:
        """Get general feedback suggestions."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM general_feedback WHERE status = ? ORDER BY created_at DESC',
                (status,)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'user_name': row['user_name'],
                    'suggestion_text': row['suggestion_text'],
                    'confidence_level': row['confidence_level'],
                    'category': row['category'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'status': row['status'],
                    'processed_rules': row['processed_rules']
                })
            
            return results
    
    def update_feedback_status(self, feedback_id: int, status: str):
        """Update feedback status after processing."""
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE feedback SET status = ? WHERE id = ?',
                (status, feedback_id)
            )
    
    def get_configuration(self, key: str) -> Optional[str]:
        """Get configuration value."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT value FROM configuration WHERE key = ?',
                (key,)
            )
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def set_configuration(self, key: str, value: str, category: str = 'general'):
        """Set configuration value."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO configuration (key, value, category, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, value, category))
    
    def get_all_configuration(self, category: Optional[str] = None) -> Dict:
        """Get all configuration values."""
        with self.get_connection() as conn:
            if category:
                cursor = conn.execute(
                    'SELECT key, value FROM configuration WHERE category = ?',
                    (category,)
                )
            else:
                cursor = conn.execute('SELECT key, value FROM configuration')
            
            return {row['key']: row['value'] for row in cursor.fetchall()}
    
    def save_equivalence_group(self, group_data: Dict):
        """Save equivalence group."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO equivalence_groups (
                    group_id, canonical_name, members, confidence_score, updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                group_data['group_id'],
                group_data['canonical_name'],
                json.dumps(group_data['members']),
                group_data['confidence_score']
            ))
    
    def get_equivalence_groups(self) -> List[Dict]:
        """Get all equivalence groups."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT group_id, canonical_name, members, confidence_score, updated_at
                FROM equivalence_groups
                ORDER BY confidence_score DESC
            ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'group_id': row['group_id'],
                    'canonical_name': row['canonical_name'],
                    'members': json.loads(row['members']),
                    'confidence_score': row['confidence_score'],
                    'updated_at': row['updated_at']
                })
            
            return results
    
    def save_system_comparison(self, comparison_data: Dict):
        """Save system comparison results."""
        comparison_id = self._generate_comparison_id(comparison_data['systems'])
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO system_comparisons (
                    comparison_id, systems, comparison_results
                ) VALUES (?, ?, ?)
            ''', (
                comparison_id,
                json.dumps(comparison_data['systems']),
                json.dumps(comparison_data['results'])
            ))
    
    def get_system_comparison(self, systems: List[str]) -> Optional[Dict]:
        """Get cached system comparison."""
        comparison_id = self._generate_comparison_id(systems)
        
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT comparison_results FROM system_comparisons WHERE comparison_id = ?',
                (comparison_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['comparison_results'])
            
            return None
    
    def record_performance_metric(self, metric_data: Dict):
        """Record performance metric."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO performance_metrics (
                    endpoint, processing_time_ms, input_size, success, error_message
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                metric_data['endpoint'],
                metric_data['processing_time_ms'],
                metric_data['input_size'],
                metric_data['success'],
                metric_data.get('error_message')
            ))
    
    def get_performance_metrics(self, endpoint: Optional[str] = None, 
                               hours: int = 24) -> List[Dict]:
        """Get performance metrics."""
        with self.get_connection() as conn:
            if endpoint:
                cursor = conn.execute('''
                    SELECT * FROM performance_metrics 
                    WHERE endpoint = ? AND created_at > datetime('now', '-{} hours')
                    ORDER BY created_at DESC
                '''.format(hours), (endpoint,))
            else:
                cursor = conn.execute('''
                    SELECT * FROM performance_metrics 
                    WHERE created_at > datetime('now', '-{} hours')
                    ORDER BY created_at DESC
                '''.format(hours))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'endpoint': row['endpoint'],
                    'processing_time_ms': row['processing_time_ms'],
                    'input_size': row['input_size'],
                    'success': bool(row['success']),
                    'error_message': row['error_message'],
                    'created_at': row['created_at']
                })
            
            return results
    
    def cleanup_old_cache(self, days: int = 30):
        """Clean up old cache entries."""
        with self.get_connection() as conn:
            conn.execute('''
                DELETE FROM cache 
                WHERE last_accessed < datetime('now', '-{} days')
            '''.format(days))
    
    def get_cache_statistics(self) -> Dict:
        """Get cache statistics."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses,
                    MAX(access_count) as max_accesses
                FROM cache
            ''')
            row = cursor.fetchone()
            
            return {
                'total_entries': row['total_entries'],
                'total_accesses': row['total_accesses'],
                'avg_accesses': row['avg_accesses'],
                'max_accesses': row['max_accesses']
            }
    
    def _hash_input(self, input_data: Dict) -> str:
        """Create hash for input data."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def _generate_comparison_id(self, systems: List[str]) -> str:
        """Generate comparison ID from systems list."""
        sorted_systems = sorted(systems)
        systems_str = "|".join(sorted_systems)
        return hashlib.md5(systems_str.encode()).hexdigest()

    def load_snomed_from_csv(self, csv_path: str):
        """Load SNOMED reference data from CSV file."""
        with self.get_connection() as conn:
            # Check if table is already populated
            cursor = conn.execute('SELECT COUNT(*) FROM snomed_reference')
            if cursor.fetchone()[0] > 0:
                print("SNOMED reference table already populated.")
                return

            with open(csv_path, 'r', encoding='utf-8') as f:
                # Clean up header row
                header = [h.strip().replace('\n', '') for h in f.readline().split(',')]
                reader = csv.reader(f)

                for row in reader:
                    if len(row) != len(header):
                        continue
                    # Create a dictionary for easier access
                    row_dict = {header[i]: val for i, val in enumerate(row)}

                    conn.execute('''
                        INSERT INTO snomed_reference (
                            snomed_concept_id, snomed_fsn, snomed_laterality_concept_id, 
                            snomed_laterality_fsn, is_diagnostic, is_interventional, clean_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        int(row_dict.get('"SNOMED CT Concept-ID"', 0)),
                        row_dict.get('SNOMED CT FSN'),
                        int(row_dict.get('SNOMED CT Concept-ID of Laterality', 0)) if row_dict.get('SNOMED CT Concept-ID of Laterality') else None,
                        row_dict.get('SNOMED FSN of Laterality'),
                        True if row_dict.get('Diagnostic procedure') == 'Y' else False,
                        True if row_dict.get('Interventional Procedure') == 'Y' else False,
                        row_dict.get('"Clean Name"')
                    ))
            print("Successfully loaded SNOMED reference data.")

    def get_snomed_code(self, clean_name: str) -> Optional[Dict]:
        """Get SNOMED code for a given clean name."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM snomed_reference WHERE clean_name = ?',
                (clean_name,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_snomed_reference_by_exam_name(self, exam_name: str) -> Optional[Dict]:
        """Get SNOMED reference data for a given exam name."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM snomed_reference WHERE snomed_fsn = ?',
                (exam_name,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def load_abbreviations_from_csv(self, csv_path: str):
        """Load abbreviations from CSV file."""
        with self.get_connection() as conn:
            # Check if table is already populated
            cursor = conn.execute('SELECT COUNT(*) FROM abbreviations')
            if cursor.fetchone()[0] > 0:
                print("Abbreviations table already populated.")
                return

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) # skip header
                next(reader) # skip header
                for row in reader:
                    if row and row[0] and row[1]:
                        conn.execute('''
                            INSERT OR IGNORE INTO abbreviations (abbreviation, full_text)
                            VALUES (?, ?)
                        ''', (row[0].strip(), row[1].strip()))
            print("Successfully loaded abbreviations data.")

    def get_all_abbreviations(self) -> Dict[str, str]:
        """Get all abbreviations from the database."""
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT abbreviation, full_text FROM abbreviations')
            return {row['abbreviation']: row['full_text'] for row in cursor.fetchall()}


class CacheManager:
    """
    In-memory cache manager for high-performance operations.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached value."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Dict):
        """Set cached value."""
        with self.lock:
            # Remove if already exists
            if key in self.cache:
                self.access_order.remove(key)
            
            # Add new entry
            self.cache[key] = value
            self.access_order.append(key)
            
            # Evict if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]
    
    def clear(self):
        """Clear all cached values."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)
    
    def stats(self) -> Dict:
        """Get cache statistics."""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'usage_percent': (len(self.cache) / self.max_size) * 100
            }