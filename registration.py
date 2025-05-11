#Class definition of a unique aircraft object

import constants
import config
import helper_functions
import datetime
import logging
logger = logging.getLogger('Registration')

class Registration:
    def __init__(self, hex):
        self.icao_hex = hex
        self.registration = None
        self.model = None
        self.manufacturer = None
        self.owner_name = None
        self.owner_country = None
        self.source = None
        self.timestamp = None
        self.valid = False
        self.CheckExisting()
        if not self.valid:
            self.Checkadsbdb()
        if not self.valid:
            self.Checkhexdb()
        if not self.valid:
            self.CheckAeroAPI()
        if self.valid and self.source != 'internal':
            self.InsertRegistrationRecord()

    def Checkadsbdb(self):
        adsbdb_aircraft_details = helper_functions.json_api_call(constants.adsbdb_aircraft_url + self.icao_hex)
        if adsbdb_aircraft_details is not None and adsbdb_aircraft_details['response'] != "unknown aircraft":
            self.registration = adsbdb_aircraft_details['response']['aircraft']['registration']
            self.model = adsbdb_aircraft_details['response']['aircraft']['type']
            self.manufacturer = adsbdb_aircraft_details['response']['aircraft']['manufacturer']
            self.owner_name = adsbdb_aircraft_details['response']['aircraft']['registered_owner']
            self.owner_country = adsbdb_aircraft_details['response']['aircraft']['registered_owner_country_name']
            self.source = "adsbdb"
            self.timestamp = round((datetime.datetime.now(datetime.timezone.utc) - datetime.datetime(1970, 1, 1,tzinfo=datetime.timezone.utc)).total_seconds())
            self.valid = True
            logger.info(self.icao_hex + ": Aircraft metadata gathered from adsbdb")
        else:
            logger.info(self.icao_hex + ": No aircraft metadata available from adsbdb")

    def Checkhexdb(self):
        #aircraft details
        if self.registration is None:
            hexdb_aircraft_details = helper_functions.json_api_call(constants.hexdb_aircraft_url + self.icao_hex,hexdb=True)
            if hexdb_aircraft_details is not None and 'Registration' in hexdb_aircraft_details:
                self.registration = hexdb_aircraft_details['Registration']
                self.model = hexdb_aircraft_details['Type']
                self.manufacturer = hexdb_aircraft_details['Manufacturer']
                self.owner_name = hexdb_aircraft_details['RegisteredOwners']
                #owner_country isn't returned by hexdb
                self.source = "hexdb"
                self.timestamp = round((datetime.datetime.now(datetime.timezone.utc) - datetime.datetime(1970, 1, 1,tzinfo=datetime.timezone.utc)).total_seconds())
                self.valid = True
                logger.info(self.icao_hex + ": Aircraft metadata gathered from hexdb")
            else:
                logger.info(self.icao_hex + ": No aircraft metadata available from hexdb")

    def CheckAeroAPI(self):
        logger.debug("Calling the CheckAeroAPI function here to get registration info from AeroAPI. Haven't needed this yet!")
        #No FA endpoint exists to get aircraft registration info by hex 
        

    def CheckExisting(self):
        if config.postgres_enabled:
            query = "select registration, model, manufacturer, owner_name, owner_country, timestamp from registrations where icao_hex = (%s)"
            param = (self.icao_hex,)
        else:
            query = "select registration, model, manufacturer, owner_name, owner_country, timestamp from registrations where icao_hex = (?)"
            param = [self.icao_hex]

        result = helper_functions.sql_fetchone(query, param)
        if result is not None:
            self.registration = result[0]
            self.model = result[1]
            self.manufacturer = result[2]
            self.owner_name = result[3]
            self.owner_country = result[4]
            self.source = 'internal'
            self.timestamp = result[5]
            self.valid = True
            logger.info(self.icao_hex + ": Aircraft metadata found locally from internal database")
        else:
            logger.info(self.icao_hex + ": No aircraft metadata available internally")

    def InsertRegistrationRecord(self):
        if config.postgres_enabled:
            reg_insert = "insert into registrations "\
                        "(timestamp, icao_hex, registration, model, manufacturer, owner_name, owner_country, source)" \
                        " values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing;"
            reg_values = (self.timestamp, #timestamp
                    self.icao_hex, #icao_hex
                    self.registration, #registration
                    self.model, #model
                    self.manufacturer, #manufacturer
                    self.owner_name, #owner_name
                    self.owner_country, #owner_country
                    self.source, #source
                    )
        else:
            reg_insert = "insert or ignore into registrations "\
                        "(timestamp, icao_hex, registration, model, manufacturer, owner_name, owner_country, source)" \
                        " values (?,?,?,?,?,?,?,?);"
            reg_values = [self.timestamp, #timestamp
                        self.icao_hex, #icao_hex
                        self.registration, #registration
                        self.model, #model
                        self.manufacturer, #manufacturer
                        self.owner_name, #owner_name
                        self.owner_country, #owner_country
                        self.source, #source
                        ]

        #write this into the database, and return True. Return False if an error occurs
        helper_functions.insert_update_row(reg_insert, reg_values)
