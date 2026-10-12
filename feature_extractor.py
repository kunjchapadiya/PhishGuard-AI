"""
feature_extractor.py - Feature Extraction Engine for PhishGuard AI

Extracts the exact 13 lexical and structural URL features used during model training.
Provides utilities for single URL and batch processing.
"""

import ipaddress
from urllib.parse import urlparse, parse_qsl
import pandas as pd


FEATURE_COLUMNS = [
    'isHTTP',
    'length',
    'isSpeacialChar',
    'isDot',
    'isDash',
    'isSlash',
    'isQuestionMark',
    'isEqual',
    'isNumber',
    'isChar',
    'path_depth',
    'query_param_count',
    'TLD_Frequency'
]


def extract_tld(url: str) -> str:
    """Extracts top-level domain (TLD) from a URL string."""
    try:
        hostname = urlparse(url).hostname or ''
        if not hostname:
            # Fallback if no scheme was present
            parsed = urlparse(f"//{url}")
            hostname = parsed.hostname or ''

        # Ignore IPv4 and IPv6 addresses
        try:
            ipaddress.ip_address(hostname)
            return ''
        except ValueError:
            parts = hostname.split('.')
            if len(parts) > 1:
                return parts[-1].lower()
            return ''
    except (ValueError, TypeError):
        return ''


def extract_structure_features(url: str) -> dict:
    """Extracts URL path depth and number of query parameters."""
    url_str = str(url).strip()
    try:
        parsed = urlparse(url_str if "://" in url_str else f"//{url_str}")
        path = parsed.path or ""
        query = parsed.query or ""
    except ValueError:
        path = ""
        query = ""

    path_depth = sum(bool(part) for part in path.split("/"))
    query_param_count = len(parse_qsl(query, keep_blank_values=True))

    return {
        "path_depth": path_depth,
        "query_param_count": query_param_count
    }


def extract_url_features(url: str, tld_frequency_map: dict = None) -> dict:
    """
    Extracts all 13 features for a single URL.
    Returns a dictionary of raw features including TLD string and frequency.
    """
    url_str = str(url).strip()
    struct = extract_structure_features(url_str)
    tld = extract_tld(url_str)

    # Frequency mapping with fallback to zero for unseen TLDs
    tld_freq = 0.0
    if tld_frequency_map and tld:
        tld_freq = float(tld_frequency_map.get(tld, 0.0))

    features = {
        'url': url_str,
        'TLD': tld,
        'isHTTP': 1 if url_str.startswith('https') else 0,
        'length': len(url_str),
        'isSpeacialChar': 1 if not url_str.isalnum() else 0,
        'isDot': sum(1 for c in url_str if c == '.'),
        'isDash': sum(1 for c in url_str if c == '-'),
        'isSlash': sum(1 for c in url_str if c == '/'),
        'isQuestionMark': sum(1 for c in url_str if c == '?'),
        'isEqual': sum(1 for c in url_str if c == '='),
        'isNumber': sum(1 for c in url_str if c.isdigit()),
        'isChar': sum(1 for c in url_str if c.isalpha()),
        'path_depth': struct['path_depth'],
        'query_param_count': struct['query_param_count'],
        'TLD_Frequency': tld_freq
    }

    return features


def features_to_dataframe(feature_list: list) -> pd.DataFrame:
    """
    Converts list of extracted feature dictionaries into an aligned
    DataFrame ready for the scikit-learn ColumnTransformer.
    """
    df = pd.DataFrame(feature_list)
    return df[FEATURE_COLUMNS]
