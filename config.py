import os

#For storing live tracking stats
adsb_history_enabled = os.getenv("ADSB_HISTORY_ENABLED", "false").lower() == "true"

#PostgreSQL vs SQLite support. Default is SQLite
postgres_enabled = os.getenv("POSTGRES_ENABLED", "false").lower() == "true"

#not used if postgres_enabled = False
postgres_server = os.getenv('POSTGRES_SERVER','localhost')
postgres_port = int(os.getenv('POSTGRES_PORT',5432))
postgres_db = os.getenv('POSTGRES_DATABASE','aero-alerts')
postgres_user = os.getenv('POSTGRES_USER','aero-user')
postgres_password = os.getenv('POSTGRES_PASSWORD','aero-pass')

#Save location for database - only used for sqlite
adsb_save_folder = os.getenv('ADSB_SAVE_FOLDER','/data')

logging_level = os.getenv('LOG_LEVEL', 'INFO').upper()

# pi-aware local JSON feed with cleansed input
live_data_url = os.getenv('LIVE_DATA_URL','http://adsbexchange.local/tar1090/data/aircraft.json')

# antenna location
my_lat = float(os.getenv('MY_LAT'))
my_lon = float(os.getenv('MY_LON'))

# distance threshold for posting aircraft
airspace_radius_km = int(os.getenv('AIRSPACE_RADIUS_KM',10))
# distance threshold for tracking aircraft
record_radius_km = int(os.getenv('RECORD_RADIUS_KM',100))

#Time to wait between polling the antenna data (seconds)
sleep_time = int(os.getenv('SLEEP_TIME',10))
#Time to wait after recording an aircraft before re-posting it
aircraft_debounce = int(os.getenv('AIRCRAFT_DEBOUNCE',3600))

#Monthly spend limit for AeroAPI
aeroapi_enabled = os.getenv("AEROAPI_ENABLED", "false").lower() == "true"
aeroapi_limit = float(os.getenv('AEROAPI_LIMIT',0))
aero_api_key = os.getenv('AEROAPI_KEY','')

#Bluesky posting settings
bsky_post_enabled = os.getenv("BSKY_POST_ENABLED", "false").lower() == "true"
bsky_account = os.getenv('BSKY_ACCOUNT','')
bsky_app_pass = os.getenv('BSKY_APP_PASS','')
#Oldest allowed age of a detected flight to post if it joins our airspace
bsky_post_lag = int(os.getenv('BSKY_POST_LAG',1800))

#Azure storage account details. Relevant if history enabled and sqlite used
azure_backup_enabled = os.getenv("AZ_BACKUP_ENABLED", "false").lower() == "true"
azure_storage_account_url = os.getenv('AZ_STORAGE_ACCOUNT_URL',' ')
azure_storage_account_key = os.getenv('AZ_STORAGE_ACCOUNT_KEY',' ')
azure_storage_container_name = os.getenv('AZ_CONTAINER_NAME',' ')
azure_storage_subfolder = os.getenv('AZ_CONTAINER_FOLDER',' ')
