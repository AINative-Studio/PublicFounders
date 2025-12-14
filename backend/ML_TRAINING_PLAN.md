# ML Training Plan for Introduction Matching Optimization

## Overview

This document outlines the machine learning training pipeline for continuously improving PublicFounders' introduction matching algorithm based on RLHF data collected from real user interactions.

## Current Baseline Algorithm

### Scoring Formula
```python
overall_score = (
    relevance_score * 0.5 +      # Semantic similarity
    trust_score * 0.25 +          # Profile quality
    reciprocity_score * 0.25      # Mutual value
)
```

### Limitations of Rule-Based Approach
1. **Fixed Weights**: 50/25/25 split may not be optimal for all contexts
2. **No Context Adaptation**: Weights same for all goal types, industries, user segments
3. **No Learned Patterns**: Cannot discover non-linear relationships or interaction effects
4. **No Personalization**: Same scoring for all users regardless of preferences
5. **Manual Tuning**: Requires A/B testing to adjust weights

## ML-Enhanced Approach

### Phase 1: Learning to Rank Model

**Objective**: Learn optimal scoring function from historical introduction outcomes

**Model Type**: Gradient Boosted Decision Trees (LightGBM or XGBoost)

**Why This Model?**
- Handles non-linear relationships between features
- Can learn interaction effects (e.g., high relevance + high trust = extra boost)
- Provides feature importance rankings
- Fast training and inference
- Robust to missing data
- Interpretable through SHAP values

**Input Features** (35+ features):

```python
# Match Score Features (3)
- relevance_score: float [0-1]
- trust_score: float [0-1]
- reciprocity_score: float [0-1]

# Matching Context Features (8)
- num_goal_matches: int [0-10]
- num_ask_matches: int [0-10]
- top_similarity: float [0-1]
- avg_similarity: float [0-1]
- match_type: categorical [goal_based, ask_based, hybrid]
- goal_type_requester: categorical [fundraising, hiring, cofounder, advisory, other]
- goal_type_target: categorical [fundraising, hiring, cofounder, advisory, other]
- goal_types_match: boolean

# Profile Features (12)
- requester_profile_completeness: float [0-1]
- target_profile_completeness: float [0-1]
- requester_has_linkedin: boolean
- target_has_linkedin: boolean
- requester_account_age_days: int
- target_account_age_days: int
- requester_activity_score: float [0-1]  # posts, goals, asks
- target_activity_score: float [0-1]
- requester_intro_success_rate: float [0-1]  # historical
- target_intro_acceptance_rate: float [0-1]  # historical
- requester_total_intros: int
- target_total_intros: int

# Geographic Features (4)
- same_country: boolean
- same_state: boolean
- same_metro_area: boolean
- distance_km: float

# Industry Features (3)
- industry_match_exact: boolean
- industry_match_related: boolean
- industry_diversity_score: float [0-1]

# Temporal Features (5)
- day_of_week: categorical [Mon-Sun]
- hour_of_day: int [0-23]
- is_weekend: boolean
- days_since_last_intro_requester: int
- days_since_last_intro_target: int
```

**Target Variable**:
```python
# Binary classification
success: boolean = (
    (status == "accepted" AND outcome_type IN ["meeting_scheduled", "email_exchanged"])
    OR rating >= 4
)

# OR Regression on success score
success_score: float [0-1] = calculated from RLHF_STRATEGY.md formula
```

**Model Architecture**:
```python
import lightgbm as lgb

params = {
    'objective': 'binary',  # or 'regression'
    'metric': 'auc',        # or 'rmse'
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'max_depth': 6,
    'min_data_in_leaf': 20,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1
}

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, val_data],
    early_stopping_rounds=50
)
```

### Phase 2: Neural Ranking Model

**Objective**: Learn deep representations and personalized rankings

**Model Type**: Two-tower neural network with cross-attention

**Architecture**:

```
Input: [requester_features, target_features, context_features]
    |
    v
[Requester Tower]    [Target Tower]
   (Dense 128)          (Dense 128)
   (Dropout 0.2)        (Dropout 0.2)
   (Dense 64)           (Dense 64)
    |                    |
    +--------------------+
             |
         [Cross-Attention Layer]
             |
         [Concat Layer]
             |
         [Dense 128, ReLU]
             |
         [Dropout 0.3]
             |
         [Dense 64, ReLU]
             |
         [Dense 1, Sigmoid]
             |
          output: P(success)
```

