# Aero-alerts

An application to document flight details for aircraft that pass by your location. Optional functionality includes posting flights to social media, saving detailed flight history, and backing up to Azure.

## Requirements

- An ADS-B receiver (PiAware, Flight Feeder, etc.) with a dump1090 or tar1090 endpoint to access the organized json feed

>[!NOTE]
>If not using ADSBx be sure to set your aircraft.json URL accordingly for other providers!

## Optional functionality

- Post to Social Media
  - Post every time an aircraft passes near your location
  - Bluesky currently supported

- Record Flight History
  - Record all flights that pass within a specified range of your location
  - Flight movement tracking: Record the path traveled by an aircraft
  - PostgreSQL is recommended for the high volume of tracks recorded
  - SQLite is the fallback and works fine if flight tracking history isn't enabled
  - If not using pgSQL there is an option to leverage Azure blob storage, as sqlite doesn't scale for large amounts of history

- AeroAPI integration
  - If you have an account with FlightAware to use AeroAPI it can be leveraged for better data quality
  - Members who submit data ADS-B receivers to FA are elibible for a small amount of free API credit
  - Optional ability to set a limit on API calls to set an upper limit on monthly costs

>[!NOTE]
>PostgreSQL is highly recommended as a backend if history/tracking is enabled. Depending on your settings, many thousands of tracks can be generated daily. SQLite does not perform well at this scale over time.

## Usage

This can either be ran as a standalone command line python application (>> python main.py) or as a Docker container. Recommendation is to use the Docker image with accompanying PostgreSQL backend, or with an embedded SQLite backend if not tracking any history.

There is a heavy reliance on environment variables for configuration so leveraging docker-compose is most convenient.

## Supported Architectures

Pulling `hub.docker.com/fortside/aero-alerts:latest` should automatically retrieve the correct image.

This is a multi-platform image with support for both x86 and newer arm architectures:

| Architecture | Available |
| :----: | :----: |
| x86-64 | ✅ |
| arm64 | ✅ |

## Data sources

