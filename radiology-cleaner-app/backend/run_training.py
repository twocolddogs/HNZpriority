#!/usr/bin/env python3
# --- START OF FILE run_training.py ---

# =============================================================================
# TRAINING RUNNER
# =============================================================================
# Simple command-line interface for running scalable training on 15K dataset

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from scalable_training import run_full_training, TrainingConfig
from training_optimizer import optimize_training_parameters
from validation_framework import run_validation

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_training_environment():
    """Set up the training environment and check prerequisites."""
    # Create necessary directories
    Path("logs/training").mkdir(parents=True, exist_ok=True)
    Path("checkpoints").mkdir(parents=True, exist_ok=True)
    
    # Check for training data
    training_dir = Path("Training")
    if not training_dir.exists():
        logger.error("Training directory not found. Please ensure Training/ directory exists.")
        return False
    
    training_files = list(training_dir.glob("radiology_codes_cleaned_v*.json"))
    if not training_files:
        logger.error("No training files found in Training/ directory.")
        return False
    
    logger.info(f"Found {len(training_files)} training files")
    for file in training_files:
        logger.info(f"  - {file.name}")
    
    return True

def run_basic_training(args):
    """Run basic training without optimization."""
    logger.info("Starting basic training on full dataset")
    
    try:
        metrics = run_full_training(
            dataset_directory=args.dataset_dir,
            experiment_name=args.experiment_name,
            chunk_size=args.chunk_size,
            max_workers=args.max_workers
        )
        
        print("\n" + "="*50)
        print("TRAINING COMPLETED SUCCESSFULLY")
        print("="*50)
        print(f"Total cases processed: {metrics.processed_cases:,}")
        print(f"Successful matches: {metrics.successful_matches:,}")
        print(f"Success rate: {metrics.successful_matches/metrics.processed_cases:.1%}")
        print(f"Average confidence: {metrics.average_confidence:.3f}")
        print(f"Total processing time: {metrics.processing_time:.1f} seconds")
        print(f"Processing speed: {metrics.processed_cases/metrics.processing_time:.1f} cases/sec")
        print(f"Errors encountered: {len(metrics.errors)}")
        
        if metrics.errors:
            print(f"\nFirst 5 errors:")
            for error in metrics.errors[:5]:
                print(f"  - {error}")
        
        return True
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return False

def run_optimization(args):
    """Run hyperparameter optimization."""
    logger.info("Starting hyperparameter optimization")
    
    try:
        best_result = optimize_training_parameters(
            dataset_directory=args.dataset_dir,
            max_experiments=args.max_experiments,
            strategy=args.strategy
        )
        
        print("\n" + "="*50)
        print("OPTIMIZATION COMPLETED SUCCESSFULLY")
        print("="*50)
        print(f"Best validation score: {best_result.validation_score:.3f}")
        print(f"Experiments run: {args.max_experiments}")
        print(f"Strategy used: {args.strategy}")
        print("\nBest parameters:")
        for param, value in best_result.config_params.items():
            print(f"  {param}: {value:.3f}")
        
        print(f"\nTraining metrics for best configuration:")
        print(f"  Cases processed: {best_result.training_metrics.processed_cases:,}")
        print(f"  Success rate: {best_result.training_metrics.successful_matches/best_result.training_metrics.processed_cases:.1%}")
        print(f"  Processing speed: {best_result.processing_speed:.1f} cases/sec")
        
        print(f"\nOptimized configuration saved to: optimized_config.yaml")
        
        return True
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return False

def run_validation_only(args):
    """Run validation framework only."""
    logger.info("Running validation framework")
    
    try:
        results = run_validation(
            config_path=args.config_path,
            sanity_test_path=args.sanity_test_path
        )
        
        print("\n" + "="*50)
        print("VALIDATION COMPLETED")
        print("="*50)
        
        if 'error' in results:
            print(f"Validation failed: {results['error']}")
            return False
        
        summary = results.get('summary', {})
        print(f"Preprocessing consistency: {summary.get('overall_preprocessing_consistency', 0):.1%}")
        print(f"Modality extraction accuracy: {summary.get('modality_extraction_overall', 0):.1%}")
        print(f"Total validation cases: {results.get('total_validation_cases', 0)}")
        
        # Show detailed results
        if 'preprocessing_consistency' in results:
            print(f"\nPreprocessing consistency by group:")
            for group, score in results['preprocessing_consistency'].items():
                print(f"  {group}: {score:.1%}")
        
        if 'modality_extraction_accuracy' in results:
            acc = results['modality_extraction_accuracy']
            if 'by_modality' in acc:
                print(f"\nModality extraction by type:")
                for modality, accuracy in acc['by_modality'].items():
                    print(f"  {modality}: {accuracy:.1%}")
        
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

def main():
    """Main entry point for training runner."""
    parser = argparse.ArgumentParser(
        description='Scalable training runner for NHS radiology lookup engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run basic training on full dataset
  python3 run_training.py train --chunk-size 1000

  # Run hyperparameter optimization
  python3 run_training.py optimize --max-experiments 50 --strategy random_search

  # Run validation only
  python3 run_training.py validate

  # Quick test with small chunks
  python3 run_training.py train --chunk-size 100 --experiment-name quick_test
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Training command')
    
    # Training command
    train_parser = subparsers.add_parser('train', help='Run full training')
    train_parser.add_argument('--dataset-dir', default='Training/', 
                             help='Directory containing training JSON files')
    train_parser.add_argument('--experiment-name', help='Name for this training experiment')
    train_parser.add_argument('--chunk-size', type=int, default=1000, 
                             help='Number of cases to process per chunk')
    train_parser.add_argument('--max-workers', type=int, default=4, 
                             help='Number of parallel workers')
    
    # Optimization command
    opt_parser = subparsers.add_parser('optimize', help='Run hyperparameter optimization')
    opt_parser.add_argument('--dataset-dir', default='Training/', 
                           help='Directory containing training JSON files')
    opt_parser.add_argument('--max-experiments', type=int, default=25, 
                           help='Maximum number of optimization experiments')
    opt_parser.add_argument('--strategy', choices=['grid_search', 'random_search'], 
                           default='random_search', help='Optimization strategy')
    
    # Validation command
    val_parser = subparsers.add_parser('validate', help='Run validation only')
    val_parser.add_argument('--config-path', default='config.yaml', 
                           help='Path to configuration file')
    val_parser.add_argument('--sanity-test-path', default='core/sanity_test.json', 
                           help='Path to sanity test data')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up environment
    if not setup_training_environment():
        return 1
    
    # Record start time
    start_time = datetime.now()
    logger.info(f"Starting {args.command} at {start_time}")
    
    # Run the requested command
    success = False
    
    try:
        if args.command == 'train':
            success = run_basic_training(args)
        elif args.command == 'optimize':
            success = run_optimization(args)
        elif args.command == 'validate':
            success = run_validation_only(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    # Report final results
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        print(f"\n✅ {args.command.upper()} COMPLETED SUCCESSFULLY")
        print(f"Total time: {duration}")
        return 0
    else:
        print(f"\n❌ {args.command.upper()} FAILED")
        print(f"Total time: {duration}")
        return 1

if __name__ == "__main__":
    exit(main())