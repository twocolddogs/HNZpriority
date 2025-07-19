# --- START OF FILE training_optimizer.py ---

# =============================================================================
# TRAINING OPTIMIZER
# =============================================================================
# Advanced optimization framework for hyperparameter tuning and model selection
# using the 15,000 case training dataset

import json
import logging
import itertools
import numpy as np
import yaml
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import sqlite3

from scalable_training import ScalableTrainingFramework, TrainingConfig, TrainingMetrics
from validation_framework import ValidationFramework

logger = logging.getLogger(__name__)

@dataclass
class OptimizationConfig:
    """Configuration for hyperparameter optimization."""
    # Scoring weight ranges to test
    anatomy_weights: List[float] = None
    modality_weights: List[float] = None
    contrast_weights: List[float] = None
    semantic_weights: List[float] = None
    
    # Penalty/bonus ranges
    interventional_penalties: List[float] = None
    exact_match_bonuses: List[float] = None
    
    # Training parameters
    max_experiments: int = 50
    validation_split: float = 0.15
    early_stopping_threshold: float = 0.95
    
    # Optimization strategy
    strategy: str = "grid_search"  # grid_search, random_search, bayesian
    
    def __post_init__(self):
        """Set default ranges if not provided."""
        if self.anatomy_weights is None:
            self.anatomy_weights = [0.25, 0.30, 0.35, 0.40, 0.45]
        if self.modality_weights is None:
            self.modality_weights = [0.20, 0.25, 0.30, 0.35]
        if self.contrast_weights is None:
            self.contrast_weights = [0.10, 0.15, 0.20]
        if self.semantic_weights is None:
            self.semantic_weights = [0.30, 0.35, 0.40, 0.45]
        if self.interventional_penalties is None:
            self.interventional_penalties = [-0.10, -0.15, -0.20, -0.25, -0.30]
        if self.exact_match_bonuses is None:
            self.exact_match_bonuses = [0.15, 0.20, 0.25, 0.30]

@dataclass
class ExperimentResult:
    """Results from a single optimization experiment."""
    experiment_id: str
    config_params: Dict[str, float]
    training_metrics: TrainingMetrics
    validation_score: float
    processing_speed: float
    memory_usage: Optional[float] = None
    error_message: Optional[str] = None

