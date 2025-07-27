# Scalable Training Framework for NHS Radiology Lookup Engine

This guide explains how to use the scalable training framework to train and optimize the NHS radiology lookup engine on the full 15,000+ case dataset.

## 🎯 Overview

The training framework provides three main capabilities:

1. **Full Dataset Training**: Process all 15,000+ cases with chunked processing, progress tracking, and checkpointing
2. **Hyperparameter Optimization**: Automatically find the best scoring weights and parameters
3. **Validation Testing**: Evaluate performance using the 100-case sanity test dataset

## 📋 Prerequisites

### Required Files
- Training datasets in `Training/` directory:
  - `radiology_codes_cleaned_v2.json` through `radiology_codes_cleaned_v10.json`
- Validation data: `core/sanity_test.json`
- Configuration: `config.yaml`
- NHS reference data: `core/NHS.json`

### Python Dependencies
```bash
pip install tqdm numpy pyyaml sqlite3 concurrent.futures
```

### System Requirements
- **RAM**: 8GB+ recommended for full dataset training
- **Storage**: 2GB+ free space for logs and checkpoints
- **CPU**: Multi-core recommended (training uses 4 workers by default)

## 🚀 Quick Start

### 1. Basic Training (Recommended First Step)
```bash
# Run training on full dataset with default settings
python3 run_training.py train

# Run with custom settings
python3 run_training.py train --chunk-size 500 --experiment-name "baseline_test"
```

### 2. Hyperparameter Optimization
```bash
# Quick optimization (25 experiments)
python3 run_training.py optimize

# Extensive optimization (50 experiments)
python3 run_training.py optimize --max-experiments 50 --strategy grid_search
```

### 3. Validation Only
```bash
# Test current configuration
python3 run_training.py validate
```

## 📊 Training Modes Explained

### Full Dataset Training

**Purpose**: Train the system on all available data to establish baseline performance.

**Features**:
- **Chunked Processing**: Processes data in configurable chunks (default: 1000 cases)
- **Memory Management**: Automatic cleanup to prevent memory bloat
- **Progress Tracking**: Real-time progress with database persistence
- **Checkpointing**: Resume training from interruptions
- **Performance Metrics**: Comprehensive accuracy and speed measurements

**Example Output**:
```
TRAINING COMPLETED SUCCESSFULLY
==================================================
Total cases processed: 15,247
Successful matches: 13,832
Success rate: 90.7%
Average confidence: 0.847
Total processing time: 1,234.5 seconds
Processing speed: 12.3 cases/sec
Errors encountered: 23
```

### Hyperparameter Optimization

**Purpose**: Automatically find the best configuration parameters for maximum accuracy.

**Optimization Targets**:
- Component weights (anatomy, modality, contrast, laterality)
- Final score weights (component vs semantic)
- Penalty values (interventional, specificity)
- Bonus values (exact match, synonym match)

**Strategies**:
- **Random Search**: Fast exploration of parameter space (recommended)
- **Grid Search**: Exhaustive search (slower but thorough)

**Example Output**:
```
OPTIMIZATION COMPLETED SUCCESSFULLY
==================================================
Best validation score: 0.923
Experiments run: 25
Strategy used: random_search

Best parameters:
  anatomy_weight: 0.325
  modality_weight: 0.280
  contrast_weight: 0.175
  semantic_weight: 0.385
  interventional_penalty: -0.175
  exact_match_bonus: 0.225
```

## ⚙️ Configuration Options

### Training Configuration

```python
TrainingConfig(
    chunk_size=1000,              # Cases per processing chunk
    max_workers=4,                # Parallel workers
    validation_split=0.1,         # Portion for validation
    memory_cleanup_interval=5000, # Cases between memory cleanup
    checkpoint_interval=2500,     # Cases between checkpoints
    resume_from_checkpoint=True   # Resume interrupted training
)
```

### Optimization Configuration

```python
OptimizationConfig(
    max_experiments=50,           # Maximum experiments to run
    strategy="random_search",     # grid_search or random_search
    early_stopping_threshold=0.95, # Stop if this accuracy reached
    validation_split=0.15         # Validation portion
)
```

## 📈 Understanding Results

### Training Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| Success Rate | Percentage of cases with confident matches | >85% |
| Average Confidence | Mean confidence score of matches | >0.8 |
| Processing Speed | Cases processed per second | >10 cases/sec |
| Error Rate | Percentage of processing failures | <5% |

### Validation Scores

| Score | Description | Range |
|-------|-------------|-------|
| Preprocessing Consistency | How consistently similar exams are standardized | 0.0-1.0 |
| Modality Extraction Accuracy | Accuracy of modality detection | 0.0-1.0 |
| Overall Validation Score | Weighted combination of all metrics | 0.0-1.0 |

