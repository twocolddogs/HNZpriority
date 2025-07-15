# Radiology Cleaner Application - System Architecture

## 1. Overview

The Radiology Cleaner application is a web-based tool designed to standardize and process radiology exam names. It leverages a Flask backend for API services, a Python-based natural language processing (NLP) engine for semantic parsing, and a simple HTML/JavaScript frontend for user interaction. The system aims to provide clean, standardized exam names, SNOMED codes, and extracted clinical components (anatomy, laterality, contrast, etc.) for improved data quality and interoperability.

## 2. Architecture Diagram

```mermaid
graph TD
    User[User] -->|HTTP/S| Frontend[Web Browser (index.html, app.js)]
    Frontend -->|API Calls (JSON)| Backend[Flask Application (backend/app.py)]

    subgraph Backend Services
        Backend --> NLPProcessor[NLP Processor (backend/nlp_processor.py)]
        Backend --> RadiologySemanticParser[Radiology Semantic Parser (backend/parser.py)]
        Backend --> NHSLookupEngine[NHS Lookup Engine (backend/nhs_lookup_engine.py)]
        Backend --> DatabaseManager[Database Manager (backend/database_models.py)]
        Backend --> CacheManager[Cache Manager (backend/database_models.py)]
        Backend --> FeedbackTrainingManager[Feedback Training Manager (backend/feedback_training.py)]
        Backend --> ParsingUtils[Parsing Utilities (backend/parsing_utils.py)]
        NLPProcessor --> HuggingFaceAPI[Hugging Face Inference API]
        RadiologySemanticParser --> ParsingUtils
        NHSLookupEngine --> NLPProcessor
        DatabaseManager --> SQLiteDB[SQLite Database (radiology_cleaner.db)]
        CacheManager --> InMemCache[In-Memory Cache]
    end

    Backend --> DataFiles[Data Files (core/*.json, abbreviations.csv, etc.)]
```

## 3. Component Breakdown

### 3.1. Frontend

*   **`index.html`**: The main entry point for the web application, providing the basic HTML structure.
*   **`app.js`**: Contains the JavaScript logic for the user interface, handling user input, making API requests to the backend, and displaying results.
*   **`unified-styles.css`**: Provides the styling for the web application.

### 3.2. Backend (Flask Application)

The Flask application (`backend/app.py`) serves as the central API hub. It exposes several endpoints for parsing, validation, batch processing, and feedback submission.

*   **Initialization**: On startup (or first request in lazy-loading mode), it initializes various core components:
    *   `RadiologySemanticParser`: The primary parsing logic.
    *   `NLPProcessor`: Handles external NLP model interactions.
    *   `NHSLookupEngine`: Manages standardization against the NHS authority.
    *   `DatabaseManager`: For persistent data storage (performance metrics, feedback).
    *   `CacheManager`: For in-memory caching of parsing results.
    *   `FeedbackTrainingManager`: Manages feedback submission and potential retraining.
    *   `AbbreviationExpander`, `AnatomyExtractor`, `LateralityDetector`, `USAContrastMapper`: Utility classes for preprocessing and component extraction.
*   **Endpoints**:
    *   `/health`: Basic health check.
    *   `/models`: Lists available NLP models with status and descriptions.
    *   `/cache-version`: Provides cache information.
    *   `/parse` (Legacy): Unified to use the modern NHS-first lookup pipeline.
    *   `/parse_enhanced`: Enhanced parsing endpoint supporting model selection (`{"model": "biolord"}`).
    *   `/parse_batch`: Optimized endpoint for processing multiple exam names concurrently.
    *   `/validate`: Validates exam data and provides quality scores, warnings, and suggestions.
    *   `/feedback`: Submits user feedback for corrections or general comments.
    *   `/parse_with_learning`: Placeholder for future learning enhancements.
    *   `/admin/retrain`: Admin endpoint to trigger pattern retraining (requires authentication).
*   **Concurrency**: Uses `ThreadPoolExecutor` for `parse_batch` to handle multiple requests efficiently.
*   **Graceful Shutdown**: Implements signal handlers and worker tracking for graceful shutdown, ensuring ongoing processes complete before termination.
*   **Performance Monitoring**: Records performance metrics for each endpoint in the database.

### 3.3. Core Logic Modules

