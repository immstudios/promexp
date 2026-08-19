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

When `--host-root` is used, the name is taken from the host `/etc/hostname`
rather than from the container.


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

Metric names
------------

Metric names follow the Prometheus naming conventions: base units (bytes,
seconds, watts, degrees Celsius), the unit as the last component of the name,
and the `_total` suffix reserved for counters. Each metric is exported along
with its `# HELP` and `# TYPE` comments, so `promtool check metrics` passes
without warnings.

Percentages are exported as `0` to `100` (Grafana unit *percent (0-100)*).


Providers
---------

Each provider returns a set of metrics. By default, all providers are enabled, when supported on the platform.


### psutil

This provider returns basic machine metrics such as CPU and RAM usage.

Name                      | Type    | Unit    | Description
--------------------------|---------|---------|-------------
`uptime_seconds`          | gauge   | seconds | Time elapsed since the machine booted
`cpu_usage_percent`       | gauge   | percent | CPU utilization since the previous scrape
`memory_total_bytes`      | gauge   | bytes   | Total physical memory (`MemTotal`)
`memory_free_bytes`       | gauge   | bytes   | Completely unused memory (`MemFree`)
`memory_available_bytes`  | gauge   | bytes   | Memory available for new allocations without swapping (`MemAvailable`)
`memory_used_bytes`       | gauge   | bytes   | Memory which cannot be reclaimed on demand
`memory_cached_bytes`     | gauge   | bytes   | Reclaimable page cache, buffers and slab
`memory_shared_bytes`     | gauge   | bytes   | tmpfs and shared memory (`Shmem`)
`memory_slab_bytes`       | gauge   | bytes   | Kernel data structures (Linux only)
`memory_arc_bytes`        | gauge   | bytes   | ZFS ARC size (only on hosts with ZFS)
`memory_usage_percent`    | gauge   | percent | `memory_used_bytes` / `memory_total_bytes`
`swap_total_bytes`        | gauge   | bytes   | Total swap space
`swap_free_bytes`         | gauge   | bytes   | Unused swap space
`swap_usage_percent`      | gauge   | percent | Used swap space
`disk_read_bytes_total`   | counter | bytes   | Bytes read from all disks
`disk_write_bytes_total`  | counter | bytes   | Bytes written to all disks

#### A note on memory usage

Buffers and page cache are given back to applications as soon as they are
needed, so they are **not** counted as used memory. `memory_usage` therefore
reports `total - free - buffers - cache` (with tmpfs added back, since it can
only be reclaimed to swap), which is roughly what `htop` and desktop memory
indicators show.

This is deliberately less conservative than `MemAvailable`, which the kernel
computes as the amount that can be allocated *without swapping anything out*:
it counts only a part of the page cache as reclaimable, so
`total - available` typically looks much higher than the real utilization.
Use `memory_available_bytes` if you prefer to alert on that instead.

Two things which do show up as used memory even though they are mostly
evictable are ZFS ARC (`memory_arc_bytes`) and kernel slab
(`memory_slab_bytes`). On a file server, ARC alone easily accounts for tens of
percent of `memory_usage_percent`. Both are exported so a dashboard can
subtract them.

### network

#### Settings

