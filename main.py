import helper_functions
import constants
import config
import time
import logging
import sys
from flight import Flight

def main():
    # Configure logging
    logging.basicConfig(
        level=config.logging_level,  # Set the minimum log level to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Define the log message format
        handlers=[
            logging.StreamHandler(sys.stdout)  # Log messages to the console
        ]
    )
    logger = logging.getLogger('Main')

    helper_functions.validate_env_vars()
    # start by ensuring the SQL backend is set up
    helper_functions.create_sql_tables()

    while True:
        data = helper_functions.json_api_call(config.live_data_url)
        if data is None:
            print("Error: No valid 1090 data feed. Check to ensure the live_data_url constant is set correctly")

        # if we have valid aircraft data, run through each aircraft to see the details
        if data is not None and data['aircraft'].__len__():
            for aircraft in data['aircraft']:
                #Check location info
                lat, lon = helper_functions.aircraft_lat_lon(aircraft)
                if lat is not None and lon is not None:
                    dist = helper_functions.get_distance(constants.home, (lat, lon))
                    aircraft['hex'] = aircraft['hex'].replace('~','')
                    logger.debug(aircraft['hex'] + ": " + str(round(dist,1)) + " km away")
                    if dist <= config.record_radius_km:
                        # check if this aircraft already exists in our local database
                        if not helper_functions.aircraft_exists(aircraft, data['now']):
                            logger.info(aircraft['hex'] + " is not in the database. Adding")
                            #get specific flight details
                            flyingthing = Flight(data['now'], aircraft)
                            #write to DB
                            flyingthing.InsertAircraftRecord()
                        #here we log the track, now including the flight ID
                        if config.adsb_history_enabled:
                            if config.postgres_enabled:
                                helper_functions.save_track_postgres(data['now'], aircraft)
                            else:
                                helper_functions.save_track(data['now'], aircraft)
                    #if the aircraft is less than <airspace radius> away we set bsky_post to 0 instead of null
                    if dist <= config.airspace_radius_km:
                        helper_functions.SetAircraftReportable(aircraft, round(data['now']))
        #tell the world
        if data is not None and config.bsky_post_enabled:
                helper_functions.BlueskyPost(data['now'])
        time.sleep(config.sleep_time)

if __name__ == "__main__":
    main()
