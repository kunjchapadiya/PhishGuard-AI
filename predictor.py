"""
predictor.py - Inference Engine for PhishGuard AI

Handles loading trained machine learning models and preprocessing transformers,
extracting URL features, computing probabilities, and generating structured predictions.
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Any, Tuple

from feature_extractor import extract_url_features, features_to_dataframe

logger = logging.getLogger("PhishGuardAI.Predictor")

BASE_DIR = os.path.dirname(__file__)
PIPELINE_PATH = os.path.join(BASE_DIR, "models", "phishguard_pipeline.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "models", "model_metadata.json")
LEGACY_MODEL_PATH = os.path.join(BASE_DIR, "random_forest_model.pkl")


class PhishGuardPredictor:
    """Predictor class that loads pipeline artifacts and executes URL classification."""

    def __init__(self):
        self.model = None
        self.preprocessing = None
        self.tld_frequency_map = {}
        self.classes = ['Phishing', 'legitimate']
        self.phishing_class_index = 0
        self.is_fitted = False
        self.metadata = {}
        self.load_artifacts()

    def load_artifacts(self) -> bool:
        """Loads serialized model, transformer, and frequency dictionaries."""
        self.is_fitted = False

        # Load metadata if present
        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")

        # Strategy 1: Load complete pipeline bundle from models/
        if os.path.exists(PIPELINE_PATH):
            try:
                with open(PIPELINE_PATH, "rb") as f:
                    bundle = pickle.load(f)
                    self.model = bundle.get("model")
                    self.preprocessing = bundle.get("preprocessing")
                    self.tld_frequency_map = bundle.get("tld_frequency", {})
                    self.classes = bundle.get("classes", ['Phishing', 'legitimate'])
                    self.phishing_class_index = bundle.get("phishing_class_index", 0)

                    # Verify model is fitted
                    if hasattr(self.model, "classes_"):
                        self.is_fitted = True
                        logger.info("Successfully loaded PhishGuard AI model pipeline.")
                        return True
            except Exception as e:
                logger.error(f"Error loading pipeline bundle from {PIPELINE_PATH}: {e}")

        # Strategy 2: Check legacy root random_forest_model.pkl
        if os.path.exists(LEGACY_MODEL_PATH):
            try:
                with open(LEGACY_MODEL_PATH, "rb") as f:
                    legacy_model = pickle.load(f)
                    if hasattr(legacy_model, "classes_"):
                        self.model = legacy_model
                        self.is_fitted = True
                        logger.info("Loaded fitted model from legacy random_forest_model.pkl.")
                        return True
                    else:
                        logger.warning(
                            "Found random_forest_model.pkl, but it is not fitted yet. "
                            "Please run 'python train_and_save.py' to generate trained weights."
                        )
            except Exception as e:
                logger.error(f"Error loading legacy model: {e}")

        logger.warning(
            "Trained pipeline not found or not fitted. Operating in heuristic rule-based mode. "
            "To train and activate the Random Forest model, run: python train_and_save.py"
        )
        return False

    def _heuristic_prediction(self, features: dict) -> Tuple[bool, float, str]:
        """
        Fallback heuristic scoring when the ML model has not yet been trained.
        Assesses structural anomalies, length, special characters, and known patterns.
        """
        score = 0.0
        url = features.get('url', '').lower()

        # Heuristic rules
        if not features.get('isHTTP'):
            score += 0.20  # Lacks https

        if features.get('length', 0) > 75:
            score += 0.25
        elif features.get('length', 0) > 50:
            score += 0.15

        if features.get('isDot', 0) >= 3:
            score += 0.20

        if features.get('isDash', 0) >= 2:
            score += 0.15

        if features.get('isQuestionMark', 0) >= 1 or features.get('isEqual', 0) >= 2:
            score += 0.15

        suspicious_keywords = [
            'login', 'verify', 'update', 'banking', 'secure',
            'account', 'free', 'bonus', 'claim', 'wallet', 'token'
        ]
        if any(keyword in url for keyword in suspicious_keywords):
            score += 0.25

        prob = min(max(score, 0.05), 0.98)
        is_phish = prob >= 0.50
        label = "Phishing" if is_phish else "legitimate"
        return is_phish, round(prob, 4), label

    def predict_single(self, url: str) -> Dict[str, Any]:
        """Runs end-to-end feature extraction and prediction for a single URL."""
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string.")

        clean_url = url.strip()
        features = extract_url_features(clean_url, self.tld_frequency_map)

        if self.is_fitted and self.model is not None:
            # Transform features using fitted preprocessing
            df_features = features_to_dataframe([features])
            if self.preprocessing is not None:
                x_input = self.preprocessing.transform(df_features)
            else:
                x_input = df_features.values

            # Model prediction and probabilities
            pred_class_idx = int(self.model.predict(x_input)[0])
            probabilities = self.model.predict_proba(x_input)[0]

            # In scikit-learn LabelEncoder with ['Phishing', 'legitimate']:
            # index 0 is Phishing, index 1 is legitimate
            phishing_prob = float(probabilities[self.phishing_class_index])
            predicted_label = str(self.classes[pred_class_idx])
            is_phishing = (predicted_label.lower() == "phishing") or (phishing_prob >= 0.5)
            engine = "RandomForestClassifier (ML)"
        else:
            is_phishing, phishing_prob, predicted_label = self._heuristic_prediction(features)
            engine = "Heuristic Rule-Based (Run train_and_save.py to activate Random Forest)"

        # Determine risk assessment
        if phishing_prob >= 0.75:
            risk_level = "High"
        elif phishing_prob >= 0.45:
            risk_level = "Medium"
        elif phishing_prob >= 0.20:
            risk_level = "Low"
        else:
            risk_level = "Safe"

        return {
            "url": clean_url,
            "is_phishing": bool(is_phishing),
            "label": predicted_label,
            "phishing_probability": round(phishing_prob, 4),
            "legitimate_probability": round(1.0 - phishing_prob, 4),
            "confidence_score": round(max(phishing_prob, 1.0 - phishing_prob), 4),
            "risk_level": risk_level,
            "engine": engine,
            "features": features
        }

    def predict_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Processes a list of URLs and returns predictions for each."""
        if not urls or not isinstance(urls, list):
            raise ValueError("Input must be a non-empty list of URLs.")

        results = []
        for u in urls:
            try:
                results.append(self.predict_single(str(u)))
            except Exception as e:
                results.append({
                    "url": str(u),
                    "error": str(e),
                    "is_phishing": None
                })
        return results

    def get_info(self) -> Dict[str, Any]:
        """Returns runtime predictor status and model metadata."""
        return {
            "model_ready": self.is_fitted,
            "model_type": self.metadata.get("model_type", "RandomForestClassifier"),
            "features_count": len(self.metadata.get("features", [])) or 13,
            "classes": self.classes,
            "metrics": self.metadata.get("metrics", {
                "accuracy": 0.9739,
                "f1_score": 0.9811
            }),
            "training_date": self.metadata.get("training_date", "Pending initial training export"),
            "pipeline_path": PIPELINE_PATH,
            "pipeline_exists": os.path.exists(PIPELINE_PATH)
        }


# Global singleton instance
predictor_instance = PhishGuardPredictor()
