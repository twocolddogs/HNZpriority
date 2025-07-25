# --- START OF FILE scalable_training.py ---

# =============================================================================
# SCALABLE TRAINING FRAMEWORK
# =============================================================================
# Comprehensive training system for 15,000+ radiology exam cases with
# progress tracking, chunked processing, and performance optimization

import json
import logging
import sqlite3
import time
import yaml
import os
import gc
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from tqdm import tqdm

# Local imports
from database_models import DatabaseManager
from validation_framework import ValidationFramework
from preprocessing import ExamPreprocessor
from nhs_lookup_engine import NHSLookupEngine
from nlp_processor import NLPProcessor
from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for scalable training."""
    chunk_size: int = 1000
    max_workers: int = 4
    validation_split: float = 0.1
    enable_progress_tracking: bool = True
    memory_cleanup_interval: int = 5000
    checkpoint_interval: int = 2500
    resume_from_checkpoint: bool = True
    experiment_name: str = None
    models_to_train: List[str] = None

@dataclass
class TrainingMetrics:
    """Training performance metrics."""
    total_cases: int = 0
    processed_cases: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    average_confidence: float = 0.0
    processing_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class ScalableTrainingFramework:
    """
    Advanced training framework for processing large-scale radiology datasets.
    
    Features:
    - Chunked processing for memory efficiency
    - Progress tracking with database persistence
    - Checkpoint/resume functionality
    - Multi-threaded processing
    - Comprehensive performance metrics
    - Automatic memory management
    """
    
    def __init__(self, config: TrainingConfig = None, config_path: str = 'config.yaml'):
        """Initialize the training framework."""
        self.config = config or TrainingConfig()
        self.config_path = config_path
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.validation_framework = ValidationFramework(config_path)
        
        # Load system configuration
        self.load_system_config()
        
        # Initialize training state
        self.training_session_id = None
        self.current_checkpoint = 0
        self.metrics = TrainingMetrics()
        
        # Set up logging
        self.setup_training_logging()
        
        logger.info(f"Initialized ScalableTrainingFramework with chunk_size={self.config.chunk_size}")
    
    def load_system_config(self):
        """Load system configuration from YAML."""
        try:
            with open(self.config_path, 'r') as f:
                self.system_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load system config: {e}")
            raise
    
    def setup_training_logging(self):
        """Set up comprehensive logging for training."""
        log_dir = Path("logs/training")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"training_{timestamp}.log"
        
        # Add file handler for training logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Training logs will be written to: {log_file}")
    
    def create_training_tables(self):
        """Create database tables for training tracking."""
        with self.db_manager.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_name TEXT,
                    config_json TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT,
                    total_cases INTEGER,
                    processed_cases INTEGER,
                    success_rate REAL,
                    average_confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS training_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    checkpoint_number INTEGER,
                    cases_processed INTEGER,
                    timestamp TIMESTAMP,
                    metrics_json TEXT,
                    FOREIGN KEY (session_id) REFERENCES training_sessions (id)
                );
                
                CREATE TABLE IF NOT EXISTS training_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    input_exam TEXT,
                    expected_output TEXT,
                    actual_output TEXT,
                    confidence REAL,
                    processing_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    chunk_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES training_sessions (id)
                );
                
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    model_name TEXT,
                    accuracy REAL,
                    precision_score REAL,
                    recall_score REAL,
                    f1_score REAL,
                    processing_speed REAL,
                    memory_usage REAL,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES training_sessions (id)
                );
            """)
        logger.info("Training database tables created/verified")
    
    def load_training_dataset(self, dataset_paths: List[str]) -> Generator[Dict, None, None]:
        """
        Load training dataset from multiple JSON files.
        
        Args:
            dataset_paths: List of paths to training JSON files
            
        Yields:
            Individual training cases
        """
        total_loaded = 0
        
        for path in dataset_paths:
            logger.info(f"Loading dataset from: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for case in data:
                    yield case
                    total_loaded += 1
                    
                logger.info(f"Loaded {len(data)} cases from {path}")
                
            except Exception as e:
                logger.error(f"Failed to load dataset from {path}: {e}")
                continue
        
        logger.info(f"Total cases loaded: {total_loaded}")
    
    def create_training_chunks(self, dataset: Generator[Dict, None, None]) -> Generator[List[Dict], None, None]:
        """
        Create chunks of training data for batch processing.
        
        Args:
            dataset: Generator yielding individual cases
            
        Yields:
            Chunks of training cases
        """
        chunk = []
        
        for case in dataset:
            chunk.append(case)
            
            if len(chunk) >= self.config.chunk_size:
                yield chunk
                chunk = []
        
        # Yield final partial chunk
        if chunk:
            yield chunk
    
    def process_training_chunk(self, chunk: List[Dict], chunk_number: int) -> TrainingMetrics:
        """
        Process a single chunk of training data.
        
        Args:
            chunk: List of training cases
            chunk_number: Current chunk number
            
        Returns:
            Metrics for this chunk
        """
        chunk_metrics = TrainingMetrics()
        chunk_metrics.total_cases = len(chunk)
        
        start_time = time.time()
        
        # Initialize processing components for this chunk
        # V4 Architecture: Initialize retriever and reranker manager for training
        retriever_processor = NLPProcessor(model_key='default')  # BioLORD for retrieval
        from reranker_manager import RerankerManager
        reranker_manager = RerankerManager()  # Manage multiple rerankers
        semantic_parser = RadiologySemanticParser(nlp_processor=retriever_processor)  # Use retriever for parsing
        
        nhs_engine = NHSLookupEngine(
            nhs_json_path='core/NHS.json',
            retriever_processor=retriever_processor,
            reranker_manager=reranker_manager,
            semantic_parser=semantic_parser
        )
        
        logger.info(f"Processing chunk {chunk_number} with {len(chunk)} cases")
        
        # Process cases with progress bar
        for i, case in enumerate(tqdm(chunk, desc=f"Chunk {chunk_number}", leave=False)):
            try:
                # Extract input and expected output
                input_exam = case.get('exam_name', '')
                expected_clean_name = case.get('clean_name', '')
                
                if not input_exam:
                    chunk_metrics.errors.append(f"Missing exam_name in case {i}")
                    continue
                
                # Process the exam
                case_start = time.time()
                result = nhs_engine.find_best_match(input_exam, nlp_processor)
                case_time = time.time() - case_start
                
                # Evaluate result
                actual_clean_name = result.get('clean_name', '')
                confidence = result.get('confidence', 0.0)
                success = bool(actual_clean_name and confidence > 0.5)
                
                if success:
                    chunk_metrics.successful_matches += 1
                else:
                    chunk_metrics.failed_matches += 1
                
                chunk_metrics.processed_cases += 1
                chunk_metrics.average_confidence += confidence
                
                # Store detailed result
                self.store_training_result(
                    input_exam=input_exam,
                    expected_output=expected_clean_name,
                    actual_output=actual_clean_name,
                    confidence=confidence,
                    processing_time=case_time,
                    success=success,
                    chunk_number=chunk_number
                )
                
            except Exception as e:
                error_msg = f"Error processing case {i}: {str(e)}"
                chunk_metrics.errors.append(error_msg)
                logger.warning(error_msg)
                chunk_metrics.failed_matches += 1
        
        # Calculate final metrics
        chunk_metrics.processing_time = time.time() - start_time
        if chunk_metrics.processed_cases > 0:
            chunk_metrics.average_confidence /= chunk_metrics.processed_cases
        
        # Memory cleanup
        del nlp_processor, semantic_parser, nhs_engine
        gc.collect()
        
        logger.info(f"Chunk {chunk_number} completed: {chunk_metrics.successful_matches}/{chunk_metrics.processed_cases} successful")
        
        return chunk_metrics
    
    def store_training_result(self, input_exam: str, expected_output: str, 
                            actual_output: str, confidence: float, 
                            processing_time: float, success: bool, 
                            chunk_number: int, error_message: str = None):
        """Store individual training result in database."""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO training_results 
                (session_id, input_exam, expected_output, actual_output, 
                 confidence, processing_time, success, error_message, chunk_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.training_session_id, input_exam, expected_output, 
                actual_output, confidence, processing_time, success, 
                error_message, chunk_number
            ))
    
    def create_checkpoint(self, chunk_number: int, cumulative_metrics: TrainingMetrics):
        """Create a training checkpoint."""
        metrics_json = json.dumps({
            'total_cases': cumulative_metrics.total_cases,
            'processed_cases': cumulative_metrics.processed_cases,
            'successful_matches': cumulative_metrics.successful_matches,
            'failed_matches': cumulative_metrics.failed_matches,
            'average_confidence': cumulative_metrics.average_confidence,
            'processing_time': cumulative_metrics.processing_time,
            'error_count': len(cumulative_metrics.errors)
        })
        
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO training_checkpoints 
                (session_id, checkpoint_number, cases_processed, timestamp, metrics_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.training_session_id, chunk_number, 
                cumulative_metrics.processed_cases, datetime.now(timezone.utc), metrics_json
            ))
        
        logger.info(f"Checkpoint saved: chunk {chunk_number}, {cumulative_metrics.processed_cases} cases processed")
    
    def resume_from_checkpoint(self) -> Optional[int]:
        """Resume training from the latest checkpoint."""
        if not self.config.resume_from_checkpoint:
            return None
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT checkpoint_number, cases_processed 
                FROM training_checkpoints 
                WHERE session_id = ? 
                ORDER BY checkpoint_number DESC 
                LIMIT 1
            """, (self.training_session_id,))
            
            result = cursor.fetchone()
            if result:
                checkpoint_number, cases_processed = result
                logger.info(f"Resuming from checkpoint {checkpoint_number} with {cases_processed} cases processed")
                return checkpoint_number
        
        return None
    
    def run_validation_on_training_results(self) -> Dict[str, float]:
        """Run validation framework on training results."""
        logger.info("Running validation on training results...")
        
        try:
            # Load sanity test data
            self.validation_framework.load_sanity_test_data()
            
            # Run validation suite
            validation_results = self.validation_framework.run_validation_suite()
            
            # Store validation metrics
            if 'summary' in validation_results:
                summary = validation_results['summary']
                with self.db_manager.get_connection() as conn:
                    conn.execute("""
                        INSERT INTO model_performance 
                        (session_id, model_name, accuracy, processing_speed)
                        VALUES (?, ?, ?, ?)
                    """, (
                        self.training_session_id, 'validation_suite',
                        summary.get('modality_extraction_overall', 0.0),
                        summary.get('overall_preprocessing_consistency', 0.0)
                    ))
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {'error': str(e)}
    
    def train_on_dataset(self, dataset_paths: List[str]) -> TrainingMetrics:
        """
        Main training method for processing the full dataset.
        
        Args:
            dataset_paths: List of paths to training JSON files
            
        Returns:
            Final training metrics
        """
        # Create training session
        self.create_training_tables()
        self.training_session_id = self.create_training_session()
        
        # Check for resume
        resume_chunk = self.resume_from_checkpoint()
        start_chunk = resume_chunk + 1 if resume_chunk else 0
        
        logger.info(f"Starting training on {len(dataset_paths)} files")
        if resume_chunk:
            logger.info(f"Resuming from chunk {start_chunk}")
        
        # Initialize cumulative metrics
        cumulative_metrics = TrainingMetrics()
        
        try:
            # Load dataset and create chunks
            dataset = self.load_training_dataset(dataset_paths)
            chunks = self.create_training_chunks(dataset)
            
            # Process chunks
            chunk_number = 0
            for chunk in chunks:
                chunk_number += 1
                
                # Skip chunks if resuming
                if chunk_number <= start_chunk - 1:
                    continue
                
                logger.info(f"Processing chunk {chunk_number}/{chunk_number} (estimated)")
                
                # Process chunk
                chunk_metrics = self.process_training_chunk(chunk, chunk_number)
                
                # Update cumulative metrics
                cumulative_metrics.total_cases += chunk_metrics.total_cases
                cumulative_metrics.processed_cases += chunk_metrics.processed_cases
                cumulative_metrics.successful_matches += chunk_metrics.successful_matches
                cumulative_metrics.failed_matches += chunk_metrics.failed_matches
                cumulative_metrics.processing_time += chunk_metrics.processing_time
                cumulative_metrics.errors.extend(chunk_metrics.errors)
                
                # Recalculate average confidence
                if cumulative_metrics.processed_cases > 0:
                    cumulative_metrics.average_confidence = (
                        (cumulative_metrics.average_confidence * (cumulative_metrics.processed_cases - chunk_metrics.processed_cases) +
                         chunk_metrics.average_confidence * chunk_metrics.processed_cases) /
                        cumulative_metrics.processed_cases
                    )
                
                # Create checkpoint
                if chunk_number % self.config.checkpoint_interval == 0:
                    self.create_checkpoint(chunk_number, cumulative_metrics)
                
                # Memory cleanup
                if chunk_number % self.config.memory_cleanup_interval == 0:
                    gc.collect()
                    logger.info(f"Memory cleanup after chunk {chunk_number}")
            
            # Final checkpoint
            self.create_checkpoint(chunk_number, cumulative_metrics)
            
            # Run validation
            validation_results = self.run_validation_on_training_results()
            
            # Update training session
            self.complete_training_session(cumulative_metrics, validation_results)
            
            logger.info(f"Training completed: {cumulative_metrics.processed_cases} cases processed")
            logger.info(f"Success rate: {cumulative_metrics.successful_matches/cumulative_metrics.processed_cases:.2%}")
            logger.info(f"Average confidence: {cumulative_metrics.average_confidence:.3f}")
            
            return cumulative_metrics
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.fail_training_session(str(e))
            raise
    
    def create_training_session(self) -> int:
        """Create a new training session record."""
        config_json = json.dumps({
            'chunk_size': self.config.chunk_size,
            'max_workers': self.config.max_workers,
            'validation_split': self.config.validation_split,
            'experiment_name': self.config.experiment_name
        })
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO training_sessions 
                (experiment_name, config_json, start_time, status)
                VALUES (?, ?, ?, ?)
            """, (
                self.config.experiment_name or f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                config_json,
                datetime.now(timezone.utc),
                'running'
            ))
            session_id = cursor.lastrowid
        
        logger.info(f"Created training session {session_id}")
        return session_id
    
    def complete_training_session(self, metrics: TrainingMetrics, validation_results: Dict):
        """Mark training session as completed."""
        success_rate = metrics.successful_matches / metrics.processed_cases if metrics.processed_cases > 0 else 0
        
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                UPDATE training_sessions 
                SET end_time = ?, status = ?, total_cases = ?, 
                    processed_cases = ?, success_rate = ?, average_confidence = ?
                WHERE id = ?
            """, (
                datetime.now(timezone.utc), 'completed', metrics.total_cases,
                metrics.processed_cases, success_rate, metrics.average_confidence,
                self.training_session_id
            ))
        
        logger.info(f"Training session {self.training_session_id} completed successfully")
    
    def fail_training_session(self, error_message: str):
        """Mark training session as failed."""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                UPDATE training_sessions 
                SET end_time = ?, status = ?
                WHERE id = ?
            """, (datetime.now(timezone.utc), f'failed: {error_message}', self.training_session_id))
        
        logger.error(f"Training session {self.training_session_id} failed: {error_message}")