class TrainingOptimizer:
    """
    Advanced hyperparameter optimization for the NHS lookup engine.
    
    Features:
    - Grid search and random search strategies
    - Validation-based performance evaluation
    - Early stopping for efficient optimization
    - Database tracking of all experiments
    - Automatic best configuration selection
    """
    
    def __init__(self, optimization_config: OptimizationConfig = None):
        """Initialize the training optimizer."""
        self.config = optimization_config or OptimizationConfig()
        self.experiments: List[ExperimentResult] = []
        self.best_experiment: Optional[ExperimentResult] = None
        
        # Initialize database for experiment tracking
        self.setup_optimization_database()
        
        logger.info(f"Initialized TrainingOptimizer with {self.config.strategy} strategy")
    
    def setup_optimization_database(self):
        """Create database tables for optimization tracking."""
        db_path = "optimization_results.db"
        
        with sqlite3.connect(db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS optimization_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_name TEXT,
                    strategy TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    total_experiments INTEGER,
                    best_score REAL,
                    best_config_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    experiment_id TEXT,
                    config_json TEXT,
                    training_cases INTEGER,
                    success_rate REAL,
                    avg_confidence REAL,
                    validation_score REAL,
                    processing_speed REAL,
                    memory_usage REAL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES optimization_runs (id)
                );
                
                CREATE TABLE IF NOT EXISTS parameter_importance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    parameter_name TEXT,
                    importance_score REAL,
                    correlation_with_performance REAL,
                    FOREIGN KEY (run_id) REFERENCES optimization_runs (id)
                );
            """)
        
        self.db_path = db_path
        logger.info(f"Optimization database initialized: {db_path}")
    
    def generate_parameter_combinations(self) -> List[Dict[str, float]]:
        """Generate parameter combinations based on optimization strategy."""
        if self.config.strategy == "grid_search":
            return self._generate_grid_search_combinations()
        elif self.config.strategy == "random_search":
            return self._generate_random_search_combinations()
        else:
            raise ValueError(f"Unknown optimization strategy: {self.config.strategy}")
    
    def _generate_grid_search_combinations(self) -> List[Dict[str, float]]:
        """Generate all combinations for grid search."""
        # Create parameter grid
        param_grid = {
            'anatomy_weight': self.config.anatomy_weights,
            'modality_weight': self.config.modality_weights,
            'contrast_weight': self.config.contrast_weights,
            'semantic_weight': self.config.semantic_weights,
            'interventional_penalty': self.config.interventional_penalties,
            'exact_match_bonus': self.config.exact_match_bonuses
        }
        
        # Generate all combinations
        keys = param_grid.keys()
        combinations = []
        
        for values in itertools.product(*param_grid.values()):
            param_dict = dict(zip(keys, values))
            
            # Ensure component weights sum to reasonable total (allowing for technique weight)
            component_sum = (param_dict['anatomy_weight'] + 
                           param_dict['modality_weight'] + 
                           param_dict['contrast_weight'])
            
            # Skip combinations where component weights are too high (leave room for laterality/technique)
            if component_sum > 0.80:
                continue
            
            combinations.append(param_dict)
        
        # Limit to max experiments
        if len(combinations) > self.config.max_experiments:
            # Sample uniformly across the space
            step = len(combinations) // self.config.max_experiments
            combinations = combinations[::step][:self.config.max_experiments]
        
        logger.info(f"Generated {len(combinations)} parameter combinations for grid search")
        return combinations
    
    def _generate_random_search_combinations(self) -> List[Dict[str, float]]:
        """Generate random parameter combinations."""
        combinations = []
        
        for _ in range(self.config.max_experiments):
            param_dict = {
                'anatomy_weight': np.random.choice(self.config.anatomy_weights),
                'modality_weight': np.random.choice(self.config.modality_weights),
                'contrast_weight': np.random.choice(self.config.contrast_weights),
                'semantic_weight': np.random.choice(self.config.semantic_weights),
                'interventional_penalty': np.random.choice(self.config.interventional_penalties),
                'exact_match_bonus': np.random.choice(self.config.exact_match_bonuses)
            }
            
            # Check component weight constraint
            component_sum = (param_dict['anatomy_weight'] + 
                           param_dict['modality_weight'] + 
                           param_dict['contrast_weight'])
            
            if component_sum <= 0.80:
                combinations.append(param_dict)
        
        logger.info(f"Generated {len(combinations)} parameter combinations for random search")
        return combinations
    
    def create_config_from_params(self, params: Dict[str, float]) -> Dict[str, Any]:
        """Create a complete configuration from optimized parameters."""
        # Calculate remaining weights
        component_total = (params['anatomy_weight'] + 
                          params['modality_weight'] + 
                          params['contrast_weight'])
        
        # Distribute remaining weight between laterality and technique
        remaining_weight = 1.0 - component_total
        laterality_weight = remaining_weight * 0.6  # 60% of remaining
        technique_weight = remaining_weight * 0.4   # 40% of remaining
        
        # Create complete configuration
        config = {
            'scoring': {
                'retriever_top_k': 25,
                'weights_component': {
                    'anatomy': params['anatomy_weight'],
                    'modality': params['modality_weight'],
                    'laterality': laterality_weight,
                    'contrast': params['contrast_weight'],
                    'technique': technique_weight
                },
                'weights_final': {
                    'component': 1.0 - params['semantic_weight'],
                    'semantic': params['semantic_weight'],
                    'frequency': 0.0  # Disable for optimization
                },
                'interventional_bonus': 0.15,
                'interventional_penalty': params['interventional_penalty'],
                'specificity_penalty_weight': 0.05,
                'exact_match_bonus': params['exact_match_bonus'],
                'synonym_match_bonus': 0.15,
                'context_match_bonus': 0.10,
                'contrast_mismatch_score': 0.3,
                'contrast_null_score': 0.7
            }
        }
        
        return config
    
    def run_single_experiment(self, params: Dict[str, float], experiment_id: str, 
                            dataset_paths: List[str]) -> ExperimentResult:
        """Run a single optimization experiment."""
        logger.info(f"Running experiment {experiment_id}")
        
        try:
            # Create temporary config file
            config = self.create_config_from_params(params)
            temp_config_path = f"temp_config_{experiment_id}.yaml"
            
            with open(temp_config_path, 'w') as f:
                yaml.safe_dump(config, f)
            
            # Set up training with smaller chunk size for optimization
            training_config = TrainingConfig(
                chunk_size=500,  # Smaller chunks for faster experiments
                max_workers=2,   # Reduce parallelism to avoid resource conflicts
                validation_split=self.config.validation_split,
                enable_progress_tracking=False,  # Disable for speed
                experiment_name=experiment_id
            )
            
            # Run training
            framework = ScalableTrainingFramework(training_config, temp_config_path)
            
            # Use subset of data for optimization (first 2000 cases)
            limited_paths = dataset_paths[:1]  # Use only first dataset for speed
            
            training_metrics = framework.train_on_dataset(limited_paths)
            
            # Run validation
            validation_framework = ValidationFramework(temp_config_path)
            validation_framework.load_sanity_test_data()
            validation_results = validation_framework.run_validation_suite()
            
            # Calculate validation score
            validation_score = 0.0
            if 'summary' in validation_results:
                summary = validation_results['summary']
                # Weighted combination of metrics
                validation_score = (
                    summary.get('modality_extraction_overall', 0.0) * 0.6 +
                    summary.get('overall_preprocessing_consistency', 0.0) * 0.4
                )
            
            # Calculate processing speed (cases per second)
            processing_speed = (training_metrics.processed_cases / 
                              training_metrics.processing_time if training_metrics.processing_time > 0 else 0)
            
            # Clean up temp file
            Path(temp_config_path).unlink(missing_ok=True)
            
            # Create experiment result
            result = ExperimentResult(
                experiment_id=experiment_id,
                config_params=params,
                training_metrics=training_metrics,
                validation_score=validation_score,
                processing_speed=processing_speed
            )
            
            logger.info(f"Experiment {experiment_id} completed: validation_score={validation_score:.3f}")
            return result
            
        except Exception as e:
            error_msg = f"Experiment {experiment_id} failed: {str(e)}"
            logger.error(error_msg)
            
            # Clean up temp file
            Path(f"temp_config_{experiment_id}.yaml").unlink(missing_ok=True)
            
            return ExperimentResult(
                experiment_id=experiment_id,
                config_params=params,
                training_metrics=TrainingMetrics(),
                validation_score=0.0,
                processing_speed=0.0,
                error_message=error_msg
            )
    
    def save_experiment_result(self, result: ExperimentResult, run_id: int):
        """Save experiment result to database."""
        with sqlite3.connect(self.db_path) as conn:
            success_rate = (result.training_metrics.successful_matches / 
                          result.training_metrics.processed_cases 
                          if result.training_metrics.processed_cases > 0 else 0.0)
            
            conn.execute("""
                INSERT INTO experiments 
                (run_id, experiment_id, config_json, training_cases, success_rate, 
                 avg_confidence, validation_score, processing_speed, memory_usage, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, result.experiment_id, json.dumps(result.config_params),
                result.training_metrics.processed_cases, success_rate,
                result.training_metrics.average_confidence, result.validation_score,
                result.processing_speed, result.memory_usage, result.error_message
            ))
    
    def optimize(self, dataset_paths: List[str], run_name: str = None) -> ExperimentResult:
        """
        Run complete hyperparameter optimization.
        
        Args:
            dataset_paths: Paths to training datasets
            run_name: Name for this optimization run
            
        Returns:
            Best experiment result
        """
        if not run_name:
            run_name = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting optimization run: {run_name}")
        
        # Create optimization run record
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO optimization_runs 
                (run_name, strategy, start_time, total_experiments)
                VALUES (?, ?, ?, ?)
            """, (run_name, self.config.strategy, datetime.now(), 0))
            run_id = cursor.lastrowid
        
        try:
            # Generate parameter combinations
            param_combinations = self.generate_parameter_combinations()
            
            logger.info(f"Running {len(param_combinations)} experiments")
            
            # Run experiments
            best_score = 0.0
            best_result = None
            
            for i, params in enumerate(param_combinations):
                experiment_id = f"{run_name}_exp_{i:03d}"
                
                # Run experiment
                result = self.run_single_experiment(params, experiment_id, dataset_paths)
                
                # Save result
                self.save_experiment_result(result, run_id)
                self.experiments.append(result)
                
                # Check if this is the best result
                if result.validation_score > best_score:
                    best_score = result.validation_score
                    best_result = result
                    logger.info(f"New best result: {best_score:.3f} from experiment {experiment_id}")
                
                # Early stopping check
                if best_score >= self.config.early_stopping_threshold:
                    logger.info(f"Early stopping: achieved threshold {self.config.early_stopping_threshold}")
                    break
            
            # Update optimization run
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE optimization_runs 
                    SET end_time = ?, total_experiments = ?, best_score = ?, best_config_json = ?
                    WHERE id = ?
                """, (
                    datetime.now(), len(self.experiments), best_score,
                    json.dumps(best_result.config_params) if best_result else None,
                    run_id
                ))
            
            self.best_experiment = best_result
            
            # Analyze parameter importance
            self._analyze_parameter_importance(run_id)
            
            logger.info(f"Optimization completed. Best score: {best_score:.3f}")
            return best_result
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise
    
    def _analyze_parameter_importance(self, run_id: int):
        """Analyze which parameters have the most impact on performance."""
        if len(self.experiments) < 10:
            return  # Need sufficient data for analysis
        
        # Extract data
        param_names = list(self.experiments[0].config_params.keys())
        param_values = {name: [] for name in param_names}
        scores = []
        
        for exp in self.experiments:
            if exp.error_message is None:  # Only successful experiments
                for name, value in exp.config_params.items():
                    param_values[name].append(value)
                scores.append(exp.validation_score)
        
        if len(scores) < 5:
            return
        
        # Calculate correlations
        scores_array = np.array(scores)
        
        with sqlite3.connect(self.db_path) as conn:
            for param_name, values in param_values.items():
                if len(set(values)) > 1:  # Only if parameter varies
                    values_array = np.array(values)
                    correlation = np.corrcoef(values_array, scores_array)[0, 1]
                    
                    # Calculate importance as absolute correlation
                    importance = abs(correlation) if not np.isnan(correlation) else 0.0
                    
                    conn.execute("""
                        INSERT INTO parameter_importance 
                        (run_id, parameter_name, importance_score, correlation_with_performance)
                        VALUES (?, ?, ?, ?)
                    """, (run_id, param_name, importance, correlation))
        
        logger.info("Parameter importance analysis completed")
    
    def get_best_configuration(self) -> Dict[str, Any]:
        """Get the best configuration found during optimization."""
        if not self.best_experiment:
            raise ValueError("No optimization has been run yet")
        
        return self.create_config_from_params(self.best_experiment.config_params)
    
    def save_best_configuration(self, output_path: str = "optimized_config.yaml"):
        """Save the best configuration to a YAML file."""
        if not self.best_experiment:
            raise ValueError("No optimization has been run yet")
        
        best_config = self.get_best_configuration()
        
        with open(output_path, 'w') as f:
            yaml.safe_dump(best_config, f, default_flow_style=False)
        
        logger.info(f"Best configuration saved to {output_path}")
        logger.info(f"Best validation score: {self.best_experiment.validation_score:.3f}")