**Implementation**:
```python
import tensorflow as tf

def build_ranking_model(requester_dim, target_dim, context_dim):
    # Requester tower
    requester_input = tf.keras.Input(shape=(requester_dim,), name='requester')
    requester_encoded = tf.keras.layers.Dense(128, activation='relu')(requester_input)
    requester_encoded = tf.keras.layers.Dropout(0.2)(requester_encoded)
    requester_encoded = tf.keras.layers.Dense(64, activation='relu')(requester_encoded)

    # Target tower
    target_input = tf.keras.Input(shape=(target_dim,), name='target')
    target_encoded = tf.keras.layers.Dense(128, activation='relu')(target_input)
    target_encoded = tf.keras.layers.Dropout(0.2)(target_encoded)
    target_encoded = tf.keras.layers.Dense(64, activation='relu')(target_encoded)

    # Context features
    context_input = tf.keras.Input(shape=(context_dim,), name='context')
    context_encoded = tf.keras.layers.Dense(32, activation='relu')(context_input)

    # Cross-attention
    attention = tf.keras.layers.Attention()([requester_encoded, target_encoded])

    # Combine all
    combined = tf.keras.layers.Concatenate()([
        requester_encoded, target_encoded, attention, context_encoded
    ])

    # Final layers
    x = tf.keras.layers.Dense(128, activation='relu')(combined)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    output = tf.keras.layers.Dense(1, activation='sigmoid', name='success_prob')(x)

    model = tf.keras.Model(
        inputs=[requester_input, target_input, context_input],
        outputs=output
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy', 'AUC']
    )

    return model
```

### Phase 3: Personalized Ranking

**Objective**: Adapt rankings to individual user preferences

**Approach**: Matrix Factorization + Feature-based Hybrid

**Model**: Factorization Machines

```python
import tensorflow as tf

def build_factorization_machine(num_features, embedding_dim=10):
    """
    FM captures both linear and pairwise interactions between features.
    """

    # Input
    inputs = tf.keras.Input(shape=(num_features,))

    # Linear part
    linear = tf.keras.layers.Dense(1, use_bias=True)(inputs)

    # Factorization part (pairwise interactions)
    embeddings = tf.keras.layers.Dense(embedding_dim)(inputs)

    # Sum of squares
    sum_of_squares = tf.reduce_sum(tf.square(embeddings), axis=1, keepdims=True)

    # Square of sum
    square_of_sum = tf.square(tf.reduce_sum(embeddings, axis=1, keepdims=True))

    # Pairwise interactions
    interactions = 0.5 * (square_of_sum - sum_of_squares)

    # Combine
    output = linear + interactions
    output = tf.keras.layers.Activation('sigmoid')(output)

    model = tf.keras.Model(inputs=inputs, outputs=output)
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['AUC']
    )

    return model
```

## Data Export for Training

### Export Function

```python
async def export_training_dataset(
    limit: Optional[int] = None,
    min_date: Optional[datetime] = None,
    include_features: bool = True
) -> pd.DataFrame:
    """
    Export RLHF data as training dataset.

    Returns:
        DataFrame with features and target variable
    """

    # Query all completed introductions with outcomes
    query = {
        "status": {"$in": ["accepted", "declined", "completed", "expired"]},
    }

    if min_date:
        query["created_at"] = {"$gte": min_date.isoformat()}

    intros = await zerodb_client.query_rows(
        table_name="introductions",
        filter=query,
        limit=limit or 10000,
        sort={"created_at": -1}
    )

    # Build feature matrix
    records = []
    for intro in intros:
        # Get RLHF data
        rlhf_data = await get_intro_rlhf_data(intro["id"])

        # Get user profiles
        requester = await zerodb_client.get_by_id("users", intro["requester_id"])
        target = await zerodb_client.get_by_id("users", intro["target_id"])

        # Extract match scores from intro context
        match_scores = intro.get("context", {}).get("match_scores", {})
        matching_context = intro.get("context", {}).get("matching_context", {})

        # Build feature record
        record = {
            # ID
            "intro_id": intro["id"],

            # Match scores
            "relevance_score": match_scores.get("relevance", 0.5),
            "trust_score": match_scores.get("trust", 0.5),
            "reciprocity_score": match_scores.get("reciprocity", 0.5),
            "overall_score": match_scores.get("overall", 0.5),

            # Matching context
            "num_goal_matches": len(matching_context.get("goal_matches", [])),
            "num_ask_matches": len(matching_context.get("ask_matches", [])),
            "top_similarity": matching_context.get("top_similarity", 0.0),
            "match_type": matching_context.get("match_type", "unknown"),

            # Profile features
            "requester_has_linkedin": requester.get("linkedin_id") is not None,
            "target_has_linkedin": target.get("linkedin_id") is not None,
            "requester_account_age_days": calculate_account_age(requester),
            "target_account_age_days": calculate_account_age(target),

            # Geographic
            "same_country": requester.get("country") == target.get("country"),

            # Target variable
            "success": calculate_success_binary(intro, rlhf_data),
            "success_score": calculate_success_score(intro, rlhf_data),

            # Metadata
            "created_at": intro["created_at"],
            "outcome_type": intro.get("outcome"),
            "rating": rlhf_data.get("rating")
        }

        records.append(record)

    df = pd.DataFrame(records)
    return df
```

