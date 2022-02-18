from prometheus_client import start_http_server, Gauge, Counter, Enum
import requests
import time
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

### Adjust this section to your environment
baseurl = "https://10.1.1.1/redfish/v1" # Use here the IP address of your iDRAC
interval = "300" #Amount of secs between polls
username = "redfish"
password = ""
headers = {"Content-type": "application/json"}

# Create Prometheus metrics
FAN_SPEED = Gauge('fan_speed','Fan speeds in RPM',['name'])
TEMPERATURE = Gauge('temperature','Temperature of various components in Celsius',['name'])
POWER = Gauge('power','Power Output in Watts',['name'])
VOLTAGE = Gauge('voltage','Voltages',['name'])
HEALTH = Gauge('server_health', 'Health of the system')

def thermal_metrics():

    health = "OK"
    url = baseurl + "/Chassis/System.Embedded.1/Thermal#"
	# The same Redfish API endpoint provides fan and temperature information
    resp = requests.get(url, auth=(username, password), headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        for each_item in json_resp["Fans"]:
            FAN_SPEED.labels(name=each_item["Name"]).set(each_item["Reading"])
            if each_item["Status"]["Health"] != "OK": # Redfish API provides health info for every component
                health = "ERROR"
        for each_item in json_resp["Temperatures"]:
            TEMPERATURE.labels(name=each_item["Name"]).set(each_item["ReadingCelsius"])
            if each_item["Status"]["Health"] != "OK":
                health = "ERROR"
    else:
        print("Failed to get Thermal metrics")

    return health

def power_metrics():

    health = "OK"
    url = baseurl + "/Chassis/System.Embedded.1/Power#"
	# The same Redfish API endpoint provides volts and watts information
    resp = requests.get(url, auth=(username, password), headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        for each_item in json_resp["PowerSupplies"]:
            POWER.labels(name=each_item["Name"]).set(each_item["PowerOutputWatts"])
            if each_item["Status"]["Health"] != "OK":
                health = "ERROR"
        for each_item in json_resp["Voltages"]:
            if each_item["PhysicalContext"] == "PowerSupply":
                VOLTAGE.labels(name=each_item["Name"]).set(each_item["ReadingVolts"])
                if each_item["Status"]["Health"] != "OK":
                    health = "ERROR"
    else:
        print("Failed to get Power metrics")

    return health

def calculate_health(health_items):
    if "ERROR" in health_items:
        HEALTH.set(0) # Convert the health label to a number so that we can use "gauge" metric type
    else:
        HEALTH.set(100)

    return

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8000)
    print("Point your browser to 'http://<your_ip>:8000/metrics' to see the metrics ...")

    while True:
        print("Collecting now ... ", end="", flush=True)
        health_items = [] # List to store health impact from various components
        start = time.time()

        health_items.append(thermal_metrics())
        health_items.append(power_metrics())
        calculate_health(health_items)

        end = time.time()
        print("collection completed in ", "%.2f" % (end - start), " seconds")
        time.sleep(interval)

