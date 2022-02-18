from prometheus_client import start_http_server, Gauge, Counter, Enum
import requests
import time
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

### Adjust this section to your environment
baseurl = "https://10.1.1.1/api/rest" # Use the IP of your PowerStore
username = "user"
password = "password"
interval = "Five_Mins" #Five_Mins, One_Hour or One_Day. Don't use Twenty_Sec with this script, because it uses different schema
headers = {"Content-type": "application/json"}

# Create Prometheus metrics
CAPACITY_USED = Gauge('cap_used', 'Capacity used in GB')
CAPACITY_TOTAL = Gauge('cap_total', 'Capacity total in GB')
DATA_REDUCTION = Gauge('data_reduction', 'Data Reduction Ratio')
APPLIANCE_IOPS_READ = Gauge('appliance_iops_read', 'Appliance Read IOPS')
APPLIANCE_IOPS_WRITE = Gauge('appliance_iops_write', 'Appliance Write IOPS')
APPLIANCE_BANDW_READ = Gauge('appliance_bandwidth_read', 'Appliance Read Bandwidth')
APPLIANCE_BANDW_WRITE = Gauge('appliance_bandwidth_write', 'Appliance Write Bandwidth')
APPLIANCE_IOPS_TOTAL = Gauge('appliance_iops_total', 'Appliance Total IOPS')
APPLIANCE_BANDW_TOTAL = Gauge('appliance_bandwidth_total', 'Appliance Total Bandwidth')
APPLIANCE_LATENCY_TOTAL = Gauge('appliance_latency_total', 'Appliance Total Latency')
APPLIANCE_IOSIZE_TOTAL = Gauge('appliance_iosize_total', 'Appliance Total IO Size')
VOL_IOPS_READ = Gauge('vol_iops_read','Volume Read IOPS',['vol_name'])
VOL_IOPS_WRITE = Gauge('vol_iops_write','Volume Write IOPS',['vol_name'])
VOL_BANDW_READ = Gauge('vol_bandwith_read','Volume Read Bandwidth',['vol_name'])
VOL_BANDW_WRITE = Gauge('vol_bandwidth_write','Volume Write Bandwidth',['vol_name'])
VOL_IOSIZE_READ = Gauge('vol_iosize_read','Volume Read IO Size in Bytes????',['vol_name'])
VOL_IOSIZE_WRITE = Gauge('vol_iosize_write','Volume Write IO Size in Bytes???',['vol_name'])
VOL_LATENCY_READ = Gauge('vol_latency_read','Volume Read IO Latency in ms???',['vol_name'])
VOL_LATENCY_WRITE = Gauge('vol_latency_write','Volume Write IO Latency in ms???',['vol_name'])
FC_IOPS_READ = Gauge('fc_iops_read','FC port Read IOPS',['fc_name'])
FC_IOPS_WRITE = Gauge('fc_iops_write','FC port Write IOPS',['fc_name'])
FC_BANDW_READ = Gauge('fc_bandwitdh_read','FC port Read Bandwidth',['fc_name'])
FC_BANDW_WRITE = Gauge('fc_bandwidth_write','FC port Write Bandwidth',['fc_name'])
ETH_BANDW_READ = Gauge('eth_bandwitdh_read','Ethernet port Read Bandwidth in bits per sec',['eth_name'])
ETH_BANDW_WRITE = Gauge('eth_bandwidth_write','Ethernet port Write Bandwidth in bits per sec',['eth_name'])
HEALTH = Gauge('array_health', 'Overall health of the array as a percentage')

def get_token():
    ### We need to run a GET call first in order to get the CSRF token
    global headers
    url = baseurl + "/cluster"
    resp = requests.get(url, auth=(username, password), headers=headers, verify=False)
    token = resp.headers['DELL-EMC-TOKEN']
    headers["DELL-EMC-TOKEN"] = token
    return 