### Data Splitting Strategy

```python
from sklearn.model_selection import train_test_split

def prepare_train_test_split(df, test_size=0.2, time_based=True):
    """
    Split data into train/validation/test sets.

    Args:
        df: Full dataset
        test_size: Proportion for test set
        time_based: If True, use temporal split (more realistic)

    Returns:
        train_df, val_df, test_df
    """

    if time_based:
        # Sort by time
        df = df.sort_values('created_at')

        # Split: 60% train, 20% val, 20% test (chronological)
        n = len(df)
        train_end = int(n * 0.6)
        val_end = int(n * 0.8)

        train_df = df[:train_end]
        val_df = df[train_end:val_end]
        test_df = df[val_end:]

    else:
        # Random split (less realistic but useful for testing)
        train_val_df, test_df = train_test_split(
            df, test_size=test_size, random_state=42, stratify=df['success']
        )

        train_df, val_df = train_test_split(
            train_val_df, test_size=0.25, random_state=42, stratify=train_val_df['success']
        )

    return train_df, val_df, test_df
```

## Model Evaluation

### Metrics

```python
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, average_precision_score,
    confusion_matrix, classification_report
)

def evaluate_model(model, X_test, y_test):
    """Comprehensive model evaluation."""

    # Predictions
    y_pred_proba = model.predict(X_test)
    y_pred = (y_pred_proba > 0.5).astype(int)

    # Metrics
    metrics = {
        # Classification metrics
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),

        # Ranking metrics
        "auc_roc": roc_auc_score(y_test, y_pred_proba),
        "auc_pr": average_precision_score(y_test, y_pred_proba),

        # Business metrics
        "success_rate_top_20pct": calculate_success_at_k(y_test, y_pred_proba, k=0.2),
        "success_rate_top_50pct": calculate_success_at_k(y_test, y_pred_proba, k=0.5),

        # Calibration
        "brier_score": brier_score_loss(y_test, y_pred_proba)
    }

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)

    return metrics, cm

def calculate_success_at_k(y_true, y_scores, k=0.2):
    """
    Calculate success rate for top k% of predicted scores.
    This is the key business metric.
    """
    n_top = int(len(y_scores) * k)
    top_indices = np.argsort(y_scores)[-n_top:]
    return y_true.iloc[top_indices].mean()
```

### Success Criteria

**Minimum Viable Model**:
- AUC-ROC > 0.70
- Success@20% > 70% (top 20% of predictions have 70%+ success rate)
- Better than rule-based baseline by 5%+

**Production-Ready Model**:
- AUC-ROC > 0.75
- Success@20% > 75%
- Better than baseline by 10%+
- Calibrated predictions (Brier score < 0.20)

**Excellent Model**:
- AUC-ROC > 0.80
- Success@20% > 80%
- Better than baseline by 15%+
- Calibrated predictions (Brier score < 0.15)

## A/B Testing Framework

### Test Design