*   **`backend/parser.py` (RadiologySemanticParser)**:
    *   The core component for rule-based semantic parsing of radiology exam names.
    *   **Modality Detection**: Accurately classifies imaging modalities including:
        *   `XR`: Plain films and mammography (MG/Mammo/Mamm→XR)
        *   `XA`: X-Ray Angiography for interventional procedures  
        *   `Fluoroscopy`: All barium studies (swallow, meal, enema, follow-through)
        *   `DEXA`: Bone densitometry studies
    *   **Technique Classification**: Distinguishes between imaging techniques:
        *   `Angiography`: Diagnostic vascular imaging including DSA
        *   `Interventional`: NHS-defined specialist procedures (stents, angioplasty, embolization)
        *   `Barium Study`: Fluoroscopic GI contrast procedures
        *   `Intervention`: General procedures (biopsies, drainages, PICC lines)
    *   Uses injected utility classes (`AnatomyExtractor`, `LateralityDetector`, `ContrastMapper`) for specific parsing tasks.
    *   Constructs a "clean name" and calculates a confidence score for the parse.
*   **`backend/nlp_processor.py` (NLPProcessor)**:
    *   Handles communication with the Hugging Face Inference API for generating text embeddings.
    *   **Multiple Model Support**: Configurable models including:
        *   `default`/`pubmed`: NeuML/pubmedbert-base-embeddings (medical terminology optimized)
        *   `biolord`: FremyCompany/BioLORD-2023 (advanced biomedical language model)
        *   `general`: sentence-transformers/all-MiniLM-L6-v2 (general-purpose)
    *   Uses direct `requests` calls for robustness and lightweight operation.
    *   Provides methods for single and batch embedding generation, and semantic similarity calculation.
    *   Requires `HUGGING_FACE_TOKEN` environment variable for functionality.
*   **`backend/nhs_lookup_engine.py` (NHSLookupEngine)**:
    *   Responsible for standardizing exam names against a predefined NHS authority (from `core/NHS.json`).
    *   **Unified Preprocessing Pipeline**: Pre-processes NHS reference data with same rules as user input.
    *   **Dynamic Cache Invalidation**: Embeddings cache incorporates system cache version to invalidate when parsing rules change.
    *   **Dual Lookup Strategy**: Attempts Clean Name matching first, then SNOMED FSN matching for expanded terminology.
    *   **Interventional Procedure Weighting**: Enhanced scoring for NHS-defined interventional procedures.
    *   Uses NLP embeddings with configurable models for semantic similarity matching.
*   **`backend/database_models.py` (DatabaseManager, CacheManager)**:
    *   `DatabaseManager`: Manages interactions with the SQLite database (`radiology_cleaner.db`) for storing performance metrics and feedback.
    *   `CacheManager`: Implements an in-memory cache to store parsing results, reducing redundant computations for frequently requested exam names.
*   **`backend/feedback_training.py` (FeedbackTrainingManager)**:
    *   Manages the submission of user feedback, which can be used for future model retraining or rule refinement.
*   **`backend/parsing_utils.py`**:
    *   Contains various utility classes and functions used by the `RadiologySemanticParser` and other modules for preprocessing and specific extraction tasks:
        *   `AbbreviationExpander`: Expands medical abbreviations including anatomy (br→breast), laterality (bilateral→bilateral), and GI studies (ugi→upper gi, sbft→small bowel follow through).
        *   `AnatomyExtractor`: Extracts anatomical terms from NHS authority data with comprehensive stop-word filtering.
        *   `LateralityDetector`: Identifies laterality with case-sensitive normalization (Left/Right/Bilateral→left/right/bilateral).
        *   `ContrastMapper`: Enhanced contrast detection supporting hyphenated variations (non-contrast, non contrast).
*   **`backend/cache_version.py`**: Manages dynamic cache versioning to ensure cache invalidation when processing rules or data change.
*   **`backend/context_detection.py`**: Provides contextual analysis including:
    *   **Interventional Procedure Detection**: NHS-specific criteria for specialist procedures performed in interventional labs.
    *   **Gender/Age Context**: Medical specialty and demographic context detection.
    *   **Clinical Context**: Screening, emergency, follow-up, and intervention classification.

### 3.4. Data Storage

*   **`radiology_cleaner.db`**: A SQLite database used by `DatabaseManager` to store:
    *   Performance metrics (endpoint, processing time, input size, success/error).
    *   User feedback.
*   **`core/NHS.json`**: Contains the authoritative list of NHS radiology exam names and their associated SNOMED codes, used by `NHSLookupEngine`.
*   **`core/USA.json`**: Likely contains USA-specific patterns or data for parsing utilities.
*   **`abbreviations.csv`**: Used by `AbbreviationExpander` for abbreviation lookup.
*   **`radiology_classifier.pkl`, `radiology_mlb.pkl`, `radiology_vectorizer.pkl`**: These are likely pickled machine learning models (classifier, multi-label binarizer, vectorizer) used for older or alternative NLP approaches, though the current `nlp_processor.py` indicates a shift towards an API-based Hugging Face model.

