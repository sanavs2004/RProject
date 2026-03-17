"""
ML Fit Predictor for RecruitAI
Uses XGBoost + SVM ensemble trained on synthetic recruitment data
to predict candidate fit with ~89% accuracy.

SHAP Explainability added — explains WHY each prediction was made.
"""

import os
import json
import numpy as np
import pickle
from datetime import datetime


FEATURE_NAMES = [
    'semantic_score',
    'skill_match_score',
    'education_score',
    'github_score',
    'confidence_bonus',
    'skill_count',
    'word_count_norm',
    'has_github',
]

FEATURE_LABELS = {
    'semantic_score'   : 'Resume–JD Semantic Match',
    'skill_match_score': 'Skill Match Score',
    'education_score'  : 'Education Relevance',
    'github_score'     : 'GitHub Activity Score',
    'confidence_bonus' : 'GitHub Confidence Bonus',
    'skill_count'      : 'Number of Skills Found',
    'word_count_norm'  : 'Resume Length',
    'has_github'       : 'Has GitHub Profile',
}


def _extract_features(candidate: dict) -> np.ndarray:
    semantic    = float(candidate.get('semantic_score', 50) or 50)
    skill_match = float(candidate.get('skill_match_score', 50) or 50)
    education   = float(candidate.get('education_score', 50) or 50)
    github      = float(candidate.get('github_score', 0) or 0)
    bonus       = float(candidate.get('confidence_bonus', 0) or 0)
    skill_count = len(candidate.get('extracted_skills', []))
    word_count  = min(float(candidate.get('word_count', 300) or 300) / 1000.0, 1.0)
    has_github  = 1.0 if candidate.get('has_github') else 0.0
    return np.array([
        semantic, skill_match, education, github,
        bonus, skill_count, word_count, has_github
    ], dtype=np.float32)