```python
class ABTestConfig:
    """Configuration for introduction matching A/B test."""

    # Test parameters
    name = "ml_ranking_v1"
    start_date = "2025-01-15"
    end_date = "2025-02-15"

    # Traffic allocation
    control_pct = 0.5   # 50% get rule-based algorithm
    treatment_pct = 0.5  # 50% get ML algorithm

    # Randomization
    random_seed = 42
    user_level = True  # Consistent experience per user

    # Metrics
    primary_metric = "success_rate"
    secondary_metrics = ["response_rate", "time_to_completion", "rating"]
    guardrail_metrics = ["suggestion_volume", "acceptance_rate"]

    # Success criteria
    min_sample_size = 200  # per group
    min_effect_size = 0.05  # 5% relative improvement
    significance_level = 0.05  # p < 0.05
```

### Assignment Logic

```python
import hashlib

def assign_ab_group(user_id: UUID, test_config: ABTestConfig) -> str:
    """
    Assign user to A/B test group deterministically.

    Args:
        user_id: User UUID
        test_config: Test configuration

    Returns:
        "control" or "treatment"
    """
    # Hash user ID for deterministic assignment
    hash_input = f"{user_id}:{test_config.random_seed}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

    # Assign based on hash
    assignment_value = (hash_value % 100) / 100.0

    if assignment_value < test_config.control_pct:
        return "control"
    else:
        return "treatment"

async def get_match_suggestions(user_id: UUID, limit: int = 20):
    """
    Get introduction suggestions using A/B test logic.
    """

    # Check if A/B test is active
    active_test = await get_active_ab_test()

    if not active_test:
        # No active test, use default algorithm
        return await matching_service.suggest_introductions(user_id, limit)

    # Assign to group
    group = assign_ab_group(user_id, active_test)

    # Log assignment
    await log_ab_assignment(user_id, active_test.name, group)

    if group == "control":
        # Use rule-based algorithm
        suggestions = await matching_service.suggest_introductions(user_id, limit)
    else:
        # Use ML algorithm
        suggestions = await ml_ranking_service.suggest_introductions(user_id, limit)

    return suggestions
```

### Analysis

```python
from scipy import stats

def analyze_ab_test(test_name: str) -> Dict[str, Any]:
    """
    Analyze A/B test results with statistical significance.
    """

    # Get data for both groups
    control_data = get_ab_test_data(test_name, "control")
    treatment_data = get_ab_test_data(test_name, "treatment")

    # Primary metric: success rate
    control_success_rate = control_data['success'].mean()
    treatment_success_rate = treatment_data['success'].mean()

    # Statistical test (two-proportion z-test)
    n_control = len(control_data)
    n_treatment = len(treatment_data)

    successes_control = control_data['success'].sum()
    successes_treatment = treatment_data['success'].sum()

    # Z-test
    p_value = proportions_ztest(
        [successes_treatment, successes_control],
        [n_treatment, n_control]
    )[1]

    # Effect size
    absolute_lift = treatment_success_rate - control_success_rate
    relative_lift = absolute_lift / control_success_rate

    # Confidence interval (95%)
    ci_lower, ci_upper = proportion_confint(
        successes_treatment,
        n_treatment,
        alpha=0.05,
        method='wilson'
    )

    results = {
        "test_name": test_name,
        "sample_size_control": n_control,
        "sample_size_treatment": n_treatment,

        "control_success_rate": control_success_rate,
        "treatment_success_rate": treatment_success_rate,

        "absolute_lift": absolute_lift,
        "relative_lift": relative_lift,
        "relative_lift_pct": f"{relative_lift * 100:.1f}%",

        "p_value": p_value,
        "is_significant": p_value < 0.05,

        "confidence_interval_95": (ci_lower, ci_upper),

        "recommendation": get_test_recommendation(
            p_value, relative_lift, n_treatment, n_control
        )
    }

    return results

def get_test_recommendation(p_value, relative_lift, n_treatment, n_control):
    """Generate recommendation based on test results."""

    min_sample = 200
    min_lift = 0.05

    if n_treatment < min_sample or n_control < min_sample:
        return "CONTINUE: Need more data (min 200 per group)"

    if p_value < 0.05 and relative_lift > min_lift:
        return "SHIP: Statistically significant improvement, roll out to 100%"
    elif p_value < 0.05 and relative_lift < -0.02:
        return "STOP: Statistically significant degradation, revert to control"
    elif p_value >= 0.05:
        return "INCONCLUSIVE: No significant difference detected"
    else:
        return "CONTINUE: Positive trend but need more confidence"
```

