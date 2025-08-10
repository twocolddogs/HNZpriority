"""
Hash-based utilities for request identification and caching.

This module provides deterministic hashing of radiology exam requests
based on the four key input fields: DATA_SOURCE, EXAM_CODE, EXAM_NAME, MODALITY_CODE.
"""

import hashlib
import unicodedata
from typing import Optional, Tuple


def normalize_field(value: Optional[str]) -> str:
    """
    Normalize a field value for consistent hashing.
    
    Steps:
    1. Convert None to empty string
    2. Normalize to NFC (canonical composition)
    3. Strip leading/trailing whitespace
    4. Collapse internal whitespace to single spaces
    5. Convert to lowercase
    
    Args:
        value: The field value to normalize (can be None)
        
    Returns:
        Normalized string ready for hashing
    """
    if value is None:
        return ""
    
    # Normalize Unicode to NFC (canonical composition)
    normalized = unicodedata.normalize('NFC', str(value))
    
    # Strip and collapse whitespace
    stripped = normalized.strip()
    collapsed = ' '.join(stripped.split())
    
    # Convert to lowercase
    return collapsed.lower()


def build_preimage(data_source: Optional[str], exam_code: Optional[str], 
                   exam_name: Optional[str], modality_code: Optional[str]) -> str:
    """
    Build the canonical preimage string for hashing.
    
    Format: "v1|ds:{DATA_SOURCE}|ec:{EXAM_CODE}|en:{EXAM_NAME}|mc:{MODALITY_CODE}"
    
    Args:
        data_source: The data source identifier
        exam_code: The exam code
        exam_name: The exam name (required field)
        modality_code: The modality code
        
    Returns:
        Formatted preimage string with escaped pipe characters
    """
    # Normalize all fields
    ds = normalize_field(data_source)
    ec = normalize_field(exam_code)
    en = normalize_field(exam_name)
    mc = normalize_field(modality_code)
    
    # Escape any pipe characters in the values as %7C
    ds = ds.replace('|', '%7C')
    ec = ec.replace('|', '%7C')
    en = en.replace('|', '%7C')
    mc = mc.replace('|', '%7C')
    
    # Build the canonical preimage
    preimage = f"v1|ds:{ds}|ec:{ec}|en:{en}|mc:{mc}"
    
    return preimage


def compute_request_hash(data_source: Optional[str], exam_code: Optional[str],
                        exam_name: Optional[str], modality_code: Optional[str]) -> str:
    """
    Compute SHA-256 hash of the request parameters.
    
    Args:
        data_source: The data source identifier
        exam_code: The exam code
        exam_name: The exam name (required field)  
        modality_code: The modality code
        
    Returns:
        SHA-256 hash as lowercase hexadecimal string
    """
    preimage = build_preimage(data_source, exam_code, exam_name, modality_code)
    hash_bytes = hashlib.sha256(preimage.encode('utf-8')).digest()
    return hash_bytes.hex()


def compute_request_hash_with_preimage(data_source: Optional[str], exam_code: Optional[str],
                                      exam_name: Optional[str], modality_code: Optional[str]) -> Tuple[str, str]:
    """
    Compute both the hash and preimage for debugging/logging.
    
    Args:
        data_source: The data source identifier
        exam_code: The exam code
        exam_name: The exam name (required field)
        modality_code: The modality code
        
    Returns:
        Tuple of (hash_hex, preimage_string)
    """
    preimage = build_preimage(data_source, exam_code, exam_name, modality_code)
    hash_bytes = hashlib.sha256(preimage.encode('utf-8')).digest()
    return hash_bytes.hex(), preimage