def optimize_training_parameters(dataset_directory: str = "Training/",
                               max_experiments: int = 25,
                               strategy: str = "random_search") -> ExperimentResult:
    """
    Convenience function to run hyperparameter optimization.
    
    Args:
        dataset_directory: Directory containing training datasets
        max_experiments: Maximum number of experiments to run
        strategy: Optimization strategy (grid_search or random_search)
        
    Returns:
        Best experiment result
    """
    # Find training datasets
    training_dir = Path(dataset_directory)
    dataset_paths = list(training_dir.glob("radiology_codes_cleaned_v*.json"))
    
    if not dataset_paths:
        raise ValueError(f"No training files found in {dataset_directory}")
    
    # Set up optimization
    opt_config = OptimizationConfig(
        max_experiments=max_experiments,
        strategy=strategy
    )
    
    optimizer = TrainingOptimizer(opt_config)
    
    # Run optimization
    best_result = optimizer.optimize(
        dataset_paths=[str(p) for p in dataset_paths],
        run_name=f"opt_{strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    # Save best configuration
    optimizer.save_best_configuration("optimized_config.yaml")
    
    return best_result

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimize training parameters')
    parser.add_argument('--dataset-dir', default='Training/', help='Training dataset directory')
    parser.add_argument('--max-experiments', type=int, default=25, help='Maximum experiments')
    parser.add_argument('--strategy', choices=['grid_search', 'random_search'], 
                       default='random_search', help='Optimization strategy')
    
    args = parser.parse_args()
    
    try:
        best_result = optimize_training_parameters(
            dataset_directory=args.dataset_dir,
            max_experiments=args.max_experiments,
            strategy=args.strategy
        )
        
        print("\n=== OPTIMIZATION COMPLETED ===")
        print(f"Best validation score: {best_result.validation_score:.3f}")
        print(f"Best parameters: {best_result.config_params}")
        print("Optimized configuration saved to optimized_config.yaml")
        
    except Exception as e:
        print(f"Optimization failed: {e}")
        exit(1)