## Model Deployment

### Model Serving Architecture

```
User Request
    |
    v
[API Gateway]
    |
    v
[Matching Service]
    |
    +---> [Feature Extraction]
    |
    +---> [Model Inference]
    |     - Load model from S3/GCS
    |     - Batch predictions
    |     - Cache results
    |
    +---> [Re-ranking]
    |
    v
Return Top N Suggestions
```

### Model Versioning

```python
class ModelRegistry:
    """Manage model versions and deployments."""

    def __init__(self):
        self.models = {}
        self.active_version = None

    async def register_model(
        self,
        version: str,
        model_path: str,
        metrics: Dict[str, float],
        metadata: Dict[str, Any]
    ):
        """Register a new model version."""

        model_info = {
            "version": version,
            "path": model_path,
            "metrics": metrics,
            "metadata": metadata,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "registered"
        }

        # Store in ZeroDB
        await zerodb_client.insert_rows(
            "ml_models",
            [model_info]
        )

        self.models[version] = model_info

    async def deploy_model(self, version: str):
        """Deploy a model version to production."""

        # Load model
        model_info = self.models.get(version)
        if not model_info:
            raise ValueError(f"Model version {version} not found")

        # Download from storage
        model = self.load_model_from_storage(model_info["path"])

        # Validate model
        self.validate_model(model)

        # Update active version
        self.active_version = version

        # Log deployment
        await self.log_deployment(version)

    async def rollback(self, to_version: str):
        """Rollback to previous model version."""

        logger.warning(f"Rolling back from {self.active_version} to {to_version}")
        await self.deploy_model(to_version)
```

### Inference Service

```python
class MLRankingService:
    """ML-powered introduction ranking service."""

    def __init__(self):
        self.model = None
        self.feature_extractor = FeatureExtractor()

    async def suggest_introductions(
        self,
        user_id: UUID,
        limit: int = 20
    ) -> List[Dict]:
        """
        Generate ML-ranked introduction suggestions.
        """

        # Step 1: Get candidates (same as rule-based)
        candidates = await matching_service._find_candidates(
            user_id=user_id,
            user_goals=await get_user_goals(user_id),
            user_asks=await get_user_asks(user_id),
            match_type="all"
        )

        if not candidates:
            return []

        # Step 2: Extract features for all candidates
        features = await self.feature_extractor.extract_batch(
            user_id, candidates
        )

        # Step 3: ML model prediction
        scores = self.model.predict_proba(features)[:, 1]  # Probability of success

        # Step 4: Rank by ML score
        ranked_indices = np.argsort(scores)[::-1]

        # Step 5: Format results
        suggestions = []
        for idx in ranked_indices[:limit]:
            candidate = candidates[idx]

            suggestions.append({
                "target_user_id": candidate["user_id"],
                "ml_score": float(scores[idx]),
                "match_score": {
                    "relevance_score": features[idx]["relevance_score"],
                    "trust_score": features[idx]["trust_score"],
                    "reciprocity_score": features[idx]["reciprocity_score"],
                    "overall_score": float(scores[idx])  # Use ML score as overall
                },
                "reasoning": await self.generate_reasoning(candidate, features[idx])
            })

        return suggestions
```

## Continuous Training Pipeline

### Training Schedule

