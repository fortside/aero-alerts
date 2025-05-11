import config
import os

if config.postgres_enabled:
    db_name = config.postgres_db
else:
    db = "aero_alerts.db"
    db_name = os.path.normpath(os.path.join(config.adsb_save_folder, db))

home = (config.my_lat, config.my_lon)

# basic conversions
knots_to_kph = 1.852
meters_to_feet = 3.28084

csv_header = ['Timestamp', 'Hex', 'Type', 'Flight','Altitude','Groundspeed','Track','Lat','Lon','FlightID']

#ADSBDB endpoints
adsbdb_aircraft_url = "https://api.adsbdb.com/v0/aircraft/"
adsbdb_callsign_url = "https://api.adsbdb.com/v0/callsign/"

#HexDB.io endpoints
hexdb_aircraft_url = "https://hexdb.io/api/v1/aircraft/"
hexdb_route_url = "https://hexdb.io/api/v1/route/icao/"
hexdb_airport_url = "https://hexdb.io/api/v1/airport/icao/"

#FlightAware AeroAPI endpoints
aero_aircraftowner_url = "https://aeroapi.flightaware.com/aeroapi/aircraft/z_ident_z/owner"
aero_flightroute_url = "https://aeroapi.flightaware.com/aeroapi/flights/"
aero_monthlyusage = "https://aeroapi.flightaware.com/aeroapi/account/usage"
aero_airport_url = "https://aeroapi.flightaware.com/aeroapi/airports/"

#sqlite syntax
flights_table_sqlite =   "Create table if not exists flights (" \
                    "id integer primary key" \
                    ", timestamp integer" \
                    ", icao_hex text" \
                    ", flight text" \
                    ", altitude integer" \
                    ", speed real" \
                    ", lat real" \
                    ", lon real" \
                    ", distance real" \
                    ", heading integer" \
                    ", bearing integer" \
                    ", squawk text" \
                    ", emergency text" \
                    ", airline_name text" \
                    ", airline_country text" \
                    ", origin_icao text" \
                    ", dest_icao text" \
                    ", flightroute_source text" \
                    ", bsky_post integer" \
                    ")"

airports_table_sqlite = "Create table if not exists airports (" \
                "id integer primary key" \
                ", code_icao text unique" \
                ", code_iata text" \
                ", name text" \
                ", type text" \
                ", city text" \
                ", state text" \
                ", lat real" \
                ", lon real" \
                ", country_code text" \
                ", timestamp integer" \
                ")"

registrations_table_sqlite = "Create table if not exists registrations (" \
                "id integer primary key" \
                ", timestamp integer" \
                ", icao_hex text unique" \
                ", registration text" \
                ", model text" \
                ", manufacturer text" \
                ", owner_name text" \
                ", owner_country text" \
                ", source text" \
                ")"

#postgres syntax
flights_table_postgres =   "Create table if not exists flights (" \
                    "id serial primary key" \
                    ", timestamp integer" \
                    ", icao_hex varchar" \
                    ", flight varchar" \
                    ", altitude integer" \
                    ", speed numeric" \
                    ", lat numeric" \
                    ", lon numeric" \
                    ", distance numeric" \
                    ", heading integer" \
                    ", bearing integer" \
                    ", squawk varchar" \
                    ", emergency varchar" \
                    ", airline_name varchar" \
                    ", airline_country varchar" \
                    ", origin_icao varchar" \
                    ", dest_icao varchar" \
                    ", flightroute_source varchar" \
                    ", bsky_post integer" \
                    ")"

airports_table_postgres = "Create table if not exists airports (" \
                "id serial primary key" \
                ", code_icao varchar unique" \
                ", code_iata varchar" \
                ", name varchar" \
                ", type varchar" \
                ", city varchar" \
                ", state varchar" \
                ", lat numeric" \
                ", lon numeric" \
                ", country_code varchar" \
                ", timestamp integer" \
                ")"

registrations_table_postgres = "Create table if not exists registrations (" \
                "id serial primary key" \
                ", timestamp integer" \
                ", icao_hex varchar unique" \
                ", registration varchar" \
                ", model varchar" \
                ", manufacturer varchar" \
                ", owner_name varchar" \
                ", owner_country varchar" \
                ", source varchar" \
                ")"

tracks_table_postgres = "Create table if not exists tracks (" \
                "id serial primary key" \
                ", timestamp integer" \
                ", hex varchar" \
                ", type varchar" \
                ", flight varchar" \
                ", altitude integer" \
                ", groundspeed numeric" \
                ", track numeric" \
                ", lat numeric" \
                ", lon numeric" \
                ", flightID integer" \
                ")"

indexes_postgres = "create index if not exists uix_timestamp on tracks (timestamp);" \
                    "create index if not exists uix_tracks_hex on tracks (hex);" \
                    "create index if not exists uix_tracks_lat on tracks (lat);" \
                    "create index if not exists uix_tracks_lon on tracks (lon);" \
                    "create index if not exists uix_tracks_fid on tracks (flightID);" \
                    "create index if not exists uix_airports_icao on airports (code_icao);" \
                    "create index if not exists uix_airports_lat on airports (lat);" \
                    "create index if not exists uix_airports_lon on airports (lon);" \
                    "create index if not exists uix_registrations_hex on registrations (icao_hex);" \
                    "create index if not exists uix_flights_hex on flights (icao_hex);" \
                    "create index if not exists uix_flights_origin on flights (origin_icao);" \
                    "create index if not exists uix_flights_dest on flights (dest_icao);"