- [ADSBDB](https://www.adsbdb.com/)
- [HexDB](https://hexdb.io)
- [FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/)

## Parameters

| Parameter | Default Value | Allowed Values | Function |
| :----: | --- | --- | --- |
| `LOG_LEVEL` | `'INFO'` | `'DEBUG','INFO'` | Application logging level |
| `ADSB_HISTORY_ENABLED` | `'FALSE'` | `'TRUE','FALSE'` | Track history of flights and flight tracks. <br>If `POSTGRES_ENABLED` is `FALSE` these tracks are saved to csv files in the `ADSB_SAVE_FOLDER`.|
| `ADSB_SAVE_FOLDER` | `'/data'` | | Folder where SQLite database and any daily tracks files will be stored.<br>Ignored if `POSTGRES_ENABLED` is `TRUE`|
| `LIVE_DATA_URL` | `'http://adsbexchange.local/tar1090/data/aircraft.json'` | | Link to aircraft.json endpoint on your ADS-B receiver |
| `MY_LAT` | | | Latitude of your ADS-B receiver |
| `MY_LON` | | | Longitude of your ADS-B receiver |
| `RECORD_RADIUS_KM` | `100` | | How far away to look for flights to track |
| `AIRSPACE_RADIUS_KM` | `10` | | Your local airspace. Send a social media post if an aircraft gets this close |
| `SLEEP_TIME` | `10` | | Time (in seconds) to wait between polling your ADS-B receiver for updated airspace information |
| `AIRCRAFT_DEBOUNCE` | `3600` | | Time (in seconds) to wait before considering this aircraft as new in your airspace again |
| `POSTGRES_ENABLED` | `'FALSE'` | `'TRUE','FALSE'` | Use PostgreSQL for data storage.<br>If False, embedded SQLite DB will be used|
| `POSTGRES_SERVER` | `'localhost'` | | Server hosting your pgSQL database.<br>Ignored if `POSTGRES_ENABLED` is `FALSE`|
| `POSTGRES_PORT` | `5432` | | Port your pgSQL server is listening on.<br>Ignored if `POSTGRES_ENABLED` is `FALSE`|
| `POSTGRES_DATABASE` | `'aero-alerts'` | | Name of your pgSQL database.<br>Ignored if `POSTGRES_ENABLED` is `FALSE`|
| `POSTGRES_USER` | `'aero-user'` | | Name of pgSQL account with rights to the `POSTGRES_DATABASE` database.<br>Ignored if `POSTGRES_ENABLED` is `FALSE`|
| `POSTGRES_PASSWORD` | `'aero-pass'` | | Password for `POSTGRES_USER` user.<br>Ignored if `POSTGRES_ENABLED` is `FALSE`|
| `AEROAPI_ENABLED` | `'FALSE'` | `'TRUE','FALSE'` | Set to `TRUE` if you have a valid AeroAPI key and want to use it |
| `AEROAPI_LIMIT` | `0` | | Upper limit of dollars to spend monthly on the AeroAPI |
| `AEROAPI_KEY` | | | API key to retreive data from AeroAPI |
| `BSKY_POST_ENABLED` | `FALSE` | `'TRUE','FALSE'` | Set to `TRUE` to make a BlueSky post when an aircraft enters your airspace radius |
| `BSKY_ACCOUNT` | | `'username.bsky.social'` | Account that will create the post |
| `BSKY_APP_PASS` | | | Highly recommended to create a dedicated app password |
| `BSKY_POST_LAG` | `1800` | | Time (in seconds) to wait before ignoring a pending social media post. e.g. If an aircraft was noted 40 minutes ago but for some reason a post couldn't be made, stop trying to create this post after `BSKY_POST_LAG` seconds |
| `AZ_BACKUP_ENABLED` | `'FALSE'` | `'TRUE','FALSE'` | Set to `TRUE` if you want nightly data backups to an Azure blob container<br>If `POSTGRES_ENABLED` is `TRUE` no cloud backups are taken|
| `AZ_STORAGE_ACCOUNT_URL` | | | Full domain name of your Az storage account<br>Ignored if `AZ_BACKUP_ENABLED` is `FALSE` |
| `AZ_STORAGE_ACCOUNT_KEY` | | | Key to access your storage account<br>Ignored if `AZ_BACKUP_ENABLED` is `FALSE` |
| `AZ_CONTAINER_NAME` | | | Blob container name in your storage account<br>Ignored if `AZ_BACKUP_ENABLED` is `FALSE` |
| `AZ_CONTAINER_FOLDER` | | | Top level folder name inside your blob container. Keep a trailing slash! e.g. `'Pending/'`<br>Ignored if `AZ_BACKUP_ENABLED` is `FALSE` |

### docker-compose

-Sample configuration for the aero alerts application bundled with a dedicated pgSQL backend

```yaml
---
services:
  aero-alerts:
    image: fortside/aero-alerts:latest
    container_name: aero-alerts
    restart: always
    volumes:
      - aerodata:/data
    environment:
      - LOG_LEVEL=INFO
      - ADSB_HISTORY_ENABLED=true
      - POSTGRES_ENABLED=true
      - POSTGRES_SERVER=aero_db
      - POSTGRES_PORT=5432
      - POSTGRES_DATABASE=aero-alerts
      - POSTGRES_USER=aero-user
      - POSTGRES_PASSWORD=aero-pass
      - ADSB_SAVE_FOLDER=/data
      - LIVE_DATA_URL=http://adsbexchange.local/tar1090/data/aircraft.json
      - MY_LAT=0
      - MY_LON=0
      - AIRSPACE_RADIUS_KM=10
      - RECORD_RADIUS_KM=100
      - SLEEP_TIME=10
      - AIRCRAFT_DEBOUNCE=3600
      - AEROAPI_ENABLED=true
      - AEROAPI_LIMIT=10
      - AEROAPI_KEY=abc123
      - BSKY_POST_ENABLED=true
      - BSKY_ACCOUNT=myaccount.bsky.social
      - BSKY_APP_PASS=abc123
      - BSKY_POST_LAG=1800
      - AZ_BACKUP_ENABLED=false
      - AZ_STORAGE_ACCOUNT_URL=https://mystorageaccount.blob.core.windows.net
      - AZ_STORAGE_ACCOUNT_KEY=abc123
      - AZ_CONTAINER_NAME=aeroalertsfeed
      - AZ_CONTAINER_FOLDER=Pending/
    networks:
      - aero-network
    depends_on:
      - aero_db
  aero_db:
    image: postgres:16-alpine
    container_name: aero_db
    restart: always
    environment:
      - POSTGRES_USER=aero-user
      - POSTGRES_PASSWORD=aero-pass
      - POSTGRES_DB=aero-alerts
    ports:
      - "5432:5432"
    volumes:
      - aerodb:/var/lib/postgresql/data
    networks:
      - aero-network
volumes:
  aerodata:
  aerodb:
networks:
  aero-network:
```

### Basic docker-compose

-Sample basic configuration to post when an aircraft enters your airspace and not keep a local flight history

```yaml
---
services:
  aero-alerts:
    image: fortside/aero-alerts:latest
    container_name: aero-alerts
    restart: always
    volumes:
      - aerodata:/data
    environment:
      - MY_LAT=0
      - MY_LON=0
      - BSKY_POST_ENABLED=true
      - BSKY_ACCOUNT=myaccount.bsky.social
      - BSKY_APP_PASS=abc123
      - BSKY_POST_LAG=1800
volumes:
  aerodata:
```

-Sample configuration to only track flight history in your airspace

```yaml
---
services:
  aero-alerts:
    image: fortside/aero-alerts:latest
    container_name: aero-alerts
    restart: always
    volumes:
      - aerodata:/data
    environment:
      - MY_LAT=0
      - MY_LON=0
      - ADSB_HISTORY_ENABLED=true
volumes:
  aerodata:
```
