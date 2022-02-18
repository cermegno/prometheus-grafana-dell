# prometheus-grafana-dell
Collection of Prometheus exporters and Grafana dashboards for Dell Technologies products for educational purposes. Use at your own risk
For detailed instructions on how to use this content and for explanation on how it all works visit the accompanying blog post:
https://vexpose.blog/2022/02/18/prometheus-exporter-for-powerstore/


## Prometheus Exporters
The following Python exporters have been provided
- PowerStore
- PowerEdge (Redfish)

## Grafana Dashboards
The following dashboards have been provided:
- PowerStore details: Includes capacity and performance metrics, for the appliance as well as for individual volumes and ports
- PowerEdge details: Includes Power, Voltage, Fans and Temperature metrics
- Storage Summary: Shows all important storage metrics for a given PowerStore in a single row. Add multiple rows to show multiple arrays
- Health Summary: This shows the Health metrics that are produced by the PowerStore and PowerEdge exporters

![Storage Summary Dashboard](https://vexposeblog.files.wordpress.com/2022/02/storage-summary.png)
![Storage Summary Dashboard](https://vexposeblog.files.wordpress.com/2022/02/grafana-powerstore.png)
![Storage Summary Dashboard](https://vexposeblog.files.wordpress.com/2022/02/poweredge.png)
