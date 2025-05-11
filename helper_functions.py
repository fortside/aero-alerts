import constants
import config
import geopy.distance
import sqlite3
import datetime
import requests
import math
import os
from atproto import Client
import logging
from azure.storage.blob import BlobServiceClient
import csv
import pandas
import psycopg2

logger = logging.getLogger('Helper_Functions')

def get_distance(my_location, remote_location):
    distance = geopy.distance.distance(my_location, remote_location).kilometers
    #logger.debug("Object is " + str(round(distance,1)) + " km away")
    return distance

# shamelessly taken from https://gist.github.com/jeromer/2005586
def get_bearing(pointA, pointB):
    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))
    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

def dt_to_datetime(dt):
    return datetime.datetime.fromtimestamp(int(dt)).strftime('%Y-%m-%d %H:%M:%S')

def heading_to_direction(heading):
    if heading > 348.75 or heading < 11.25:
        return "N"
    elif heading >= 11.25 and heading < 33.75:
        return "NNE"
    elif heading >= 33.75 and heading < 56.25:
        return "NE"
    elif heading >= 56.25 and heading < 78.75:
        return "ENE"
    elif heading >= 78.75 and heading < 101.25:
        return "E"
    elif heading >= 101.25 and heading < 123.75:
        return "ESE"
    elif heading >= 123.75 and heading < 146.25:
        return "SE"
    elif heading >= 146.25 and heading < 168.75:
        return "SSE"
    elif heading >= 168.75 and heading < 191.25:
        return "S"
    elif heading >= 191.25 and heading < 213.75:
        return "SSW"
    elif heading >= 213.75 and heading < 236.25:
        return "SW"
    elif heading >= 236.25 and heading < 258.75:
        return "WSW"
    elif heading >= 258.75 and heading < 281.25:
        return "W"
    elif heading >= 281.25 and heading < 303.75:
        return "WNW"
    elif heading >= 303.75 and heading < 326.25:
        return "NW"
    else:  # heading >= 326.25 and heading < 348.75
        return "NNW"

def sql_conn():
    if config.postgres_enabled:
        conn = psycopg2.connect(dbname=config.postgres_db,user=config.postgres_user,
                                password=config.postgres_password,host=config.postgres_server,port=config.postgres_port)
    else:
        conn = sqlite3.connect(constants.db_name)
    return conn

def create_sql_tables():
    ##TODO simpler check if the table exists.
    #check_tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
    # connect to the database
    conn = sql_conn()
    # get the cursor so we can do stuff
    cur = conn.cursor()
    # create our tables
    if config.postgres_enabled:
        cur.execute(constants.flights_table_postgres)
        conn.commit()
        cur.execute(constants.airports_table_postgres)
        conn.commit()
        cur.execute(constants.registrations_table_postgres)
        conn.commit()
        cur.execute(constants.tracks_table_postgres)
        conn.commit()
        cur.execute(constants.indexes_postgres)
        conn.commit()
    else:
        cur.execute(constants.flights_table_sqlite)
        conn.commit()
        cur.execute(constants.airports_table_sqlite)
        conn.commit()
        cur.execute(constants.registrations_table_sqlite)
        conn.commit()

    # close the connections
    cur.close()
    conn.close()

def aircraft_exists(this_aircraft, now):
    # find the most recent entry for this aircraft
    if config.postgres_enabled:
        query = "select * from flights where icao_hex = (%s) order by id desc limit 1"
        param = (this_aircraft['hex'],)
    else:
        query = "select * from flights where icao_hex = (?) order by id desc limit 1"
        param = [this_aircraft['hex']]
    # run the query to see if this one is entered yet
    db_aircraft = sql_fetchone(query, param)
    if db_aircraft is None:
        # this aircraft has never been in our airspace
        return False
    else:
        #we've seen this before, check the timestamp to verify it's  not been in the last X minutes
        if round(now) > db_aircraft[1] + config.aircraft_debounce:
            #its been longer than the debounce time, so consider this a new entry
            return False
        else:
            #we've seen this aircraft in the last 'aircraft_debounce' seconds so ignore it
            return True

