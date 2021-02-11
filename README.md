# promexp

Promexp is a stand-alone service (Windows/Linux), which acts as a simplified replacement of Prometheus node exporter.
Along with basic system metrics, it provides information useful in a broadcast environment. 

Configuration
-------------

Most of the features should work out of the box, but you may tweak the settings using a `settings.json`
file stored in the same directory as the application. All of the variables are optional.

```json
{
    "host" : "localhost",
    "port" : 8080,
    "hostname" : "thismachinehasanothername",
    "prefix" : "system",
    "tags" : {
        "site_name" : "TV1"
    },
    "provider_settings" : {}
}
```

### Listening address

By default, the built-in HTTP server listens on all interfaces on port 9731.
When needed, you may override this using `host` and `port` variables.

### Hostname

The software automatically attaches a `hostname` tag to each published metrics.
You may disable this behavior by setting the `hostname` variable to `null` or 
override the machine name by setting it to a string value. 


### Prefix

By default, all metric names are prefixed with the string `nebula_`. 
It is possible to change the prefix by setting the `prefix` to a string value. 
A trailing underscore of the prefix is added automatically.

### Additional tags

Using the `tags` dictionary, you may specify additional tags to be appended to each metric.
For example to create a server group or specify a client name in a multitenant environment.

Providers
---------

Each provider returns a set of metrics. By default, all providers are enabled, when supported on the platform.
You may explicitly disable a provider by setting its configuration to `null`:

```json
{
   "provider_settings" : {
       "nvidia" : null,
       "casparcg" : {"host" : "10.0.1.15"}
   } 
}
```


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
`ignore_inactive` | boolean | `true`  | Do not export metrics for interfaces without traffic

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
`smi_path` | string | `null` (autodetect) | Path to the `nvidia-smi` application binary

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
`host`     | string  | `"127.0.0.1"` | IP address or a hostname of the target CasparCG instance
`port`     | integer | `5250`        | AMCP port of the target CasparCG instance
`osc_port` | integer | `6250`        | OSC listening port (server listens on all interfaces)
`force`    | boolean | `false`       | Do not disable the provider when CasparCG is not available during startup (keep retrying to connect)
`heartbeat_interval` | float | `10`  | Number of seconds after which the provider sends a heartbeat `VERSION` command


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

Building on Windows
-------------------

We use Nuitka to build the application. You may as well:

 1. Download and install [Python 3.8](https://www.python.org/ftp/python/3.8.7/python-3.8.7-amd64.exe) (any version &gt;3.6 should work should work)
 2. When asked, select "install for all users" and "install pip"
 3. Start a terminal (cmd) as an administrator
 4. Run `pip install psutil nuitka nxtools`
 5. Install [MinGW](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/installer/mingw-w64-install.exe/download)
 6. Create an environment variable called `CC` containing a path to `gcc.exe` binary from the MinGW package 
 7. Run `build.bat` from the `promexp` directory
 8. After a while, resulting binary should be located in `promexp.dist`


Acknowledgements
----------------

### Prometheus

Thanks to [Prometheus](https://prometheus.io) developers for their great work!

### psutil

As a system metrics source, [psutil](https://github.com/giampaolo/psutil) module by giampaolo is used.

### python-osc

CasparCG provider uses public domain [python-osc](https://github.com/attwad/python-osc) module by attwad.

### nuitka

Windows binary is built using [nuitka](https://nuitka.net).