def run_full_training(dataset_directory: str = "Training/", 
                     experiment_name: str = None,
                     chunk_size: int = 1000,
                     max_workers: int = 4) -> TrainingMetrics:
    """
    Convenience function to run full training on all datasets.
    
    Args:
        dataset_directory: Directory containing training JSON files
        experiment_name: Name for this training experiment
        chunk_size: Number of cases per chunk
        max_workers: Number of parallel workers
        
    Returns:
        Final training metrics
    """
    # Find all training JSON files
    training_dir = Path(dataset_directory)
    dataset_paths = list(training_dir.glob("radiology_codes_cleaned_v*.json"))
    
    if not dataset_paths:
        raise ValueError(f"No training files found in {dataset_directory}")
    
    # Configure training
    config = TrainingConfig(
        chunk_size=chunk_size,
        max_workers=max_workers,
        experiment_name=experiment_name or f"full_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    # Run training
    framework = ScalableTrainingFramework(config)
    return framework.train_on_dataset([str(p) for p in dataset_paths])

if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Run scalable training on radiology dataset')
    parser.add_argument('--dataset-dir', default='Training/', help='Directory with training JSON files')
    parser.add_argument('--experiment-name', help='Name for this training experiment')
    parser.add_argument('--chunk-size', type=int, default=1000, help='Cases per chunk')
    parser.add_argument('--max-workers', type=int, default=4, help='Parallel workers')
    
    args = parser.parse_args()
    
    try:
        metrics = run_full_training(
            dataset_directory=args.dataset_dir,
            experiment_name=args.experiment_name,
            chunk_size=args.chunk_size,
            max_workers=args.max_workers
        )
        
        print("\n=== TRAINING COMPLETED ===")
        print(f"Total cases processed: {metrics.processed_cases}")
        print(f"Successful matches: {metrics.successful_matches}")
        print(f"Success rate: {metrics.successful_matches/metrics.processed_cases:.2%}")
        print(f"Average confidence: {metrics.average_confidence:.3f}")
        print(f"Total processing time: {metrics.processing_time:.1f}s")
        print(f"Errors encountered: {len(metrics.errors)}")
        
    except Exception as e:
        print(f"Training failed: {e}")
        exit(1)