Name              | Type    | Default | Description
------------------|---------|---------|------------
`--network-ignore-inactive` / `PROMEXP_NETWORK_IGNORE_INACTIVE` | boolean | `true` | Do not export metrics for interfaces without traffic
`--network-interfaces` / `PROMEXP_NETWORK_INTERFACES` | string | all interfaces | Comma-separated interface whitelist
`--host-root` / `PROMEXP_HOST_ROOT` | string | `null` | Read the counters of the host network namespace. See [running in a container](#monitoring-host-storages-from-a-container).

Interfaces which are down are not exported. Loopback and the virtual
interfaces of container and VM runtimes (`veth*`, `br-*`, `docker*`, `virbr*`,
`vnet*`) are skipped as well, unless they are explicitly whitelisted.

#### Exported metrics

Name                       | Type    | Unit  | Description
---------------------------|---------|-------|-------------
`network_sent_bytes_total` | counter | bytes | Bytes transmitted by the interface
`network_recv_bytes_total` | counter | bytes | Bytes received by the interface

Both metrics are tagged with the `interface` name.

### nvidia

Uses `nvidia-smi` to obtain and return metrics of NVIDIA GPUs

#### Settings

Name       | Type   | Default             | Description
-----------|--------|---------------------|------------
`--nvidia-smi-path` / `PROMEXP_NVIDIA_SMI_PATH` | string | `null` (autodetect) | Path to the `nvidia-smi` application binary

#### Exported metrics

Name                        | Type  | Unit           | Description
----------------------------|-------|----------------|-------------
`gpu_usage_percent`         | gauge | percent        | Current utilization of the GPU core
`gpu_memory_usage_percent`  | gauge | percent        | Current GPU RAM usage
`gpu_encoder_usage_percent` | gauge | percent        | Utilization of the nvenc video encoder
`gpu_decoder_usage_percent` | gauge | percent        | Utilization of the nvdec video decoder
`gpu_fan_speed_percent`     | gauge | percent        | Current fan speed
`gpu_temperature_celsius`   | gauge | degree Celsius | GPU core temperature
`gpu_power_watts`           | gauge | watt           | Current power consumption of the card

Each metric is tagged with the GPU `id` and `model`.

### storage

Returns storage utilization information for each mountpoint/drive. Mountpoints
are autodetected and pseudo filesystems (`proc`, `sysfs`, `tmpfs`, `overlay`,
...) as well as system paths (`/boot`, `/run`, `/var/lib`, ...) are skipped.
The mount table is re-read on every scrape, so storages mounted or unmounted
while promexp is running are picked up.

#### Settings

Name | Type | Default | Description
-----|------|---------|------------
`--storages` / `PROMEXP_STORAGES` | string | all detected | Comma-separated mountpoint whitelist. Entries are prefixes (except `/`, which matches exactly) and override the autodetection filters, so an explicitly listed ramdisk or system path is exported too.
`--host-root` / `PROMEXP_HOST_ROOT` | string | `null` | Directory the host root filesystem is mounted to. See [monitoring host storages from a container](#monitoring-host-storages-from-a-container).

#### Exported metrics

Name | Type | Unit | Description
-----|------|------|-------------
`storage_total_bytes`   | gauge | bytes   | Size of the filesystem
`storage_free_bytes`    | gauge | bytes   | Space available to unprivileged users
`storage_used_bytes`    | gauge | bytes   | Used space
`storage_usage_percent` | gauge | percent | `used / (used + free)`, same as `df`

Each metric is tagged with the `mountpoint` and the `fstype`.

`storage_total_bytes` includes reserved blocks (usually 5% on ext4), which are
not part of `storage_free_bytes`. This is why `total - free` may be slightly
higher than `storage_used_bytes`.

#### Monitoring host storages from a container

A container has its own mount namespace, so by default promexp sees the
container filesystem (an `overlay` root plus whatever docker injected) and not
the host storages.

The host filesystems therefore have to be bind mounted into the container, and
promexp has to be told where they are, so that metrics are tagged with the host
side path:

```sh
docker run -d --name promexp \
  -p 9731:9731 \
  -v /:/host:ro,rslave \
  -e PROMEXP_HOST_ROOT=/host \
  nebulabroadcast/promexp
```

```yaml
services:
  promexp:
    image: nebulabroadcast/promexp
    restart: unless-stopped
    ports:
      - 9731:9731
    environment:
      PROMEXP_HOST_ROOT: /host
    volumes:
      - type: bind
        source: /
        target: /host
        read_only: true
        bind:
          propagation: rslave
```

  - `rslave` propagation is what makes storages mounted on the host *after* the
    container started appear in the container. Without it, only the mounts
    which existed at container start are visible.
  - Host networking is **not** required. `/proc/net` is namespaced, but
    `PROMEXP_HOST_ROOT` lets the network provider read the counters from the
    network namespace of the host init process
    (`/host/proc/1/net/dev`), so a container on a bridge network still reports
    the host interfaces. This needs the container to run as root, which is the
    default.
  - Memory, CPU and disk I/O metrics are host-wide even without any bind mount,
    because `/proc/meminfo`, `/proc/stat` and `/proc/diskstats` are not
    namespaced.
  - The `hostname` tag would otherwise be the container ID (and would change
    on every recreate), so it is read from `/host/etc/hostname` as well.
    `PROMEXP_HOSTNAME` still overrides it.

If bind mounting the whole root filesystem is not acceptable, mount just the
storages you care about *under the host root prefix*, keeping their host paths,
and whitelist them:

```yaml
    environment:
      PROMEXP_HOST_ROOT: /host
      PROMEXP_STORAGES: /mnt/media,/mnt/archive
    volumes:
      - /mnt/media:/host/mnt/media:ro
      - /mnt/archive:/host/mnt/archive:ro
```

In both cases the `mountpoint` tag is the host path (`/mnt/media`), so metrics
are identical whether promexp runs in a container or directly on the host.

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

Name                           | Type  | Unit    | Description
-------------------------------|-------|---------|-------------
`casparcg_connected`           | gauge | boolean | Returns `1` when CasparCG connection is estabilished
`casparcg_idle_seconds`        | gauge | seconds | Time elapsed since last OSC message. Shouldn't be much higher than 1/FPS
`casparcg_peak_volume_percent` | gauge | percent | Audio peak per channel since the last scrape, in percent of full scale
`casparcg_peak_dbfs`           | gauge | dBFS    | The same peak expressed in decibels relative to full scale

The peak metrics are tagged with the `channel` number and are reset by every
scrape, so they hold the loudest peak seen during the last scrape interval.

They may either help you determine whether the channel playback is stalled
(assuming audio should always play, check for silence) or to find out there is
an audio channel with a posibility of clipping audio (check for full scale).

`casparcg_peak_volume_percent` is a linear amplitude, so a nominal -20 dBFS
signal is reported as `10`. `casparcg_peak_dbfs` is the same value on a
logarithmic scale (`100% = 0 dBFS`, `50% = -6 dBFS`, `1% = -40 dBFS`), which is
easier to read on a graph and to set thresholds on. Digital silence is reported
as `-100`.


Upgrading from 1.x
------------------

Metric names have been aligned with the Prometheus naming conventions, so
dashboards and alerting rules need to be updated:

1.x | 2.0
----|----
`cpu_usage` | `cpu_usage_percent`
`memory_bytes_total` | `memory_total_bytes`
`memory_bytes_free` | `memory_available_bytes`
`memory_usage` | `memory_usage_percent` **(value changed, see below)**
`swap_bytes_total` | `swap_total_bytes`
`swap_bytes_free` | `swap_free_bytes`
`swap_usage` | `swap_usage_percent`
`disk_read_bytes` | `disk_read_bytes_total`
`disk_write_bytes` | `disk_write_bytes_total`
`storage_bytes_total` | `storage_total_bytes`
`storage_bytes_free` | `storage_free_bytes`
`storage_usage` | `storage_usage_percent`
`gpu_usage` | `gpu_usage_percent`
`gpu_memory` | `gpu_memory_usage_percent`
`gpu_encoder` | `gpu_encoder_usage_percent`
`gpu_decoder` | `gpu_decoder_usage_percent`
`gpu_fan_speed` | `gpu_fan_speed_percent`
`gpu_temperature` | `gpu_temperature_celsius`
`gpu_power_draw` | `gpu_power_watts`
`casparcg_peak_volume` | `casparcg_peak_volume_percent`
`casparcg_dropped_total` | removed, it always reported `0`

`uptime_seconds`, `casparcg_connected`, `casparcg_idle_seconds`,
`network_sent_bytes_total` and `network_recv_bytes_total` are unchanged.

Two changes are not just renames:

  - **`memory_usage_percent` reports lower values than `memory_usage` did.**
    1.x counted reclaimable page cache as used memory. See
    [a note on memory usage](#a-note-on-memory-usage).
  - **`memory_free_bytes` is not the new name of `memory_bytes_free`.** The old
    metric held `MemAvailable` and is now `memory_available_bytes`;
    `memory_free_bytes` is `MemFree`, which is a different (much lower) number.

New in 2.0: `memory_free_bytes`, `memory_used_bytes`, `memory_cached_bytes`,
`memory_shared_bytes`, `memory_slab_bytes`, `memory_arc_bytes`,
`storage_used_bytes` and `casparcg_peak_dbfs`.


Acknowledgements
----------------

### psutil

As a system metrics source, [psutil](https://github.com/giampaolo/psutil) module by giampaolo is used.

### python-osc

CasparCG provider uses public domain [python-osc](https://github.com/attwad/python-osc) module by attwad.
