# Importing the external libraries.
from flask import Flask, request, jsonify
import threading
import requests
import time

# Importing the internal libraries.
from cerber import SecurityManager
from schemas import SentimentTextSchema, AwakeRequestSchema, IncreaseDecreaseSchema
from config import ConfigManager

# Loading the configuration from the configuration file.
config = ConfigManager("config.ini")

# Creation of the Security Manager.
security_manager = SecurityManager(config.security.secret_key)
# TODO: don't forget to set it when it gets the service awake.
sentiment_analysis_security_manager = None
cache_security_managers = []

# Creation of the validation schemas.
sentiment_schema = SentimentTextSchema()
awake_schema = AwakeRequestSchema()
increase_decrease_schema = IncreaseDecreaseSchema()

SERVICE_NAME = None
SERVICE_HOST = None
SERVICE_KEY = None
SERVICE_PORT = None

CACHE_SERVICES = None

DATA_WAREHOUSE_DATA = {}

# Setting up the Flask dependencies.
app = Flask(__name__)
app.secret_key = config.security.secret_key


def send_heartbeats():
    '''
        This function sends heartbeat requests to the service discovery.
    '''
    global sentiment_analysis_security_manager, SERVICE_NAME, SERVICE_HOST, SERVICE_KEY, SERVICE_PORT
    # Creating the request body for the inference endpoint.
    test_json = {
        "correlation_id" : "heartbeat",
        "text" : "test"
    }
    # Sending requests till a successful response.
    while True:
        # Computing the HMAC of the request for the inference service.
        service_hmac = sentiment_analysis_security_manager._SecurityManager__encode_hmac(test_json)
        try:
            # Sending the request.
            response = requests.get(
                f"http://{SERVICE_HOST}:{SERVICE_PORT}/sentiment",
                json = test_json,
                headers = {"Token" : service_hmac}
            )
            status_code = response.status_code
        except Exception as e:
            # In case of an exception a 503 status code is created.
            status_code = 503
        if status_code == 200 or status_code == 429:
            # In case of a successful request a heartbeat request is sent to the Service Discovery.
            # Computing the HMAC of the request for the Service Discovery.
            service_discovery_hmac = SecurityManager(
                config.service_discovery.secret_key
            )._SecurityManager__encode_hmac({"status_code" : status_code})

            # Sending the request to the Service Discovery.
            response = requests.post(
                f"http://{config.service_discovery.host}:{config.service_discovery.port}/heartbeat/{config.general.name}",
                json={"status_code" : status_code},
                headers={"Token" : service_discovery_hmac}
            )
            if response.status_code == 200:
                time.sleep(60)
        else:
            print("Failed Heartbeat")
            time.sleep(20)

@app.route("/awake", methods=["POST"])
def awake():
    global sentiment_analysis_security_manager, SERVICE_NAME, SERVICE_HOST, SERVICE_KEY, SERVICE_PORT, CACHE_SERVICES, DATA_WAREHOUSE_DATA

    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        status_code = 200

        # Validation of the json.
        result, status_code = awake_schema.validate_json(request.json)
        if status_code != 200:
            # If the request body didn't passed the json validation a error is returned.
            return result, status_code
        else:
            # Creating the intent classification security manager.
            sentiment_analysis_security_manager = SecurityManager(result["security"]["secret_key"])

            # Extracting from the request the Intent classification service credentials.
            SERVICE_NAME = result["general"]["name"]
            SERVICE_KEY = result["security"]["secret_key"]
            SERVICE_PORT = result["general"]["port"]
            SERVICE_HOST = result["general"]["host"]

            # Generating the registration credentials for Service Discovery.
            credentials_for_service_discovery = config.generate_info_for_service_discovery()

            # Computing the HMAC for the registration request.
            service_discovery_hmac = SecurityManager(config.service_discovery.secret_key)._SecurityManager__encode_hmac(credentials_for_service_discovery)

            while True:
                # Sending the request to the Service Discovery until a successful response.
                res = requests.post(
                    f"http://{config.service_discovery.host}:{config.service_discovery.port}/{config.service_discovery.register_endpoint}",
                    json=credentials_for_service_discovery,
                    headers={"Token" : service_discovery_hmac}
                )
                if res.status_code == 200:
                    while True:
                        # In case of a successful registration the service is asking for needed services credentials.
                        time.sleep(3)
                        service_discovery_hmac = SecurityManager(config.service_discovery.secret_key)._SecurityManager__encode_hmac(
                            {"service_names" : ["cache-service-1", "cache-service-2", "data-warehouse-service"]}
                        )
                        # Computing the request HMAC.
                        res = requests.get(
                            f"http://{config.service_discovery.host}:{config.service_discovery.port}/get_services",
                            json = {"service_names" : ["cache-service-1", "cache-service-2", "data-warehouse-service"]},
                            headers={"Token" : service_discovery_hmac}
                        )
                        if res.status_code == 200:
                            # In case of the successful request the process of sending heartbeat requests is starting.
                            time.sleep(10)
                            threading.Thread(target=send_heartbeats).start()
                            res_json = res.json()

                            # Extracting the cache credentials.
                            CACHE_SERVICES = [res_json[service_info] for service_info in res_json
                                              if service_info in ["cache-service-1", "cache-service-2"]]

                            # Creating the Security Managers for caches services.
                            for cache in CACHE_SERVICES:
                                cache_security_managers.append(
                                    SecurityManager(cache["security"]["secret_key"])
                                )

                            # Extracting the Data Warehouse credentials.
                            DATA_WAREHOUSE_DATA = {
                                "host" : res_json["data-warehouse-service"]["general"]["host"],
                                "port" : res_json["data-warehouse-service"]["general"]["port"],
                                "security_manager" : SecurityManager(res_json["data-warehouse-service"]["security"]["secret_key"])
                            }
                            break
                    break
                else:
                    time.sleep(10)


            return {
                "code" : 200,
                "message" : "Registered"
            }