def appliance_cap_metrics():
    ### Appliance level capacity metrics
    url = baseurl + "/metrics/generate"
    json_body = {"entity": "space_metrics_by_appliance", "entity_id": "A1","interval": interval}
    resp = requests.post(url, json=json_body, auth=(username, password), headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        ### Update Prometheus metrics
        CAPACITY_USED.set(json_resp[-1]['physical_used'])
        CAPACITY_TOTAL.set(json_resp[-1]['physical_total'])
        DATA_REDUCTION.set(json_resp[-1]['data_reduction'])
		
        # Health computation section
		# In this example:
		# Used capacity > 80% means health impact of 10
		# Used capacity > 90% means health impact of 20
        health_impact = 0
        if json_resp[-1]['physical_used'] * 100 / json_resp[-1]['physical_total'] > 80: health_impact = 10
        if json_resp[-1]['physical_used'] * 100 / json_resp[-1]['physical_total'] > 90: health_impact = 20
    else:
        print("Failed to get Capacity metrics")
        health_impact = 50

    return health_impact

def appliance_perf_metrics():

    ### Appliance level performance metrics
    url = baseurl + "/metrics/generate"
    json_body = {"entity": "performance_metrics_by_appliance","entity_id": "A1","interval": interval}
    resp = requests.post(url, json=json_body, auth=(username, password), headers=headers, verify=False)
    if resp.status_code == 200:
        json_resp = json.loads(resp.content)
        #print(json_resp)
        ### Update Prometheus metrics
        APPLIANCE_IOPS_READ.set(json_resp[-1]['avg_read_iops'])
        APPLIANCE_IOPS_WRITE.set(json_resp[-1]['avg_write_iops'])
        APPLIANCE_BANDW_READ.set(json_resp[-1]['avg_read_bandwidth'])
        APPLIANCE_BANDW_WRITE.set(json_resp[-1]['avg_write_bandwidth'])
        APPLIANCE_IOPS_TOTAL.set(json_resp[-1]['avg_total_iops'])
        APPLIANCE_BANDW_TOTAL.set(json_resp[-1]['avg_total_bandwidth'])
        APPLIANCE_LATENCY_TOTAL.set(json_resp[-1]['avg_latency'])
        APPLIANCE_IOSIZE_TOTAL.set(json_resp[-1]['avg_io_size'])

        # Health computation section. This is an example with 2 health thresholds per metric
        health_impact = 0
        if json_resp[-1]['avg_read_iops'] > 50000: health_impact = 10
        if json_resp[-1]['avg_read_iops'] > 200000 and health_impact < 10: health_impact = 20
        if json_resp[-1]['avg_write_iops'] > 30000 and health_impact < 10: health_impact = 10
        if json_resp[-1]['avg_write_iops'] > 100000 and health_impact < 10: health_impact = 20

    else:
        print("Failed to get Performance metrics") 
        health_impact = 50

    return health_impact

def volume_perf_metrics():
    ### Volume-level performance metrics

	# First we get a list of volumes. We get the "type" as well so that we can filter out snapshots
    url = baseurl + "/volume?select=id,name,type"
    resp_vols = requests.get(url, auth=(username, password), headers=headers, verify=False)

    # Now we are going to get the metrics for each individual volume
    url = baseurl + "/metrics/generate"
    for each_vol in resp_vols.json():
        if each_vol["type"] != "Snapshot": # I am not tracking performance of snapshots
            json_body = {"entity": "performance_metrics_by_volume","entity_id": each_vol["id"] ,"interval": interval}
            resp = requests.post(url, json=json_body, auth=(username, password), headers=headers, verify=False)
            json_resp = json.loads(resp.content)
            if len(json_resp) > 0:
                VOL_IOPS_READ.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_read_iops"])
                VOL_IOPS_WRITE.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_write_iops"])
                VOL_BANDW_READ.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_read_bandwidth"])
                VOL_BANDW_WRITE.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_write_bandwidth"])
                VOL_IOSIZE_READ.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_read_size"])
                VOL_IOSIZE_WRITE.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_write_size"])
                VOL_LATENCY_READ.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_read_latency"])
                VOL_LATENCY_WRITE.labels(vol_name=each_vol["name"]).set(json_resp[-1]["avg_write_latency"])
            else: # If no data is given for a volume then make the value 0 
                VOL_IOPS_READ.labels(vol_name=each_vol["name"]).set(0)
                VOL_IOPS_WRITE.labels(vol_name=each_vol["name"]).set(0)
                VOL_BANDW_READ.labels(vol_name=each_vol["name"]).set(0)
                VOL_BANDW_WRITE.labels(vol_name=each_vol["name"]).set(0)
                VOL_IOSIZE_READ.labels(vol_name=each_vol["name"]).set(0)
                VOL_IOSIZE_WRITE.labels(vol_name=each_vol["name"]).set(0)
                VOL_LATENCY_READ.labels(vol_name=each_vol["name"]).set(0)
                VOL_LATENCY_WRITE.labels(vol_name=each_vol["name"]).set(0)
    return


def fe_fc_port_perf_metrics():

    ### FC Port performance metrics

    # First we get a list of ports
    url = baseurl + "/fc_port?select=id,name"
    resp_fc_ports = requests.get(url, auth=(username, password), headers=headers, verify=False)

    # Now we are going to get the metrics for each individual port
    url = baseurl + "/metrics/generate"
    for each_port in resp_fc_ports.json():
        json_body = {"entity": "performance_metrics_by_fe_fc_port","entity_id": each_port["id"] ,"interval": interval}
        resp = requests.post(url, json=json_body, auth=(username, password), headers=headers, verify=False)
        json_resp = json.loads(resp.content)
        FC_IOPS_READ.labels(fc_name=each_port["name"]).set(json_resp[-1]["avg_read_iops"])
        FC_IOPS_WRITE.labels(fc_name=each_port["name"]).set(json_resp[-1]["avg_write_iops"])
        FC_BANDW_READ.labels(fc_name=each_port["name"]).set(json_resp[-1]["avg_read_bandwidth"])
        FC_BANDW_WRITE.labels(fc_name=each_port["name"]).set(json_resp[-1]["avg_write_bandwidth"])
    return

def fe_eth_port_perf_metrics():

    ### Ethernet Port performance metrics
	
    # First we get a list of ports
    url = baseurl + "/eth_port?select=id,name"
    resp_eth_ports = requests.get(url, auth=(username, password), headers=headers, verify=False)

    # Now we are going to get the metrics for each individual port
    url = baseurl + "/metrics/generate"
    for each_port in resp_eth_ports.json():
        json_body = {"entity": "performance_metrics_by_fe_eth_port","entity_id": each_port["id"] ,"interval": interval}
        resp = requests.post(url, json=json_body, auth=(username, password), headers=headers, verify=False)
        json_resp = json.loads(resp.content)
        ETH_BANDW_READ.labels(eth_name=each_port["name"]).set(json_resp[-1]["avg_bytes_tx_ps"])
        ETH_BANDW_WRITE.labels(eth_name=each_port["name"]).set(json_resp[-1]["avg_bytes_rx_ps"])
    return

def calculate_health(health_items): 
    current_health = 100 - max(health_items) # Use this to take the max impact across all categories
    #current_health = 100 - sum(health_items) # Use this to show cumulative impact of multiple issues
    HEALTH.set(current_health) # The resulting health value will be stored as a metric in Prometheus
    return

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8000)
    print("Point your browser to 'http://<your_ip>:8000/metrics' to see the metrics ...")

    while True:
        print("Collecting now ... ", end="", flush=True)
        health_items = [] # List to store health impact 
        start = time.time()

        get_token()
        health_items.append(appliance_cap_metrics()) #This is being used to calculate health
        health_items.append(appliance_perf_metrics()) #This is being used to calculate health
        volume_perf_metrics()
        fe_fc_port_perf_metrics()
        fe_eth_port_perf_metrics()
        calculate_health(health_items)

        end = time.time()
        print("collection completed in ", "%.2f" % (end - start), " seconds")
        time.sleep(300)