```python
class TrainingSchedule:
    """Automated model retraining schedule."""

    # Weekly retraining (every Monday at 2 AM UTC)
    WEEKLY_SCHEDULE = "0 2 * * 1"

    # Monthly full retraining (first day of month)
    MONTHLY_SCHEDULE = "0 2 1 * *"

    async def weekly_retrain(self):
        """Incremental retraining with new data."""

        # Get new data since last training
        last_train_date = await get_last_training_date()
        new_data = await export_training_dataset(min_date=last_train_date)

        if len(new_data) < 50:
            logger.info("Not enough new data, skipping retraining")
            return

        # Load existing model
        current_model = self.load_current_model()

        # Incremental training
        updated_model = current_model.refit(new_data)

        # Evaluate on validation set
        metrics = evaluate_model(updated_model, val_X, val_y)

        # Register new version
        new_version = f"v{datetime.utcnow().strftime('%Y%m%d')}"
        await model_registry.register_model(
            version=new_version,
            model_path=self.save_model(updated_model),
            metrics=metrics,
            metadata={"training_type": "incremental"}
        )

        # Auto-deploy if improvement > 2%
        if metrics["auc_roc"] > current_metrics["auc_roc"] * 1.02:
            await model_registry.deploy_model(new_version)

    async def monthly_full_retrain(self):
        """Full retraining from scratch."""

        # Get all historical data
        full_data = await export_training_dataset(limit=10000)

        # Train new model from scratch
        train_df, val_df, test_df = prepare_train_test_split(full_data)

        new_model = train_model(train_df)

        # Comprehensive evaluation
        metrics = evaluate_model(new_model, test_df)

        # Register
        new_version = f"v{datetime.utcnow().strftime('%Y%m')}_full"
        await model_registry.register_model(
            version=new_version,
            model_path=self.save_model(new_model),
            metrics=metrics,
            metadata={"training_type": "full"}
        )

        # Deploy via staged rollout
        await self.staged_rollout(new_version)
```

## Monitoring and Alerts

### Model Performance Monitoring

```python
class ModelMonitor:
    """Monitor ML model performance in production."""

    async def check_model_health(self):
        """Daily health check."""

        # Get recent predictions and outcomes
        recent_data = await get_recent_introductions(days=7)

        # Calculate actual success rate
        actual_success_rate = recent_data['success'].mean()

        # Compare to baseline
        baseline_success_rate = await get_baseline_success_rate()

        # Alert if degradation
        if actual_success_rate < baseline_success_rate * 0.9:
            await alert(
                severity="HIGH",
                message=f"Model performance degraded: {actual_success_rate:.2%} < {baseline_success_rate:.2%}"
            )

    async def check_prediction_drift(self):
        """Detect distribution drift in predictions."""

        # Get recent prediction distribution
        recent_preds = await get_recent_predictions(days=7)

        # Compare to training distribution
        training_dist = await get_training_distribution()

        # KL divergence
        kl_div = calculate_kl_divergence(recent_preds, training_dist)

        if kl_div > 0.1:  # Threshold
            await alert(
                severity="MEDIUM",
                message=f"Prediction drift detected: KL={kl_div:.3f}"
            )

    async def check_feature_drift(self):
        """Detect drift in input features."""

        # Get recent feature distributions
        recent_features = await get_recent_features(days=7)

        # Compare each feature to training baseline
        for feature in recent_features.columns:
            drift_score = calculate_drift_score(
                recent_features[feature],
                training_baseline[feature]
            )

            if drift_score > 0.05:
                await alert(
                    severity="LOW",
                    message=f"Feature drift in {feature}: {drift_score:.3f}"
                )
```

## Model Interpretation

### Feature Importance

```python
import shap

def explain_predictions(model, X_test):
    """Generate SHAP explanations for model predictions."""

    # Create SHAP explainer
    explainer = shap.TreeExplainer(model)

    # Calculate SHAP values
    shap_values = explainer.shap_values(X_test)

    # Summary plot (global importance)
    shap.summary_plot(shap_values, X_test, plot_type="bar")

    # Feature importance ranking
    feature_importance = pd.DataFrame({
        'feature': X_test.columns,
        'importance': np.abs(shap_values).mean(axis=0)
    }).sort_values('importance', ascending=False)

    return feature_importance

def explain_individual_prediction(model, features, feature_names):
    """Explain why a specific introduction was suggested."""

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)

    # Force plot for individual prediction
    shap.force_plot(
        explainer.expected_value[1],
        shap_values[1],
        features,
        feature_names=feature_names
    )

    # Text explanation
    top_factors = get_top_contributing_factors(shap_values[1], feature_names, top_k=3)

    explanation = f"This introduction was suggested because:\n"
    for factor, contribution in top_factors:
        explanation += f"- {factor}: {contribution:+.2f}\n"

    return explanation
```

## Next Steps

1. **Month 1**: Data collection and baseline establishment
2. **Month 2**: Feature engineering and initial model training
3. **Month 3**: A/B testing and validation
4. **Month 4**: Production deployment and monitoring
5. **Month 5+**: Continuous improvement and optimization

---

**Document Version**: 1.0
**Last Updated**: 2025-12-13
**Owner**: ML Engineering Team
**Review Cycle**: Quarterly
