# promexp

Promexp is a stand-alone service which acts as a simplified replacement of Prometheus node exporter.
Along with basic system metrics, it provides information useful in a broadcast environment. 

Configuration
-------------

Most features work out of the box. Configure the exporter with command-line
arguments or `PROMEXP_*` environment variables or command-line arguments.

Run `python -m promexp --help` to see the available options. For example:

```sh
python -m promexp \
  --listen-address 127.0.0.1 \
  --listen-port 8080 \
  --prefix system \
  --hostname exporter-01 \
  --tag site_name=TV1
```

The same configuration can be supplied through the environment:

```sh
PROMEXP_LISTEN_ADDRESS=127.0.0.1 \
PROMEXP_LISTEN_PORT=8080 \
PROMEXP_PREFIX=system \
PROMEXP_HOSTNAME=exporter-01 \
python -m promexp --tag site_name=TV1
```

### Listening address

By default, the built-in HTTP server listens on all interfaces on port 9731.
Override this with `--listen-address` / `PROMEXP_LISTEN_ADDRESS` and
`--listen-port` / `PROMEXP_LISTEN_PORT`.

### Hostname

The software automatically attaches a `hostname` tag to each published metrics.
Disable this behavior with `--hostname false` or `PROMEXP_HOSTNAME=false`, or
override the machine name with `--hostname NAME` or `PROMEXP_HOSTNAME=NAME`.


### Prefix

By default, all metric names are prefixed with the string `nebula_`. 
Change the prefix with `--prefix` or `PROMEXP_PREFIX`.
A trailing underscore of the prefix is added automatically.

### Additional tags

Use `--tag KEY=VALUE` one or more times to append additional tags to each
metric. For example, this can create a server group or specify a client name in
a multitenant environment:

```sh
python -m promexp --tag site_name=TV1 --tag group=playout
```

Providers
---------

Each provider returns a set of metrics. By default, all providers are enabled, when supported on the platform.


### psutil

This provider returns basic machine metrics such as CPU and RAM usage.

Name                 | Type    | Unit    | Description
---------------------|---------|---------|-------------
`uptime_seconds`     | counter | seconds | ...
`cpu_usage`          | gauge   | percent | ...
`memory_bytes_total` | gauge   | bytes   | ...
`memory_bytes_free`  | gauge   | bytes   | ...
`memory_usage`       | gauge   | percent | ...
`swap_bytes_total`   | gauge   | bytes   | ...
`swap_bytes_free`    | gauge   | bytes   | ...
`swap_usage`         | gauge   | percent | ...
`disk_read_bytes`    | counter | bytes   | ...
`disk_write_bytes`   | counter | bytes   | ...

### network

#### Settings

Name              | Type    | Default | Description
------------------|---------|---------|------------
`--network-ignore-inactive` / `PROMEXP_NETWORK_IGNORE_INACTIVE` | boolean | `true` | Do not export metrics for interfaces without traffic
`--network-interfaces` / `PROMEXP_NETWORK_INTERFACES` | string | all interfaces | Comma-separated interface whitelist

#### Exported metrics

Name                       | Type    | Unit  | Description
---------------------------|---------|-------|-------------
`network_sent_bytes_total` | Counter | bytes | ...
`network_recv_bytes_total` | Counter | bytes | ...

### nvidia

Uses `nvidia-smi` to obtain and return metrics of NVIDIA GPUs

#### Settings

Name       | Type   | Default             | Description
-----------|--------|---------------------|------------
`--nvidia-smi-path` / `PROMEXP_NVIDIA_SMI_PATH` | string | `null` (autodetect) | Path to the `nvidia-smi` application binary

#### Exported metrics

Name              | Type  | Unit           | Description
------------------|-------|----------------|-------------
`gpu_usage`       | gauge | percent        | Current utilization of the GPU core
`gpu_memory`      | gauge | percent        | Current GPU RAM usage
`gpu_encoder`     | gauge | percent        | Utilization of the nvenc video encoder
`gpu_decoder`     | gauge | percent        | Utilization of the nvdec video decoder
`gpu_fan_speed`   | gauge | percent        | Current fan speed
`gpu_temperature` | gauge | Degree Celsius | GPU core temperature 
`gpu_power_draw`  | gauge | Watt           | Current power consumption of the card

### storage

Returns storage utilization information for each mountpoint/drive.

Configure a comma-separated mountpoint whitelist with `--storages` or
`PROMEXP_STORAGES`.

#### Exported metrics

Name | Type | Unit | Description
-----|------|------|-------------
`storage_bytes_total` | gauge | bytes   | ...
`storage_bytes_free`  | gauge | bytes   | ...
`storage_usage`       | gauge | percent | ...

### storagespaces

On Windows, this provider shows a health status of each configured storage space.

#### Exported metrics

Name                  | Type  | Unit    | Description
----------------------|-------|---------|-------------
storage_space_healthy | gauge | boolean | While `1` indicates nominal status, `0` indicates a problem (typically a degraded array)

`storage_space_healthy` metric contains two tags `name` and `mode`, which may be used for filtering.

### casparcg

#### Settings

Name       | Type    | Default       | Description
-----------|---------|---------------|------------
`--caspar-host` / `PROMEXP_CASPAR_HOST` | string | `null` | IP address or hostname of the target CasparCG instance
`--caspar-port` / `PROMEXP_CASPAR_PORT` | integer | `5250` | AMCP port of the target CasparCG instance
`--caspar-osc-port` / `PROMEXP_CASPAR_OSC_PORT` | integer | `6250` | OSC listening port (server listens on all interfaces)
`--caspar-heartbeat-interval` / `PROMEXP_CASPAR_HEARTBEAT_INTERVAL` | integer | `10` | Seconds between `VERSION` heartbeat commands

Set `--caspar-host` or `PROMEXP_CASPAR_HOST` to configure the CasparCG provider;
the remaining CasparCG options are applied only when a host is set.


#### Exported metrics

Name                    | Type    | Unit    | Description
------------------------|---------|---------|-------------
casparcg_connected      | Gauge   | boolean | Returns `1` when CasparCG connection is estabilished
casparcg_idle_seconds   | Gauge   | seconds | Time elapsed since last OSC message. Shouldn't be much higher than 1/FPS
casparcg_dropped_total  | Counter | none    | A number of dropped frames per channel since the application started
casparcg_peak_volume    | Gauge   | Percent | Audio peak value per channel since the last request

`casparcg_peak_volume` may either help you determine whether the channel playback is stalled 
(assuming audio should always play, you may check for zero values)
or to find out there is an audio channel with a posibility of clipping audio (check for 100%).

`casparcg_dropped_frames` metric is not available with CasparCG &gt;2.2


Acknowledgements
----------------

### psutil

As a system metrics source, [psutil](https://github.com/giampaolo/psutil) module by giampaolo is used.

### python-osc

CasparCG provider uses public domain [python-osc](https://github.com/attwad/python-osc) module by attwad.
