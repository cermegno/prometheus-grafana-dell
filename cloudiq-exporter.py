from prometheus_client import start_http_server, Gauge, Counter, Enum
import requests
import time
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

debug = 1
### Adjust this section to your environment
baseurl = "https://cloudiq.apis.dell.com/cloudiq/rest/v1/"
interval = 300 #Amount of secs between polls
cid = "l76b0b05c680fc00000000001111111111"
secret = "b8f55b73cdc600000000001111111111"

headers = {"Content-type": "application/json"}
token = ""

authurl = "https://cloudiq.apis.dell.com/auth/oauth/v2/token"
authheaders = {'Content-Type': 'application/x-www-form-urlencoded'}
authdata = {
    'grant_type': 'client_credentials',
    'client_id': cid,
    'client_secret': secret
}

### Create Prometheus metrics ###
# Sample Storage array metrics
STORAGE_FREE_PERCENT = Gauge('storage_free_percent','Percentage of free storage',['name','system_type'])
STORAGE_FREE_SIZE = Gauge('storage_free_size','Free storage in Gigabytes',['name','system_type'])
STORAGE_IOPS = Gauge('storage_iops','Storage operations per second',['name','system_type'])
STORAGE_BANDWIDTH = Gauge('storage_bandwidth','Data transferred in Mbps per second',['name','system_type'])
STORAGE_LATENCY = Gauge('storage_latency','Latency in microseconds',['name','system_type'])

# Sample metrics for server systems
SERVER_INLET_TEMPERATURE = Gauge('server_inlet_temperature','Temperature in degree Celsius',['name','model'])
SERVER_POWER_CONSUMPTION = Gauge('server_power_consumption','Power consumption in Watts',['name','model'])
SERVER_CPU_USAGE_PERCENTAGE = Gauge('server_cpu_usage_percentage','Average cpu usage percent',['name','model'])
SERVER_MEM_USAGE_PERCENTAGE = Gauge('server_mem_usage_percentage','Average memory usage percent',['name','model'])

# Sample metrics for volumes
VOLUME_TOTAL_SIZE = Gauge('volume_total_size','Volume size in Gigabytes',['id'])
VOLUME_ALLOCATED_SIZE = Gauge('volume_allocated_size','Volume allocated size in Gigabytes',['id'])
VOLUME_DATA_REDUCTION_RATIO = Gauge('volume_data_reduction_ratio','Volume data reduction ratio',['id'])
VOLUME_SNAPSHOT_COUNT = Gauge('volume_snapshot_count','Number of snapshots from the volume',['id'])
VOLUME_SNAPSHOT_SIZE = Gauge('volume_snapshot_size','Space used by snapshots in Gigabytes',['id'])

def get_token():

    global token
    resp = requests.post(authurl, data=authdata, headers=authheaders)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        print("\nToken = " + json_resp['access_token'])
        token = json_resp['access_token']
        return 
    else:
        print("Failed to get a Token")
        return
        
def storage_details():

    global token
    url = baseurl + "storage_systems"
    #You can use a filter in the query to get only the systems you need. Ex:
    #url = baseurl + "storage_systems?filter=location ilike 'SINGAPORE'"
    #You can find more examples at: https://developer.dell.com/apis/
    headers["Authorization"] = "Bearer " + token
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        if debug: print("\nCollecting Storage information")
        for each_item in json_resp["results"]:
            if debug: print(each_item["system_type"], each_item["display_identifier"])
            STORAGE_FREE_PERCENT.labels(name=each_item["display_identifier"],system_type=each_item["system_type"]).set(each_item.get("free_percent",0))
            STORAGE_FREE_SIZE.labels(name=each_item["display_identifier"],system_type=each_item["system_type"]).set(each_item.get("free_size",0)/1073741824)
            STORAGE_IOPS.labels(name=each_item["display_identifier"],system_type=each_item["system_type"]).set(each_item.get("iops",0))
            STORAGE_BANDWIDTH.labels(name=each_item["display_identifier"],system_type=each_item["system_type"]).set(each_item.get("bandwidth",0)/8388608)
            STORAGE_LATENCY.labels(name=each_item["display_identifier"],system_type=each_item["system_type"]).set(each_item.get("latency",0))
    else:
        print("Collection of Storage data failed")

    return

def server_details():

    global token
    url = baseurl + "server_systems"
    headers["Authorization"] = "Bearer " + token
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        if debug: print("\nCollecting Server information")
        for each_item in json_resp["results"]:
            if debug: print(each_item["model"], each_item["display_identifier"])
            SERVER_INLET_TEMPERATURE.labels(name=each_item["display_identifier"],model=each_item["model"]).set(each_item.get("inlet_temperature",0))
            SERVER_POWER_CONSUMPTION.labels(name=each_item["display_identifier"],model=each_item["model"]).set(each_item.get("power_consumption",0))
            SERVER_CPU_USAGE_PERCENTAGE.labels(name=each_item["display_identifier"],model=each_item["model"]).set(each_item.get("cpu_usage_percent",0))
            SERVER_MEM_USAGE_PERCENTAGE.labels(name=each_item["display_identifier"],model=each_item["model"]).set(each_item.get("memory_usage_percent",0))

    else:
        print("Collection of Server data failed")

    return

def volume_details():

    global token
    url = baseurl + "volumes"
    headers["Authorization"] = "Bearer " + token
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        if debug: print("\nCollecting Volume information")
        for each_item in json_resp["results"]:
            if debug: print(each_item["id"])
            VOLUME_TOTAL_SIZE.labels(id=each_item["id"]).set(each_item.get("total_size",0)/1073741824)
            VOLUME_ALLOCATED_SIZE.labels(id=each_item["id"]).set(each_item.get("allocated_size",0)/1073741824)
            VOLUME_DATA_REDUCTION_RATIO.labels(id=each_item["id"]).set(each_item.get("data_reduction_ratio",0))
            VOLUME_SNAPSHOT_COUNT.labels(id=each_item["id"]).set(each_item.get("snapshot_count",0))
            VOLUME_SNAPSHOT_SIZE.labels(id=each_item["id"]).set(each_item.get("snapshot_size",0)/1073741824)
            
    else:
        print("Collection of Volume data failed")

    return


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8000)
    print("Point your browser to 'http://<your_ip>:8000/metrics' to see the metrics ...")

    while True:
        print("Collecting now ... \n")
        start = time.time()

        get_token()
        storage_details()
        server_details()
        volume_details()
        end = time.time()
        print("\nCollection completed in ", "%.2f" % (end - start), " seconds")
        
        time_to_sleep = interval - int(end - start)
        print("Now sleeping for " + str(time_to_sleep) + " secs")
        time.sleep(time_to_sleep)

