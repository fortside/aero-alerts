#Class definition of a flight object
import helper_functions
import constants
import config
from registration import Registration
import logging

logger = logging.getLogger('Flight')

class Flight:
    def __init__(self, now, aircraftjson):
        self.timestamp = round(now)
        self.hex = None
        self.flight = None
        self.altitude = None
        self.speed = None
        self.lat = None
        self.lon = None
        self.distance = None
        self.heading = None
        self.squawk = None
        self.emergency = None
        self.airline_name = None
        self.airline_country = None
        self.origin_icao = None
        self.origin_airport = None
        self.dest_icao = None
        self.dest_airport = None
        self.airframe_source = None
        self.flightroute_source = None
        self.bearing = None
        self.bsky_post = None
        self.reg = Registration(aircraftjson['hex'])
        self.SetProperties(aircraftjson)
        self.CheckAeroAPI()
        #self.Checkadsbdb() #This is a last resort. Callsign information (flight routes) is very inaccurate. Hexdb even worse for this.
   
    def SetProperties(self, aircraftjson):
        self.lat, self.lon = helper_functions.aircraft_lat_lon(aircraftjson)
        self.hex = aircraftjson['hex']
        #parse out some inconsistently formatted values
        self.flight = aircraftjson.get('flight',None)
        self.flight = None if self.flight is None else self.flight.strip()
        self.altitude = aircraftjson.get('alt_baro',None)
        self.speed = aircraftjson.get('gs',None)
        self.speed = None if self.speed is None else round(self.speed*constants.knots_to_kph,1)
        self.dist = aircraftjson.get('r_dst',None) 
        self.dist = None if self.dist is None else round(self.dist*constants.knots_to_kph,1)
        self.track = aircraftjson.get('track',None)
        self.track = None if self.track is None else round(self.track)
        self.squawk = aircraftjson.get('squawk',None)
        self.emerg = aircraftjson.get('emergency',None)
        self.bearing = round(helper_functions.get_bearing(constants.home, (self.lat, self.lon)))
        logger.info(self.hex + ": Default properties set")

    def Checkadsbdb(self):
        #flight route details
        if self.flight is not None and self.origin_icao is None:
            adsbdb_flightroute_details = helper_functions.json_api_call(constants.adsbdb_callsign_url + self.flight.strip())
            if adsbdb_flightroute_details is not None and adsbdb_flightroute_details['response'] != "unknown callsign":
                if adsbdb_flightroute_details['response']['flightroute']['airline'] is not None:
                    self.airline_name = adsbdb_flightroute_details['response']['flightroute']['airline']['name']
                    self.airline_country = adsbdb_flightroute_details['response']['flightroute']['airline']['country']
                    #create an origin airport object out of returned values
                    self.origin_icao = adsbdb_flightroute_details['response']['flightroute']['origin']['icao_code']
                    self.origin_airport = helper_functions.get_airport_info(self.origin_icao, self.timestamp)
                    #create a destination airport object out of returned values
                    self.dest_icao = adsbdb_flightroute_details['response']['flightroute']['destination']['icao_code']
                    self.dest_airport = helper_functions.get_airport_info(self.dest_icao, self.timestamp)
                    self.flightroute_source = "adsbdb"
                logger.info(self.hex + ": Flight route grabbed from adsbdb")
            else:
                logger.info(self.hex + ": No flight route metadata available from adsbdb")

    def CheckAeroAPI(self):
        #Try to look up the flight if required
        if self.flight is not None and self.origin_icao is None and config.aeroapi_enabled:
            #Must have credit available and know the tail # as well
            if self.reg.registration is not None and helper_functions.aeroapi_available():
                aeroAPI_flightroute_details = helper_functions.json_api_call(constants.aero_flightroute_url + self.reg.registration, aeroAPI=True)
                #ensure the response is valid
                if aeroAPI_flightroute_details is not None and 'flights' in aeroAPI_flightroute_details:
                    if aeroAPI_flightroute_details['flights'].__len__():
                        #the details we want are somewhere in the array. Must iterate until we find it
                        for fli in aeroAPI_flightroute_details['flights']:
                            if fli['ident_icao']==self.flight:
                                self.origin_icao = fli['origin']['code_icao']
                                self.origin_airport = helper_functions.get_airport_info(self.origin_icao, self.timestamp)
                                if fli['destination'] is not None:
                                    self.dest_icao = fli['destination']['code_icao']
                                    self.dest_airport = helper_functions.get_airport_info(self.dest_icao, self.timestamp)
                                break
                        logger.info(self.hex + ": Flight route grabbed from aeroAPI")
                        self.flightroute_source = "aeroAPI"
                else:
                    logger.info(self.hex + ": No flight route metadata available from aeroAPI")

        #Can't trust hexdb or adsbdb callsign info. Must gather from URL parsing :(
        # As soon as AeroAPI allows lookups based on icao hex values we can use that instead
        if self.flight is None or self.origin_icao is None:
            parsed_results = helper_functions.parse_flight(self.hex)
            if parsed_results is not None:
                self.flight = parsed_results['callsign']
                self.origin_icao = parsed_results['origin']
                self.origin_airport = None if self.origin_icao is None else helper_functions.get_airport_info(self.origin_icao, self.timestamp)
                self.dest_icao = parsed_results['dest']
                self.dest_airport = None if self.dest_icao is None else helper_functions.get_airport_info(self.dest_icao, self.timestamp)
                self.flightroute_source = "FA_parse" if self.flightroute_source is None else self.flightroute_source + ",FA_parse"

    
    def InsertAircraftRecord(self):
        if config.postgres_enabled:
            aircraft_insert = "insert into flights "\
                        "(timestamp, icao_hex, flight, " \
                        " altitude, speed, lat, lon, distance, heading, squawk, emergency, airline_name, airline_country," \
                        " origin_icao, dest_icao, flightroute_source, bearing, bsky_post)" \
                        " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing;"
            aircraft_values = (self.timestamp, #timestamp
                        self.hex, #icao_hex
                        self.flight, #flight
                        self.altitude, #altitude
                        self.speed, #speed
                        self.lat, #lat
                        self.lon, #lon
                        self.dist, #distance
                        self.track, #heading
                        self.squawk, #squawk
                        self.emerg, #emergency
                        self.airline_name, #airline name                       
                        self.airline_country, #airline country                       
                        self.origin_icao, # origin icao
                        self.dest_icao, #dest icao
                        self.flightroute_source,
                        self.bearing,
                        self.bsky_post                 
                        )        
        else:
            aircraft_insert = "insert or ignore into flights "\
                        "(timestamp, icao_hex, flight, " \
                        " altitude, speed, lat, lon, distance, heading, squawk, emergency, airline_name, airline_country," \
                        " origin_icao, dest_icao, flightroute_source, bearing, bsky_post)" \
                        " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);"
            aircraft_values = [self.timestamp, #timestamp
                        self.hex, #icao_hex
                        self.flight, #flight
                        self.altitude, #altitude
                        self.speed, #speed
                        self.lat, #lat
                        self.lon, #lon
                        self.dist, #distance
                        self.track, #heading
                        self.squawk, #squawk
                        self.emerg, #emergency
                        self.airline_name, #airline name                       
                        self.airline_country, #airline country                       
                        self.origin_icao, # origin icao
                        self.dest_icao, #dest icao
                        self.flightroute_source,
                        self.bearing,
                        self.bsky_post                 
                        ]

        #write this into the database
        helper_functions.insert_update_row(aircraft_insert, aircraft_values)