## 4. Data Flow

1.  **User Input**: A user enters an exam name into the frontend (`index.html`, `app.js`).
2.  **API Request**: `app.js` sends an AJAX request (e.g., to `/parse_enhanced` or `/parse_batch`) to the Flask backend.
3.  **Backend Processing**:
    *   `backend/app.py` receives the request.
    *   It first checks the `CacheManager` for a cached result.
    *   If not cached, the exam name is preprocessed (`_preprocess_exam_name`).
    *   The `RadiologySemanticParser` is invoked to extract components (modality, anatomy, laterality, contrast, technique). This parser may utilize `NLPProcessor` for semantic embeddings and `ParsingUtils` for rule-based extraction.
    *   The `NHSLookupEngine` then takes the extracted components and the cleaned exam name to find the best matching standardized NHS exam from `core/NHS.json`, potentially using `NLPProcessor` for semantic similarity.
    *   The result is formatted and stored in the `CacheManager`.
    *   Performance metrics are recorded via `DatabaseManager`.
4.  **API Response**: The Flask backend returns a JSON response containing the parsed, standardized, and enriched exam data.
5.  **Frontend Display**: `app.js` receives the JSON response and updates the UI to display the results to the user.
6.  **Feedback Loop**: Users can submit feedback via the `/feedback` endpoint, which is stored in the SQLite database by `DatabaseManager` and managed by `FeedbackTrainingManager` for potential future retraining.

## 5. Key Technologies

*   **Frontend**: HTML, CSS, JavaScript
*   **Backend**: Python, Flask, Flask-CORS
*   **NLP**: Hugging Face Inference API (via `requests`), `numpy`
*   **Data Storage**: SQLite, JSON files, CSV files
*   **Concurrency**: Python's `threading`, `multiprocessing`, `concurrent.futures.ThreadPoolExecutor`
*   **Logging**: Python's `logging` module

## 6. Recent Architectural Improvements

### 6.1. Enhanced Medical Accuracy (2024)

**Modality Classification Improvements:**
*   **Mammography Reclassification**: Mammography is now correctly classified as XR modality (technique) rather than separate modality, aligning with medical standards.
*   **Barium Studies**: All barium procedures (swallow, meal, enema, follow-through) correctly classified as Fluoroscopy modality.
*   **XA Modality Support**: Added X-Ray Angiography modality for interventional radiology procedures.
*   **DEXA Integration**: Bone densitometry studies properly classified with dedicated patterns.

**NHS Interventional Procedure Accuracy:**
*   Redefined interventional detection based on NHS credentialing requirements for specialist procedures.
*   Focuses on procedures performed by interventional radiologists in specialized labs (typically XA modality).
*   Distinguishes NHS interventional procedures from general interventions (PICC lines, biopsies).

**Preprocessing Pipeline Enhancements:**
*   **Abbreviation Expansion**: Critical medical abbreviations (br→breast, bilateral case normalization).
*   **Cache Invalidation**: NHS embeddings cache now incorporates system version for proper invalidation.
*   **Consistent Processing**: NHS reference data uses identical preprocessing as user input.

### 6.2. Multi-Model NLP Support

**Advanced Biomedical Models:**
*   **BioLORD Integration**: FremyCompany/BioLORD-2023 for enhanced medical terminology understanding.
*   **Model Selection API**: Users can specify model via `{"model": "biolord"}` in requests.
*   **Model Discovery**: `/models` endpoint lists available models with status and capabilities.

**Improved Semantic Matching:**
*   Dual lookup strategy (Clean Name + SNOMED FSN) for comprehensive matching.
*   Enhanced confidence scoring with component alignment bonuses.
*   Interventional procedure weighting for accurate NHS flag classification.

## 7. Deployment Considerations

*   **Environment Variables**: `HUGGING_FACE_TOKEN` is crucial for NLP functionality. `ADMIN_TOKEN` is required for the `/admin/retrain` endpoint.
*   **Scalability**: The `parse_batch` endpoint and `ThreadPoolExecutor` are designed for efficient batch processing. The API-based NLP approach offloads heavy computation.
*   **Database**: SQLite is suitable for local development and smaller deployments. For larger-scale production, a more robust database (e.g., PostgreSQL, MySQL) might be considered, requiring changes to `database_models.py`.
*   **Caching**: The in-memory cache improves performance for repeated requests. A distributed cache (e.g., Redis) could be integrated for multi-instance deployments.
*   **Monitoring**: Performance metrics are recorded, which can be used for monitoring and optimization.
*   **Graceful Shutdown**: Ensures data integrity and smooth service restarts.