#generic function for handling calls to JSON APIs
def json_api_call(my_url, aeroAPI=False, hexdb=False):
    my_header = {'x-apikey':config.aero_api_key} if aeroAPI else {}
    if hexdb:
        my_header['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0'
    my_url = my_url.strip()
    try:
        logger.debug("Making API call to " + my_url.strip())
        req = requests.get(my_url.strip(), headers=my_header)
        data = req.json()
    except Exception as e:
        logger.debug("General Exception. Error reaching " + my_url + "Exception: " + str(e))
        data = None

    return data

def aircraft_lat_lon(aircraft):
    if 'lat' in aircraft:
        lat = aircraft['lat']
        lon = aircraft['lon']
        return lat, lon
    elif 'lastPosition' in aircraft:
        lat = aircraft['lastPosition']['lat']
        lon = aircraft['lastPosition']['lon']
        return lat, lon                                          
    else:
        return None, None

def aeroapi_available():
    if config.aeroapi_limit > 0:
        #Let's stay just below the limit to give a slight buffer
        #billing cycles start at the beginning of the month
        # https://discussions.flightaware.com/t/billing-cycles-at-start-of-month-or-end-of-month/81398/2
        firstdate = datetime.datetime.today().replace(day=1).strftime("%Y-%m-%d")
        thisdate = datetime.datetime.today().strftime("%Y-%m-%d")
        #The API throws an 'invalid argument' message if the start and end dates are the as the current date.
        # either way the API costs would be zero to start a new billing cycle 
        if thisdate == firstdate:
            thisdate = datetime.datetime.today().replace(day=2).strftime("%Y-%m-%d")
        dateparams = f"?start={firstdate}&end={thisdate}"
        total_spent = json_api_call(constants.aero_monthlyusage+dateparams, aeroAPI=True)
        if 'total_cost' in total_spent:
                total = total_spent['total_cost']
        else:
            total = 0
        logger.info("Total spend this month on AeroAPI is $" + str(total))
        if total <= config.aeroapi_limit - 0.10:
            return True
        else:
            return False
    else:
        return False
    
def parse_flight(hex):
    #build return object
    this_flight = {}
    url = "https://www.flightaware.com/live/modes/" + hex + "/redirect"
    try:
        logger.info("Parsing flight detail from " + url.strip())
        my_header = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0'}
        redirect_url = requests.get(url, headers=my_header).url
    except Exception as e:
        logger.debug("General Exception. Error reaching " + url + "Exception: " + str(e))
        return None

    #clean any mess from the URLs
    url = url.replace('https://www.flightaware.com/live/modes/',"").replace('https://flightaware.com/live/modes/',"")
    redirect_url = redirect_url.replace('https://www.flightaware.com/live/modes/',"").replace('https://flightaware.com/live/modes/',"")
    if url != redirect_url:
        params = redirect_url.split('/')
        logger.debug('Parsed paramaters are: : %s', params)
        flight = redirect_url.split('/')[5]
        logger.debug(hex + ": Parsed flight " + flight + " from FA")
        this_flight['callsign'] = params[5]
        logger.debug("Parsed callsign: " + this_flight['callsign'])
        if params.__len__() > 9:
            this_flight['origin'] = params[9]
            logger.debug("Parsed origin: " + this_flight['origin'])
        else:
            this_flight['origin'] = None
        if params.__len__() > 10:
            this_flight['dest'] = params[10]
            logger.debug("Parsed dest: " + this_flight['dest'])
        else:
            this_flight['dest'] = None
    else:
        flight = None
        this_flight = None

    return this_flight
        
def get_airport_info(icao, timestamp=None):
    #build return object
    this_airport = {}
    #check Airports DB
    if config.postgres_enabled:
        query = "select name, city from airports where code_icao = (%s) order by id desc limit 1"
        param = (icao,)
    else:
        query = "select name, city from airports where code_icao = (?) order by id desc limit 1"
        param = [icao]
    db_airport = sql_fetchone(query, param)
    if db_airport is None and config.aeroapi_enabled and aeroapi_available():
        # this airport is new to us. Look it up and save it.
        airport_json = json_api_call(constants.aero_airport_url + icao, aeroAPI=True)
        if airport_json is not None and'country_code' in airport_json:
            #populate return object
            this_airport['name'] = airport_json.get('name',None)
            this_airport['city'] = airport_json.get('city',None)
            this_airport['country'] = airport_json.get('country_code',None)
            #now write this to the local database so we don't need to waste future API calls
            if config.postgres_enabled:
                airport_insert = "insert into airports "\
                "(code_icao, name, type, city, state, lat, lon, country_code, timestamp)" \
                " values (%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing;"
                airport_values = (airport_json.get('code_icao',None),
                                airport_json.get('name',None),
                                airport_json.get('type',None),
                                airport_json.get('city',None),
                                airport_json.get('state',None),
                                airport_json.get('latitude',None),
                                airport_json.get('longitude',None),
                                airport_json.get('country_code',None),
                                timestamp)
            else:
                airport_insert = "insert or ignore into airports "\
                "(code_icao, name, type, city, state, lat, lon, country_code, timestamp)" \
                " values (?,?,?,?,?,?,?,?,?);"
                airport_values = [airport_json.get('code_icao',None),
                                airport_json.get('name',None),
                                airport_json.get('type',None),
                                airport_json.get('city',None),
                                airport_json.get('state',None),
                                airport_json.get('latitude',None),
                                airport_json.get('longitude',None),
                                airport_json.get('country_code',None),
                                timestamp]
            insert_update_row(airport_insert, airport_values)
            logger.info(icao + " airport details added to local database")
    elif db_airport is None:
        this_airport['name'] = None
        this_airport['city'] = None
        this_airport['country'] = None
    else:
        #return the airport info from the database
        this_airport['name'] = db_airport[0]
        this_airport['city'] = db_airport[1]
        logger.debug(icao + " airport details retreived locally")

    return this_airport

def save_track(now, aircraft):
    #Validate the save path
    #create one folder for each day
    todaystring = "tracks-" + datetime.datetime.now().strftime('%Y-%m-%d')
    #todayfolder = constants.adsb_save_folder + todaystring + "\\"
    #todayfile = config.adsb_save_folder + "\\" + todaystring + ".csv"
    todayfile = os.path.join(config.adsb_save_folder, todaystring + ".csv")
    if not os.path.exists(todayfile):
        try:
            with open(todayfile, 'w', encoding='utf-8',newline='') as f:
                writer = csv.writer(f)
                writer.writerow(constants.csv_header)
            logger.info("Created new file for today: " + todayfile)
            #upload the database as a daily backup step
            if config.azure_backup_enabled:
                upload_database()
        except Exception as e:
            logger.info("Error creating save folder. Live info will not be saved.\n" + str(e))
            return
    # save this info to today's CSV file
    logger.debug("Appending to csv file on disk: " + todayfile)
    with open(todayfile, 'a', encoding='utf-8',newline='') as f:
        writer = csv.writer(f)
        #['Timestamp', 'Hex', 'Type', 'Flight','Altitude','Groundspeed','Track','Lat','Lon','FlightID']
        flightID = sql_fetchone("select ID from flights where icao_hex = (?) order by id desc limit 1",[aircraft['hex']])
        flight = aircraft.get('flight',None)
        flight = None if flight is None else flight.strip()
        alt = aircraft.get('alt_baro',None)
        speed = aircraft.get('gs',None)
        speed = None if speed is None else round(speed*constants.knots_to_kph,1)
        track = track = aircraft.get('track',None)
        track = None if track is None else round(track)
        lat,lon = aircraft_lat_lon(aircraft)
        info = [round(now),aircraft['hex'],aircraft['type'],flight,alt,speed,track,lat,lon,flightID[0]]
        writer.writerow(info)

def save_track_postgres(now, aircraft):
    track_insert = "insert into tracks "\
    "(timestamp, hex, type, flight, altitude, groundspeed, track, lat, lon, flightID)" \
    " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing;"
    
    flightID = sql_fetchone("select ID from flights where icao_hex = (%s) order by id desc limit 1",(aircraft['hex'],))
    flight = aircraft.get('flight',None)
    flight = None if flight is None else flight.strip()
    alt = aircraft.get('alt_baro',None)
    speed = aircraft.get('gs',None)
    speed = None if speed is None else round(speed*constants.knots_to_kph,1)
    track = track = aircraft.get('track',None)
    track = None if track is None else round(track)
    lat,lon = aircraft_lat_lon(aircraft)
        
    track_values = (round(now),aircraft['hex'],aircraft['type'],flight,alt,speed,track,lat,lon,flightID[0])
    insert_update_row(track_insert, track_values)
    logger.debug(aircraft['hex'] + " written to tracks table in database")

def BlueskyPost(now):
    # # Find any non-posted aircraft from within our tolerated lag window
    max_lag = round(now - config.bsky_post_lag)
    if config.postgres_enabled:
        query = "select f.flight, r.registration, r.model, r.manufacturer, r.owner_name, "\
                "f.altitude, f.speed, f.heading, f.bearing, f.airline_name, "\
                "oa.name as \"origin_name\", da.name as \"dest_name\", f.id from flights f left join registrations r "\
                "on f.icao_hex = r.icao_hex left join airports oa on f.origin_icao = oa.code_icao "\
                "left join airports da on f.dest_icao = da.code_icao where f.bsky_post = 0 and f.timestamp >= (%s) order by f.id asc"
        param = (max_lag,)
    else:
        query = "select f.flight, r.registration, r.model, r.manufacturer, r.owner_name, "\
                "f.altitude, f.speed, f.heading, f.bearing, f.airline_name, "\
                "oa.name as 'origin_name', da.name as 'dest_name', f.id from flights f left join registrations r "\
                "on f.icao_hex = r.icao_hex left join airports oa on f.origin_icao = oa.code_icao "\
                "left join airports da on f.dest_icao = da.code_icao where f.bsky_post = 0 and f.timestamp >= (?) order by f.id asc"
        param = [max_lag]
    
    # run the query to see if this one is entered yet.
    db_posts = sql_fetchall(query,param)

    if db_posts.__len__() > 0:
        try:
            logger.info(str(db_posts.__len__()) + " postable items found")
            # Instantiate the client object
            client = Client()
            # Log in 
            client.login(config.bsky_account, config.bsky_app_pass)
            #now make our post(s)   
            for unposted_aircraft in db_posts:
                post_text = ""
                #bearing. Should always be known
                if unposted_aircraft[8] is None:
                    post_text += "Aircraft detected from unknown direction" + "!\n"
                else:
                    post_text += "Aircraft detected to the " + heading_to_direction(unposted_aircraft[8]) + "!\n" 
                #owner/airline name
                if unposted_aircraft[9] is None and unposted_aircraft[4] is None:
                    owner = "Unknown owner"
                elif unposted_aircraft[9] is None or unposted_aircraft[9] == 'Karat':
                    owner = unposted_aircraft[4]
                else:
                    owner = unposted_aircraft[9]
                #flight
                if unposted_aircraft[0] is None or unposted_aircraft[0] == "":
                    flight = "Unknown"
                else:
                    flight = unposted_aircraft[0]
                #origin
                if unposted_aircraft[10] is None:
                    origin = "unknown origin"
                else:
                    origin = unposted_aircraft[10]
                #destination
                if unposted_aircraft[11] is None:
                    dest = ""
                else:
                    dest = " to " + unposted_aircraft[11]            
                #airline name, flight, origin airport, dest airport
                post_text += owner + " flight #" + flight + " from " + origin + dest + "\n"
                #model/manufacturer always report together
                if unposted_aircraft[2] is None:
                    model = "unknown"
                else:
                    model = unposted_aircraft[3] + " " + unposted_aircraft [2]
                post_text += "Aircraft: " + model + "\n"
                #registration
                if unposted_aircraft[1] is None:
                    tail = flight
                else:
                    tail = unposted_aircraft[1]
                post_text += "Tail # " + tail + "\n"
                #speed/haeading always report together
                if unposted_aircraft[6] is None:
                    speed = "unknown"
                else:
                    speed = str(unposted_aircraft[6]) + " km/h tracking " + heading_to_direction(unposted_aircraft[7])
                post_text += "Speed: " + speed + "\n"
                #alt
                if unposted_aircraft[5] is None:
                    alt = "unknown"
                else:
                    alt = str(unposted_aircraft[5]) + " ft"
                post_text += "Alt: " + alt + "\n"
            
                logger.info("Bsky post is:\n" + post_text)
                # Create and send a new post
                try:
                    new_post = client.send_post(post_text)
                    successful_post = True
                except Exception as e:
                    
                    logger.debug("Error posting: " + str(e))
                    successful_post = False
                #mark the record as being posted successfully
                if successful_post:
                    if config.postgres_enabled:
                        query = "update flights set bsky_post = 1 where id = (%s)"
                        param = (unposted_aircraft[12],)
                    else:
                        query = "update flights set bsky_post = 1 where id = (?)"
                        param = [unposted_aircraft[12]]
                    insert_update_row(query,param)
        except Exception as e:
            logger.debug("Error authenticating to Bluesky. Check credentials if this persists. "+ str(e))

    return True

def SetAircraftReportable(aircraft, now):
    logger.debug("Checking if " + aircraft['hex'] + " set as reportable")
    max_lag = round(now - config.bsky_post_lag)
    if config.postgres_enabled:
        query = "select id from flights where icao_hex = (%s) and bsky_post is null and timestamp >= (%s) order by id desc limit 1"
        params = (aircraft['hex'], max_lag)
    else:
        query = "select id from flights where icao_hex = (?) and bsky_post is null and timestamp >= (?) order by id desc limit 1"
        params = [aircraft['hex'], max_lag]
    
    id = sql_fetchone(query, params)
    if id is not None:
        logger.info(aircraft['hex'] + ": now set as reportable")
        #set the row as postable and upate more recent information about the aircraft
        newspeed = aircraft.get('gs',None)
        newspeed = None if newspeed is None else round(newspeed*constants.knots_to_kph,1)
        newaltitude = aircraft.get('alt_baro',None)
        newtrack = aircraft.get('track',None)
        newtrack = None if newtrack is None else round(newtrack)
        newlat, newlon = aircraft_lat_lon(aircraft)
        newbearing = round(get_bearing(constants.home, (newlat, newlon)))
        if config.postgres_enabled:
            update_query = "update flights set timestamp = (%s), lat = (%s), lon = (%s), speed = (%s), altitude = (%s), heading = (%s), bearing = (%s), bsky_post = (%s) where id = (%s)"
            update_values = (now,
                            newlat,
                            newlon,
                            newspeed,
                            newaltitude,
                            newtrack,
                            newbearing,
                            0,
                            id[0]
                            )
        else:
            update_query = "update flights set timestamp = (?), lat = (?), lon = (?), speed = (?), altitude = (?), heading = (?), bearing = (?), bsky_post = (?) where id = (?)"
            update_values = [now,
                            newlat,
                            newlon,
                            newspeed,
                            newaltitude,
                            newtrack,
                            newbearing,
                            0,
                            id[0]
                            ]
        insert_update_row(update_query, update_values)
        logger.info(dt_to_datetime(now) + ": " + aircraft['hex'] + " is now in our space. Posting about it!")
    
    return

def sql_fetchone(query, values):
    logger.debug("Fetch one query: " + query)
    logger.debug('Fetch one values: : %s', values)
    try:
        conn = sql_conn()
        cur = conn.cursor()
        cur.execute(query, values)
        result = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        logger.debug("SQL fetch one error: " + str(e))
        result = None
    return result

def sql_fetchall(query, values):
    logger.debug("Fetch all query: " + query)
    logger.debug('Fetch all values: : %s', values)
    try:
        conn = sql_conn()
        cur = conn.cursor()
        cur.execute(query, values)
        result = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        logger.debug("SQL fetch all error: " + str(e))
        result = None
    return result

def insert_update_row(query, record):
    logger.debug("Insert/Update query: " + query)
    logger.debug('Insert/Update record: %s', record)
    try:
        conn = sql_conn()
        cur = conn.cursor()
        cur.execute(query, record)
        conn.commit()
        result = True
    except Exception as e:
        logger.debug("SQL insert error: " + str(e))
        result = False
    finally:
        cur.close()
        conn.close()
        
    return result

def upload_database():
    #we must break the database tables down into individual csv files that can be uploaded
    tables = ['airports','flights','registrations']
    try:
        conn = sql_conn()
        for table in tables:
            db_table = pandas.read_sql('SELECT * from ' + table, conn)
            db_table.to_csv(config.adsb_save_folder + table + ".csv", index=False)
        conn.close()
    except Exception as e:
        logger.debug("Error exporting tables " + str(e))

    #now upload the database and exported tables to the blob container
    try:
        logger.info("Uploading database snapshot")
        blob_service_client = BlobServiceClient(account_url=config.azure_storage_account_url, credential=config.azure_storage_account_key)
        container_client = blob_service_client.get_container_client(config.azure_storage_container_name)
        
        #upload database
        blob_client = container_client.get_blob_client(constants.db)
        with open(constants.db_name, "rb") as blob:
            blob_client.upload_blob(blob, overwrite=True)
        if blob_client.exists():
            logger.info("Database snapshot successfully uploaded to storage account")
        else:
            logger.info("Upload unsuccessful. Debug more if this error appears")

        #upload the 3 files
        for table in tables:
            blob_client = container_client.get_blob_client(table + ".csv")
            with open(config.adsb_save_folder + table + ".csv", "rb") as blob:
                blob_client.upload_blob(blob, overwrite=True)
            if blob_client.exists():
                logger.info(table + " snapshot successfully uploaded to storage account")
            else:
                logger.info(table + " upload unsuccessful. Debug more if this error appears")
    except Exception as e:
        logger.info("Error uploading to Azure storage. Try again next time. Exception:\n" + str(e))

    #find any daily tracks files and upload them
    todaystracks = "tracks-" + datetime.datetime.today().strftime("%Y-%m-%d") + ".csv"
    for root, _, files, in os.walk(config.adsb_save_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if "tracks-" in file_path:
                # Create a BlobClient
                blob_client = container_client.get_blob_client(config.azure_storage_subfolder + file)
                #upload the file
                with open(file_path, "rb") as blob:
                    blob_client.upload_blob(blob, overwrite=True)
                logger.debug("Uploaded " + file)
                #delete the local files from previous days if they were uploaded
                if file != todaystracks and blob_client.exists():
                    os.remove(file_path)

def validate_env_vars():
    logger = logging.getLogger('env_validation')
    logger.debug("[LOG_LEVEL] = " + config.logging_level)
    logger.debug("[ADSB_HISTORY_ENABLED] = " + str(config.adsb_history_enabled))
    logger.debug("[POSTGRES_ENABLED] = " + str(config.postgres_enabled))
    logger.debug("[POSTGRES_SERVER] = " + config.postgres_server)
    logger.debug("[POSTGRES_PORT] = " + str(config.postgres_port))
    logger.debug("[POSTGRES_DATABASE] = " + config.postgres_db)
    logger.debug("[POSTGRES_USER] = " + config.postgres_user)
    logger.debug("[POSTGRES_PASSWORD] = " + config.postgres_password)
    logger.debug("[ADSB_SAVE_FOLDER] = " + config.adsb_save_folder)
    logger.debug("[LIVE_DATA_URL] = " + config.live_data_url)
    logger.debug("[MY_LAT] = " + str(config.my_lat))
    logger.debug("[MY_LON] = " + str(config.my_lon))
    logger.debug("[AIRSPACE_RADIUS_KM] = " + str(config.airspace_radius_km))
    logger.debug("[RECORD_RADIUS_KM] = " + str(config.record_radius_km))
    logger.debug("[SLEEP_TIME] = " + str(config.sleep_time))
    logger.debug("[AIRCRAFT_DEBOUNCE] = " + str(config.aircraft_debounce))
    logger.debug("[AEROAPI_ENABLED] = " + str(config.aeroapi_enabled))
    logger.debug("[AEROAPI_LIMIT] = " + str(config.aeroapi_limit))
    logger.debug("[AEROAPI_KEY] = " + config.aero_api_key)
    logger.debug("[BSKY_POST_ENABLED] = " + str(config.bsky_post_enabled))
    logger.debug("[BSKY_ACCOUNT] = " + config.bsky_account)
    logger.debug("[BSKY_APP_PASS] = " + config.bsky_app_pass)
    logger.debug("[BSKY_POST_LAG] = " + str(config.bsky_post_lag))
    logger.debug("[AZ_BACKUP_ENABLED] = " + str(config.azure_backup_enabled))
    logger.debug("[AZ_STORAGE_ACCOUNT_URL] = " + config.azure_storage_account_url)
    logger.debug("[AZ_STORAGE_ACCOUNT_KEY] = " + config.azure_storage_account_key)
    logger.debug("[AZ_CONTAINER_NAME] = " + config.azure_storage_container_name)
    logger.debug("[AZ_CONTAINER_FOLDER] = " + config.azure_storage_subfolder)
    return