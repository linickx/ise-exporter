# ise-exporter  [![Docker Build Statu](https://img.shields.io/docker/build/linickx/ise-exporter.svg)](https://hub.docker.com/r/linickx/ise-exporter/)
A Prometheus Cisco ISE Exporter for the [MNT API](http://www.cisco.com/c/en/us/td/docs/security/ise/2-2/api_ref_guide/api_ref_book/ise_api_ref_ch1.html) and [ERS API](http://www.cisco.com/c/en/us/td/docs/security/ise/2-2/api_ref_guide/api_ref_book/ise_api_ref_ers1.html)

## Examples

To run the ise-exporter, as a minimum you need valid `ise.yml`. You should also generate a CA bundle (PEM File, base64 encoded) of your certificate chain.

### ise.yml
```
adm_node: server
rest_uid: admin
rest_pw: cisco
```

### Docker Command
```
docker run -p 9123:9123 -v /home/nick/ise-exporter/my.ise.yml:/etc/ise-exporter/ise.yml -v /home/nick/ise-exporter/my.ca_bundle.pem:/etc/ise-exporter/ca_bundle.pem linickx/ise-exporter
```

### prometheus.yml
This assumes that prometheus and ise-exporter are on the same host, update as necessary.
```
  - job_name: 'ise'
    scrape_interval: 60s
    static_configs:
        - targets: ['127.0.0.1:9123']
```

## Options
The following settings are optional:

### ISE 1.x MNT API
Older ISE servers can be monitored by adding `rest_ver: 1` to `ise.yml`

### ERS API
If you have the ERS API enabled, you can add `ers_enabled: True` to `ise.yml` to gather more metrics

### Environment Variables
If you're not using Docker, to run as a local python script you can use a different path for the ise.yml and CA bundle; e.g:
```
$ export ISE_FILE=my.ise.yml
$ export CA_FILE=my.ca_bundle.pem
$ ./ise-exporter.py
[INFO]  * Running on http://0.0.0.0:9123/ (Press CTRL+C to quit)
```
