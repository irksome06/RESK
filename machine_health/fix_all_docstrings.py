with open('generate_notebook.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all occurrences of function docstrings in code cells:
docstrings_to_replace = [
    ('''def compute_engineered_vibration_features(df_features: pd.DataFrame) -> pd.DataFrame:
    """
    Computes domain-grounded dimensionless indicators from vibration features.
    Strictly uses information available at inference time without lookahead leakage.
    """''',
     '''def compute_engineered_vibration_features(df_features: pd.DataFrame) -> pd.DataFrame:
    # Computes domain-grounded dimensionless indicators from vibration features.
    # Strictly uses information available at inference time without lookahead leakage.'''
    ),
    ('''def create_random_forest_pipeline(random_state: int = RANDOM_STATE) -> Pipeline:
    """
    Constructs a leakage-safe Pipeline for Random Forest classification.
    Uses SimpleImputer for robustness, leaving features unscaled since decision trees
    are invariant to monotonic feature scaling.
    """''',
     '''def create_random_forest_pipeline(random_state: int = RANDOM_STATE) -> Pipeline:
    # Constructs a leakage-safe Pipeline for Random Forest classification.
    # Uses SimpleImputer for robustness, leaving features unscaled since decision trees
    # are invariant to monotonic feature scaling.'''
    ),
    ('''def create_svm_pipeline(random_state: int = RANDOM_STATE) -> Pipeline:
    """
    Constructs a leakage-safe Pipeline for SVM classification.
    StandardScaler is strictly embedded inside the pipeline to guarantee that
    mean and variance are learned solely from training folds, eliminating data leakage.
    """''',
     '''def create_svm_pipeline(random_state: int = RANDOM_STATE) -> Pipeline:
    # Constructs a leakage-safe Pipeline for SVM classification.
    # StandardScaler is strictly embedded inside the pipeline to guarantee that
    # mean and variance are learned solely from training folds, eliminating data leakage.'''
    ),
    ('''class IntelligentSleepModeController:
    """
    Industrial decision framework for energy-efficient machine sleep mode.
    Demonstrates why multi-modal sensor inputs (current, RPM, load, thermal status)
    are strictly required before an automated shutdown/sleep command can be issued.
    """''',
     '''class IntelligentSleepModeController:
    # Industrial decision framework for energy-efficient machine sleep mode.
    # Demonstrates why multi-modal sensor inputs (current, RPM, load, thermal status)
    # are strictly required before an automated shutdown/sleep command can be issued.'''
    ),
    ('''    def evaluate_sleep_eligibility(
        self,
        vibration_anomaly_flag: int,
        motor_current_amps: float,
        motor_rpm: float,
        motor_torque_nm: float,
        bearing_temp_c: float,
        idle_duration_seconds: float,
        production_starved: bool,
        safety_interlocks_ok: bool
    ) -> dict:
        """
        Evaluates machine operational state and determines sleep-mode qualification.
        """''',
     '''    def evaluate_sleep_eligibility(
        self,
        vibration_anomaly_flag: int,
        motor_current_amps: float,
        motor_rpm: float,
        motor_torque_nm: float,
        bearing_temp_c: float,
        idle_duration_seconds: float,
        production_starved: bool,
        safety_interlocks_ok: bool
    ) -> dict:
        # Evaluates machine operational state and determines sleep-mode qualification.'''
    ),
    ('''class VibrationConditionMonitoringService:
    """
    Production-grade inference service for real-time condition monitoring.
    Accepts raw vibration window features, validates schema, applies feature engineering,
    and returns a structured health diagnostic assessment.
    """''',
     '''class VibrationConditionMonitoringService:
    # Production-grade inference service for real-time condition monitoring.
    # Accepts raw vibration window features, validates schema, applies feature engineering,
    # and returns a structured health diagnostic assessment.'''
    ),
    ('''    def predict_window(self, input_data: dict) -> dict:
        """
        Processes a single vibration window dictionary and produces health assessment.
        """''',
     '''    def predict_window(self, input_data: dict) -> dict:
        # Processes a single vibration window dictionary and produces health assessment.'''
    ),
    ('''def validate_dataset_schema(
    dataframe: pd.DataFrame,
    expected_features: list,
    expected_metadata: list
) -> bool:
    '''
    Validates that the input DataFrame strictly adheres to the condition monitoring schema.
    Raises ValueError or TypeError if columns are missing or have invalid datatypes.
    ''' ''',
     '''def validate_dataset_schema(
    dataframe: pd.DataFrame,
    expected_features: list,
    expected_metadata: list
) -> bool:
    # Validates that the input DataFrame strictly adheres to the condition monitoring schema.
    # Raises ValueError or TypeError if columns are missing or have invalid datatypes.'''
    )
]

for old, new in docstrings_to_replace:
    text = text.replace(old, new)

with open('generate_notebook.py', 'w', encoding='utf-8') as f:
    f.write(text)

import py_compile
try:
    py_compile.compile('generate_notebook.py', doraise=True)
    print("SUCCESS! generate_notebook.py compiled with zero syntax errors!")
except py_compile.PyCompileError as e:
    print("Compile Error:", e)