@app.route("/serve", methods=["POST"])
def serve():
    global sentiment_analysis_security_manager, SERVICE_NAME, SERVICE_HOST, SERVICE_KEY, SERVICE_PORT, CACHE_SERVICES

    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        status_code = 200

        # Validation of the json.
        result, status_code = sentiment_schema.validate_json(request.json)
        if status_code != 200:
            # If the request body didn't passed the json validation a error is returned.
            return result, status_code
        else:
            # Computing the Inference Service HMAC.
            service_hmac = sentiment_analysis_security_manager._SecurityManager__encode_hmac(result)

            # Making the request to Inference Service.
            response = requests.get(
                f"http://{SERVICE_HOST}:{SERVICE_PORT}/sentiment",
                json = result,
                headers = {"Token" : service_hmac}
            )
            response_json = response.json()

            # Creating the dictionary with error metrics.
            error_metrics = {
                "request_status" : response.status_code,
                "request_reason" : response.reason,
                "db_error" : response_json["errors"]["db_error"]["cause"] if response_json["errors"]["db_error"] is not None else None
            }

            # Creating the metrics JSON and adding the error metrics to them.
            metrics = {key : response_json[key] for key in response_json if key in ["latency", "saturation"]}
            metrics["errors"] = error_metrics

            # Completing the metrics JSON with the correlation id, service name and traffic metrics.
            metrics["correlation_id"] = result["correlation_id"]
            metrics["service_name"] = SERVICE_NAME
            metrics["traffic"] = {
                "write_query" : 1 if error_metrics["db_error"] is not None else 0,
                "read_query" : 0
            }

            # Calculating the HMAC for the Data Warehouse request.
            data_warehouse_hmac = DATA_WAREHOUSE_DATA["security_manager"]._SecurityManager__encode_hmac(metrics)

            # Sending the request to the Data Warehouse.
            data_warehouse_resp = requests.post(
                f"http://{DATA_WAREHOUSE_DATA['host']}:{DATA_WAREHOUSE_DATA['port']}/metrics",
                json = metrics,
                headers = {"Token" : data_warehouse_hmac}
            )

            if response.status_code == 200:
                # Preparing data for response.
                prediction = {
                    "correlation_id" : result["correlation_id"],
                    "text" : result["text"],
                    "prediction" : response_json["prediction"]
                }

                # Preparing data for saving to cache.
                data_for_cache = {
                    "text" : result["text"],
                    "service" : "sentiment",
                    "prediction" : response_json["prediction"]
                }

                # Sending the save request to every caches.
                for i in range(len(CACHE_SERVICES)):
                    # Computing the HMAC for the Cache request.
                    hmac = cache_security_managers[i]._SecurityManager__encode_hmac(data_for_cache)
                    # Sending the request to cache.
                    res = requests.post(
                        f"http://{CACHE_SERVICES[i]['general']['host']}:{CACHE_SERVICES[i]['general']['port']}/save",
                        json=data_for_cache,
                        headers={"Token" : hmac}
                    )

                return prediction, 200
            else:
                return response_json, response.status_code


@app.route("/increase", methods=["POST"])
def increase():
    global sentiment_analysis_security_manager, SERVICE_NAME, SERVICE_HOST, SERVICE_KEY, SERVICE_PORT

    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        status_code = 200

        # Validation of the json.
        result, status_code = increase_decrease_schema.validate_json(request.json)
        if status_code != 200:
            # If the request body didn't passed the json validation a error is returned.
            return result, status_code
        else:
            service_hmac = sentiment_analysis_security_manager._SecurityManager__encode_hmac(result)

            response = requests.post(
                f"http://{SERVICE_HOST}:{SERVICE_PORT}/increase",
                json = result,
                headers = {"Token" : service_hmac}
            )
            return response.json(), response.status_code

@app.route("/decrease", methods=["POST"])
def decrease():
    global sentiment_analysis_security_manager, SERVICE_NAME, SERVICE_HOST, SERVICE_KEY, SERVICE_PORT

    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        status_code = 200

        # Validation of the json.
        result, status_code = increase_decrease_schema.validate_json(request.json)
        if status_code != 200:
            # If the request body didn't passed the json validation a error is returned.
            return result, status_code
        else:
            service_hmac = sentiment_analysis_security_manager._SecurityManager__encode_hmac(result)

            response = requests.post(
                f"http://{SERVICE_HOST}:{SERVICE_PORT}/decrease",
                json = result,
                headers = {"Token" : service_hmac}
            )
            return response.json(), response.status_code


app.run(
    port = config.general.port,
    #host = config.general.host
    host = "0.0.0.0"
)