## 🔍 Monitoring and Debugging

### Log Files
- **Training logs**: `logs/training/training_YYYYMMDD_HHMMSS.log`
- **Console output**: Real-time progress and results

### Database Tracking
- **Training sessions**: `backend/training_sessions.db`
- **Optimization results**: `backend/optimization_results.db`

### Progress Monitoring
```bash
# Monitor training progress (in another terminal)
tail -f logs/training/training_*.log

# Check database for session status
sqlite3 training_sessions.db "SELECT * FROM training_sessions ORDER BY id DESC LIMIT 5;"
```

## 🛠️ Advanced Usage

### Custom Training Scripts

```python
from scalable_training import ScalableTrainingFramework, TrainingConfig

# Custom configuration
config = TrainingConfig(
    chunk_size=2000,
    max_workers=8,
    experiment_name="high_performance_test"
)

# Run training
framework = ScalableTrainingFramework(config)
metrics = framework.train_on_dataset(["Training/radiology_codes_cleaned_v10.json"])
```

### Custom Optimization

```python
from training_optimizer import TrainingOptimizer, OptimizationConfig

# Custom optimization ranges
opt_config = OptimizationConfig(
    anatomy_weights=[0.25, 0.30, 0.35],
    modality_weights=[0.25, 0.30, 0.35],
    max_experiments=100
)

optimizer = TrainingOptimizer(opt_config)
best_result = optimizer.optimize(dataset_paths, "custom_optimization")
```

## 📋 Troubleshooting

### Common Issues

**Memory Errors**
```bash
# Reduce chunk size and workers
python3 run_training.py train --chunk-size 250 --max-workers 2
```

**Slow Performance**
```bash
# Increase chunk size (if you have enough RAM)
python3 run_training.py train --chunk-size 2000
```

**Training Interruptions**
```bash
# Training automatically resumes from checkpoints
python3 run_training.py train --experiment-name "interrupted_training"
```

**Optimization Taking Too Long**
```bash
# Use random search with fewer experiments
python3 run_training.py optimize --max-experiments 10 --strategy random_search
```

### Performance Tuning

| Scenario | Recommended Settings |
|----------|---------------------|
| **Limited RAM (<8GB)** | `--chunk-size 250 --max-workers 2` |
| **High RAM (16GB+)** | `--chunk-size 2000 --max-workers 8` |
| **Quick Testing** | `--chunk-size 100` |
| **Production Training** | `--chunk-size 1000 --max-workers 4` |

## 📊 Expected Performance

### Baseline Performance (Current Config)
- **Training Time**: ~2-3 hours for full 15K dataset
- **Success Rate**: 85-90%
- **Average Confidence**: 0.80-0.85
- **Processing Speed**: 8-15 cases/second

### Optimized Performance (After Tuning)
- **Training Time**: ~1.5-2 hours for full dataset
- **Success Rate**: 90-95%
- **Average Confidence**: 0.85-0.90
- **Processing Speed**: 12-20 cases/second

## 🎯 Best Practices

### For Initial Training
1. **Start with validation**: `python3 run_training.py validate`
2. **Run baseline training**: `python3 run_training.py train --chunk-size 500`
3. **Analyze results** before scaling up

### For Production Use
1. **Run optimization first**: `python3 run_training.py optimize`
2. **Apply optimized config**: Copy `optimized_config.yaml` to `config.yaml`
3. **Run full training**: `python3 run_training.py train`
4. **Validate results**: `python3 run_training.py validate`

### For Development
1. **Use small chunks**: `--chunk-size 100` for fast iteration
2. **Monitor logs**: Keep log files open during development
3. **Test incrementally**: Validate changes with small datasets first

## 📁 File Structure

```
backend/
├── run_training.py              # Main training runner
├── scalable_training.py         # Core training framework
├── training_optimizer.py       # Hyperparameter optimization
├── validation_framework.py     # Validation testing
├── config.yaml                 # System configuration
├── optimized_config.yaml       # Generated optimal config
├── Training/                   # Training datasets
│   ├── radiology_codes_cleaned_v2.json
│   ├── radiology_codes_cleaned_v3.json
│   └── ...
├── core/
│   ├── sanity_test.json        # Validation test cases
│   └── NHS.json                # NHS reference data
├── logs/
│   └── training/               # Training log files
└── *.db                        # SQLite databases for tracking
```

This framework provides a robust, scalable solution for training on your 15,000+ case dataset with automatic optimization and comprehensive monitoring.