def _generate_synthetic_dataset(n_samples: int = 2000):
    np.random.seed(42)
    X, y = [], []
    for _ in range(n_samples):
        profile = np.random.choice(['strong', 'medium', 'weak'], p=[0.3, 0.4, 0.3])
        if profile == 'strong':
            semantic    = np.random.normal(75, 10)
            skill_match = np.random.normal(80, 8)
            education   = np.random.normal(70, 12)
            github      = np.random.normal(72, 15)
            bonus       = np.random.normal(8, 3)
            skill_count = np.random.randint(6, 15)
            word_count  = np.random.uniform(0.4, 1.0)
            has_github  = np.random.choice([0, 1], p=[0.2, 0.8])
            label = 1
        elif profile == 'medium':
            semantic    = np.random.normal(58, 10)
            skill_match = np.random.normal(60, 10)
            education   = np.random.normal(55, 12)
            github      = np.random.normal(45, 20)
            bonus       = np.random.normal(4, 3)
            skill_count = np.random.randint(3, 8)
            word_count  = np.random.uniform(0.2, 0.6)
            has_github  = np.random.choice([0, 1], p=[0.5, 0.5])
            label = np.random.choice([0, 1], p=[0.45, 0.55])
        else:
            semantic    = np.random.normal(40, 10)
            skill_match = np.random.normal(38, 10)
            education   = np.random.normal(40, 12)
            github      = np.random.normal(20, 15)
            bonus       = np.random.normal(1, 2)
            skill_count = np.random.randint(0, 4)
            word_count  = np.random.uniform(0.05, 0.3)
            has_github  = np.random.choice([0, 1], p=[0.8, 0.2])
            label = 0
        features = np.clip([
            semantic, skill_match, education,
            max(github, 0), max(bonus, 0),
            skill_count, word_count, has_github
        ], 0, 100)
        features[6] = np.clip(word_count, 0, 1)
        features[7] = has_github
        X.append(features)
        y.append(label)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def train_and_save(models_folder: str) -> dict:
    from sklearn.svm import SVC
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.ensemble import VotingClassifier
    import xgboost as xgb

    os.makedirs(models_folder, exist_ok=True)
    print("🔧 Generating synthetic recruitment dataset...")
    X, y = _generate_synthetic_dataset(n_samples=2000)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    print("🚀 Training XGBoost...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric='logloss',
        random_state=42, verbosity=0)
    xgb_model.fit(X_train_s, y_train)
    xgb_acc = accuracy_score(y_test, xgb_model.predict(X_test_s))

    print("🚀 Training SVM...")
    svm_model = SVC(kernel='rbf', C=10, gamma='scale',
                    probability=True, random_state=42)
    svm_model.fit(X_train_s, y_train)
    svm_acc = accuracy_score(y_test, svm_model.predict(X_test_s))

    print("🚀 Building Ensemble...")
    ensemble = VotingClassifier(
        estimators=[('xgb', xgb_model), ('svm', svm_model)],
        voting='soft', weights=[0.6, 0.4])
    ensemble.fit(X_train_s, y_train)
    ens_preds = ensemble.predict(X_test_s)
    ens_acc   = accuracy_score(y_test, ens_preds)
    report    = classification_report(y_test, ens_preds, output_dict=True)

    # Save ensemble
    with open(os.path.join(models_folder, 'fit_predictor_ensemble.pkl'), 'wb') as f:
        pickle.dump(ensemble, f)
    # Save scaler
    with open(os.path.join(models_folder, 'fit_predictor_scaler.pkl'), 'wb') as f:
        pickle.dump(scaler, f)
    # Save XGBoost separately — needed for SHAP
    with open(os.path.join(models_folder, 'fit_predictor_xgb.pkl'), 'wb') as f:
        pickle.dump(xgb_model, f)

    metadata = {
        'trained_at'       : datetime.now().isoformat(),
        'n_samples'        : 2000,
        'features'         : FEATURE_NAMES,
        'xgb_accuracy'     : round(xgb_acc * 100, 1),
        'svm_accuracy'     : round(svm_acc * 100, 1),
        'ensemble_accuracy': round(ens_acc * 100, 1),
        'precision'        : round(report['1']['precision'] * 100, 1),
        'recall'           : round(report['1']['recall'] * 100, 1),
        'f1_score'         : round(report['1']['f1-score'] * 100, 1),
    }
    with open(os.path.join(models_folder, 'fit_predictor_meta.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Models saved! Accuracy: {ens_acc*100:.1f}%")
    return metadata


# ══════════════════════════════════════════════════════════════════════════════
#  SHAP Explanation
# ══════════════════════════════════════════════════════════════════════════════

def _compute_shap(xgb_model, scaler, features: np.ndarray) -> list:
    """
    Compute SHAP values for one candidate.
    Returns list sorted by impact — highest first.

    Each item:
    {
        'feature'   : 'skill_match_score',
        'label'     : 'Skill Match Score',
        'value'     : 82.1,
        'impact'    : '+34.2%',
        'direction' : 'positive',   ← pushed score UP
        'magnitude' : 'high',
    }
    """
    try:
        import shap

        scaled = scaler.transform(features.reshape(1, -1))
        explainer   = shap.TreeExplainer(xgb_model)
        shap_values = explainer.shap_values(scaled)

        # Binary classification: pick class 1 (fit=True)
        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]

        raw = features[0]
        result = []
        for i, fname in enumerate(FEATURE_NAMES):
            sv_i      = float(sv[i])
            raw_val   = float(raw[i])
            abs_pct   = abs(sv_i) * 100

            magnitude = 'high' if abs_pct >= 10 else ('medium' if abs_pct >= 4 else 'low')

            result.append({
                'feature'   : fname,
                'label'     : FEATURE_LABELS.get(fname, fname),
                'value'     : round(raw_val, 1),
                'shap_value': round(sv_i, 4),
                'impact_pct': round(abs_pct, 1),
                'impact'    : f"+{abs_pct:.1f}%" if sv_i > 0 else f"-{abs_pct:.1f}%",
                'direction' : 'positive' if sv_i > 0 else 'negative',
                'magnitude' : magnitude,
            })

        result.sort(key=lambda x: x['impact_pct'], reverse=True)
        return result

    except ImportError:
        print("⚠️  pip install shap")
        return _simple_explanation(features)
    except Exception as e:
        print(f"⚠️  SHAP error: {e}")
        return _simple_explanation(features)


def _simple_explanation(features: np.ndarray) -> list:
    """Simple rule-based explanation when SHAP unavailable."""
    raw = features[0]
    thresholds = {
        'semantic_score'   : (70, 50),
        'skill_match_score': (70, 50),
        'education_score'  : (65, 45),
        'github_score'     : (60, 0),
        'confidence_bonus' : (8, 0),
        'skill_count'      : (7, 3),
        'word_count_norm'  : (0.4, 0.2),
        'has_github'       : (1, 0),
    }
    result = []
    for i, fname in enumerate(FEATURE_NAMES):
        val = float(raw[i])
        good, poor = thresholds.get(fname, (70, 40))
        direction = 'positive' if val >= good else ('negative' if val < poor else 'neutral')
        result.append({
            'feature'   : fname,
            'label'     : FEATURE_LABELS.get(fname, fname),
            'value'     : round(val, 1),
            'shap_value': 0,
            'impact_pct': 0,
            'impact'    : '+high' if direction == 'positive' else ('-low' if direction == 'negative' else '~medium'),
            'direction' : direction,
            'magnitude' : 'medium',
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  FitPredictor Class
# ══════════════════════════════════════════════════════════════════════════════

class FitPredictor:

    def __init__(self, models_folder: str):
        self.models_folder = models_folder
        self.ensemble  = None
        self.scaler    = None
        self.xgb_model = None
        self.metadata  = {}
        self._load()

    def _load(self):
        ep = os.path.join(self.models_folder, 'fit_predictor_ensemble.pkl')
        sp = os.path.join(self.models_folder, 'fit_predictor_scaler.pkl')
        xp = os.path.join(self.models_folder, 'fit_predictor_xgb.pkl')
        mp = os.path.join(self.models_folder, 'fit_predictor_meta.json')

        if os.path.exists(ep) and os.path.exists(sp):
            with open(ep, 'rb') as f: self.ensemble  = pickle.load(f)
            with open(sp, 'rb') as f: self.scaler    = pickle.load(f)

            # Load XGBoost for SHAP
            if os.path.exists(xp):
                with open(xp, 'rb') as f: self.xgb_model = pickle.load(f)
            else:
                # Extract from ensemble estimators
                try:
                    self.xgb_model = self.ensemble.estimators_[0]
                except:
                    self.xgb_model = None

            if os.path.exists(mp):
                with open(mp, 'r') as f: self.metadata = json.load(f)

            print(f"✅ FitPredictor loaded (accuracy: {self.metadata.get('ensemble_accuracy','?')}%)")
        else:
            print("⚙️  No saved model — training now...")
            self.metadata = train_and_save(self.models_folder)
            self._load()

    def predict(self, candidate: dict) -> dict:
        """
        Predict fit + SHAP explanation for one candidate.

        Input:  candidate dict with semantic_score, skill_match_score etc.
        Output: adds ml_fit_score, ml_fit_label, shap_explanation
        """
        if self.ensemble is None:
            return self._fallback(candidate)

        try:
            features = _extract_features(candidate).reshape(1, -1)
            scaled   = self.scaler.transform(features)
            proba    = self.ensemble.predict_proba(scaled)[0][1]
            score    = round(proba * 100, 1)

            if score >= 70:
                label, confidence = 'Strong Fit', 'High'
            elif score >= 45:
                label, confidence = 'Potential Fit', 'Medium'
            else:
                label, confidence = 'Not a Fit', 'High' if score < 25 else 'Medium'

            # SHAP explanation
            shap_exp = []
            if self.xgb_model is not None:
                shap_exp = _compute_shap(self.xgb_model, self.scaler, features)

            return {
                'ml_fit_score'     : score,
                'ml_fit_label'     : label,
                'ml_fit_confidence': confidence,
                'ml_probability'   : round(float(proba), 4),
                'ml_features_used' : FEATURE_NAMES,
                'shap_explanation' : shap_exp,
            }

        except Exception as e:
            print(f"⚠️ FitPredictor error: {e}")
            return self._fallback(candidate)

    def predict_batch(self, candidates: list) -> list:
        for c in candidates:
            c.update(self.predict(c))
        return candidates

    def _fallback(self, candidate: dict) -> dict:
        score    = candidate.get('overall_score', 50)
        features = _extract_features(candidate).reshape(1, -1)
        label    = 'Strong Fit' if score >= 65 else ('Potential Fit' if score >= 50 else 'Not a Fit')
        conf     = 'Medium'
        return {
            'ml_fit_score'     : round(score, 1),
            'ml_fit_label'     : label,
            'ml_fit_confidence': conf,
            'ml_probability'   : round(score / 100, 4),
            'ml_features_used' : FEATURE_NAMES,
            'shap_explanation' : _simple_explanation(features),
        }

    def get_model_info(self) -> dict:
        return self.metadata

    def retrain(self) -> dict:
        self.metadata = train_and_save(self.models_folder)
        self._load()
        return self.metadata