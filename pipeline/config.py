"""Every constant of the Glidepath pipeline."""

# Airport reference (EDDF)
REF_LAT = 50.0333
REF_LON = 8.5706
EARTH_RADIUS_NM = 3440.065
FIELD_ELEV_M = 111.0
MS_TO_KT = 1.943844
LOCAL_TZ = "Europe/Berlin"

# Flights and touchdown labels
FLIGHT_GAP_S = 15 * 60
MIN_POINTS = 20
ARRIVAL_START_NM = 30.0
GROUND_NM = 5.0
MIDPOINT_MAX_GAP_S = 60.0
DESCENT_THRESHOLD_MS = -1.0
DEFAULT_DESCENT_MS = 3.7
EXTRAP_CAP_S = 120.0
FALLBACK_MAX_ALT_M = 600.0
FALLBACK_REJECT_NM = 8.0
INNER_GAP_NM = 20.0
INNER_MAX_GAP_S = 120.0
DIRECTION_NM = 8.0
RUNWAY_HEADINGS = {"25": 249.0, "07": 69.0}
DIRECTION_TOL_DEG = 45.0
GO_AROUND_NM = 15.0
GO_AROUND_CLIMB_M = 250.0
MAX_Y_S = 3 * 3600
MAX_DISTANCE_NM = 150.0

# Features
LAGS_S = (60, 120)
LAG_TOL_S = 45.0
TURN_WINDOW_S = 300.0
TURN_STEP_MAX_S = 60.0
HOLDING_TURN_DEG = 300.0
DIRECTION_LAST_N = 3
DIRECTION_CODES = {"25": 1, "07": 0}
TRAFFIC_BUCKET_S = 30
TRAFFIC_RADII_NM = (20, 50, 100)
LANDINGS_WINDOW_S = 30 * 60
BAND_EDGES_NM = (0.0, 20.0, 50.0, 100.0, float("inf"))
BAND_LABELS = ("0 to 20 nm", "20 to 50 nm", "50 to 100 nm", "over 100 nm")

TRAFFIC_FEATURES = ["traffic_20", "traffic_50", "traffic_100", "distance_rank",
                    "landings_30min"]
DIRECTION_FEATURES = ["direction_code"]
FEATURES = [
    "distance_nm", "bearing_sin", "bearing_cos", "alt_m", "gs_kt", "vrate_ms",
    "course_offset_deg", "speed_toward_kt",
    "d_alt_60", "d_alt_120", "d_gs_60", "d_gs_120",
    "turn_5min_deg", "holding",
    *DIRECTION_FEATURES, *TRAFFIC_FEATURES,
    "local_hour", "category",
]

# Splits
MIN_SPLIT_DAYS = 3
MIN_ARRIVALS_PER_DAY = 150
TRAIN_FRAC = 0.6
CAL_FRAC = 0.2

# Models
BASELINE_A_MIN_KT = 100.0
BASELINE_B_BIN_NM = 5.0
BASELINE_B_MIN_ROWS = 30
QUANTILES = (0.1, 0.5, 0.9)
LGB_PARAMS = {
    "objective": "quantile",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 40,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.9,
    "verbose": -1,
}
LGB_MAX_ROUNDS = 5000
EARLY_STOPPING_ROUNDS = 100
VALID_FLIGHT_FRAC = 0.2
SEED = 7
ALPHA = 0.2
CQR_MIN_BAND_ROWS = 20

# Evaluation
WINDOWS_MIN = (2, 5, 10)
MAIN_WINDOW_MIN = 5
HORIZONS_NM = (100, 50, 20)
N_BOOT = 10_000
H1_MIN_TEST_ROWS = 50
H1_TOLERANCE = 0.05
H4_MIN_HOLDING_FLIGHTS = 5
H3_MIN_FLIGHTS = 5
SHAP_MAX_ROWS = 5000
SHAP_TOP = 10
REPLAY_STEP_S = 30

# Figure colors
COLOR_MODEL = "#2a78d6"
COLOR_BASELINE_B = "#eb6834"
COLOR_UNCAL = "#eda100"
COLOR_BASELINE_A = "#52514e"
COLOR_GRID = "#d9d9d9"
FIG_DPI = 150

SYNTHETIC_LABEL = "SYNTHETIC TEST"
