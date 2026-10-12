"""
train_and_save.py - Model Training and Artifact Serialization Script for PhishGuard AI

This script trains the Phishing URL Detection model using the exact pipeline
defined in script.py / script.ipynb and exports all necessary artifacts
(preprocessing transformer, random forest model, TLD frequency table, metadata)
so that the Flask API can perform real-time URL inferences.
"""

import os
import sys
import json
import pickle
import time
import ipaddress
from urllib.parse import urlparse, parse_qsl

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix


DATA_PATH = os.path.join(os.path.dirname(__file__), "Data", "data.csv")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
PIPELINE_PATH = os.path.join(MODELS_DIR, "phishguard_pipeline.pkl")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")
LEGACY_MODEL_PATH = os.path.join(os.path.dirname(__file__), "random_forest_model.pkl")


def extract_tld(url):
    """Extracts top-level domain from a URL string."""
    try:
        hostname = urlparse(url).hostname or 'N/A'
        try:
            ipaddress.ip_address(hostname)
            return ''
        except ValueError:
            parts = hostname.split('.')
            if len(parts) > 1:
                return parts[-1]
            else:
                return ''
    except (ValueError, TypeError):
        return ''


def extract_features_df(df_input):
    """Extracts all 13 handcrafted URL features matching script.py."""
    print("Extracting lexical and structural features...")
    df = df_input.copy()

    # Lexical features
    df['isHTTP'] = df['url'].apply(lambda x: 1 if str(x).startswith('https') else 0)
    df['length'] = df['url'].apply(lambda x: len(str(x)))
    df['isSpeacialChar'] = df['url'].apply(lambda x: 1 if not str(x).isalnum() else 0)
    df['TLD'] = df['url'].apply(extract_tld)

    # Character count features
    df['isDot'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c == '.'))
    df['isDash'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c == '-'))
    df['isSlash'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c == '/'))
    df['isQuestionMark'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c == '?'))
    df['isEqual'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c == '='))
    df['isNumber'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c.isdigit()))
    df['isChar'] = df['url'].apply(lambda x: sum(1 for c in str(x) if c.isalpha()))

    # Structural path & query features
    def get_structure(url_str):
        u = str(url_str).strip()
        try:
            parsed = urlparse(u if "://" in u else f"//{u}")
            path = parsed.path or ""
            query = parsed.query or ""
        except ValueError:
            path = ""
            query = ""
        path_depth = sum(bool(part) for part in path.split("/"))
        query_params = len(parse_qsl(query, keep_blank_values=True))
        return path_depth, query_params

    struct_results = df['url'].apply(get_structure)
    df['path_depth'] = [r[0] for r in struct_results]
    df['query_param_count'] = [r[1] for r in struct_results]

    return df


def train_and_export(sample_size=None):
    os.makedirs(MODELS_DIR, exist_ok=True)
    start_time = time.time()

    print(f"Loading dataset from: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    initial_shape = df.shape
    print(f"Loaded {initial_shape[0]} rows, {initial_shape[1]} columns.")

    # Deduplication
    df.drop_duplicates(inplace=True)
    print(f"After deduplication: {df.shape[0]} rows.")

    if sample_size and sample_size < len(df):
        print(f"Sampling {sample_size} records for quick training...")
        df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)

    print(f"Class distribution:\n{df['Type'].value_counts()}")

    # Feature extraction
    df = extract_features_df(df)

    # Compute TLD frequency dictionary
    tld_freq_series = df['TLD'].value_counts(normalize=True)
    tld_frequency_dict = tld_freq_series.to_dict()
    df['TLD_Frequency'] = df['TLD'].map(tld_freq_series).fillna(0.0)
    df.drop(columns=['TLD'], inplace=True)

    # Feature matrix X and Target y
    feature_cols = [
        'isHTTP', 'length', 'isSpeacialChar', 'isDot', 'isDash',
        'isSlash', 'isQuestionMark', 'isEqual', 'isNumber', 'isChar',
        'path_depth', 'query_param_count', 'TLD_Frequency'
    ]
    X = df[feature_cols]
    y = df['Type']

    print(f"Features: {feature_cols}")

    # Standard scaling subset as in script.py
    std_cols = [
        'length', 'isNumber', 'isChar', 'isDot', 'isDash',
        'isSlash', 'isQuestionMark', 'isEqual', 'path_depth', 'query_param_count'
    ]
    preprocessing = ColumnTransformer(
        transformers=[('StandardScaler', StandardScaler(), std_cols)],
        remainder='passthrough'
    )

    # Label encoder (0: Phishing, 1: legitimate)
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    classes_list = list(label_encoder.classes_)
    print(f"Classes encoded: {dict(enumerate(classes_list))}")

    # Train-test split
    x_train, x_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    print("Fitting preprocessor...")
    x_train_scaled = preprocessing.fit_transform(x_train)
    x_test_scaled = preprocessing.transform(x_test)

    print("Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )
    model.fit(x_train_scaled, y_train)

    print("Evaluating model performance on test set...")
    y_pred = model.predict(x_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    report = classification_report(y_test, y_pred, target_names=classes_list, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)

    print(f"\nModel Accuracy: {acc:.4f}")
    print(f"Model F1-Score: {f1:.4f}")
    print("\n========== Classification Report ==========")
    print(classification_report(y_test, y_pred, target_names=classes_list))

    print("\n========== Confusion Matrix ==========")
    print(f"                     Predicted {classes_list[0]}    Predicted {classes_list[1]}")
    print(f"Actual {classes_list[0]:<12} {cm[0][0]:>15}    {cm[0][1]:>15}")
    print(f"Actual {classes_list[1]:<12} {cm[1][0]:>15}    {cm[1][1]:>15}\n")

    # Package complete pipeline bundle
    pipeline_bundle = {
        'model': model,
        'preprocessing': preprocessing,
        'tld_frequency': tld_frequency_dict,
        'feature_cols': feature_cols,
        'std_cols': std_cols,
        'classes': classes_list,
        'phishing_class_index': classes_list.index('Phishing') if 'Phishing' in classes_list else 0
    }

    print(f"Saving full pipeline bundle to: {PIPELINE_PATH}")
    with open(PIPELINE_PATH, "wb") as f:
        pickle.dump(pipeline_bundle, f)

    # Also save the model to root directory for backwards compatibility
    with open(LEGACY_MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    # Save model metadata and metrics
    metadata = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 100,
        "features": feature_cols,
        "standard_scaled_features": std_cols,
        "classes": classes_list,
        "metrics": {
            "accuracy": float(acc),
            "f1_score_weighted": float(f1),
            "confusion_matrix": cm.tolist(),
            "confusion_matrix_breakdown": {
                "true_phishing": int(cm[0][0]),
                "false_legitimate_missed": int(cm[0][1]),
                "false_phishing_alarm": int(cm[1][0]),
                "true_legitimate": int(cm[1][1])
            },
            "classification_report": report
        },
        "training_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_training_records": len(df),
        "execution_time_seconds": round(time.time() - start_time, 2)
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"Saved metadata to: {METADATA_PATH}")
    print("Training and artifact export completed successfully!")
    return metadata


if __name__ == "__main__":
    quick_mode = "--quick" in sys.argv
    sample = 50000 if quick_mode else None
    train_and_export(sample_size=sample)
