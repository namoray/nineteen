# Table names
HOTKEY_INFO_TABLE = "hotkey_info"
AXON_INFO_TABLE = "axon_info"
AXON_INFO_HISTORY_TABLE = "axon_info_history"
PARTICIPANTS_TABLE = "participants"
PARTICIPANTS_HISTORY_TABLE = "participants_history"

TABLE_TASKS = "tasks"
TABLE_REWARD_DATA = "reward_data"
TABLE_UID_RECORDS = "uid_records"


######## Column names ###########

# Hotkey info table
HOTKEY = "hotkey"
AXON_IP = "axon_ip"
UID = "uid"

# Axon info table
AXON_VERSION = "axon_version"
IP = "ip"
PORT = "port"
IP_TYPE = "ip_type"
HOTKEY = "hotkey"
COLDKEY = "coldkey"
AXON_UID = "axon_uid"
INCENTIVE = "incentive"
NETUID = "netuid"
NETWORK = "network"
STAKE = "stake"
CREATED_AT = "created_at"


# Axon Info history table

# AXON_VERSION = "axon_version"
# IP = "ip"
# PORT = "port"
# IP_TYPE = "ip_type"
# HOTKEY = "hotkey"
# COLDKEY = "coldkey"
# AXON_UID = "axon_uid"
# NETUID = "netuid"
# NETWORK = "network"
# STAKE = "stake"
# CREATED_AT = "created_at"
EXPIRED_AT = "expired_at"

# Participants table
PARTICIPANT_ID = "participant_id"
MINER_HOTKEY = "miner_hotkey"
TASK = "task"
VALIDATOR_HOTKEY = "validator_hotkey"
CAPACITY = "capacity"
CAPACITY_TO_SCORE = "capacity_to_score"
CONSUMED_CAPACITY = "consumed_capacity"
DELAY_BETWEEN_SYNTHETIC_REQUESTS = "delay_between_synthetic_requests"
SYNTHETIC_REQUESTS_STILL_TO_MAKE = "synthetic_requests_still_to_make"
TOTAL_REQUESTS_MADE = "total_requests_made"
REQUESTS_429 = "requests_429"
REQUESTS_500 = "requests_500"
RAW_CAPACITY = "raw_capacity"
PERIOD_SCORE = "period_score"
CREATED_AT = "created_at"
UPDATED_AT = "updated_at"

# Participants history table

# PARTICIPANT_ID = "participant_id"
# MINER_HOTKEY = "miner_hotkey"
# TASK = "task"
# VALIDATOR_HOTKEY = "validator_hotkey"
# CAPACITY = "capacity"
# CAPACITY_TO_SCORE = "capacity_to_score"
# CONSUMED_CAPACITY = "consumed_capacity"
# DELAY_BETWEEN_SYNTHETIC_REQUESTS = "delay_between_synthetic_requests"
# SYNTHETIC_REQUESTS_STILL_TO_MAKE = "synthetic_requests_still_to_make"
# TOTAL_REQUESTS_MADE = "total_requests_made"
# REQUESTS_429 = "requests_429"
# REQUESTS_500 = "requests_500"
# RAW_CAPACITY = "raw_capacity"
# PERIOD_SCORE = "period_score"
# CREATED_AT = "created_at"
# UPDATED_AT = "updated_at"
EXPIRED_AT = "expired_at"


# Common column names
COLUMN_ID = "id"
COLUMN_CREATED_AT = "created_at"
COLUMN_MINER_HOTKEY = "miner_hotkey"

# `tasks` table column names
COLUMN_TASK_NAME = "task_name"
COLUMN_CHECKING_DATA = "checking_data"

# `reward_data` table column names
COLUMN_TASK = "task"
COLUMN_AXON_UID = "axon_uid"
COLUMN_QUALITY_SCORE = "quality_score"
COLUMN_VALIDATOR_HOTKEY = "validator_hotkey"
COLUMN_SYNTHETIC_QUERY = "synthetic_query"
COLUMN_SPEED_SCORING_FACTOR = "speed_scoring_factor"
COLUMN_RESPONSE_TIME = "response_time"
COLUMN_VOLUME = "volume"

# UID record columns
COLUMN_DECLARED_VOLUME = "declared_volume"
COLUMN_CONSUMED_VOLUME = "consumed_volume"
COLUMN_TOTAL_REQUESTS_MADE = "total_requests_made"
COLUMN_REQUESTS_429 = "requests_429"
COLUMN_REQUESTS_500 = "requests_500"
COLUMN_PERIOD_SCORE = "period_score"
