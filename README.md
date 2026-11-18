# esphome-tcl-heatpump

An ESPHome package that decodes the full status data from TCL-built heat pumps
(Rheem, TCL and rebadges) and exposes it to Home Assistant. It sits alongside the
[tclac](https://github.com/sorz2122/tclac) climate package: tclac keeps controlling the
unit, and this package listens to the frames the unit already sends.

Built for a Rheem RC2IV12HP3BA with an SLWF-01Pro on CN16 (ESP8266). The status frame
layout matches the TCL TAC-12CHSD. Other TCL units vary slightly (some 9k units report
compressor Hz at byte 39), so check the values on yours.

## What you get

- **Room temperature at 0.1 °C** from the unit's own sensor (tclac rounds it)
- **Energy (kWh)** from the unit's internal counter, plus derived **power (W)**
- **Compressor frequency**, outdoor, outdoor-coil and discharge temperatures, fan speeds
- **Indoor coil temperature A/B**: byte 30, correctly split on its multiplex flag and rescaled
- **Supply voltage** and a **compressor load index**
- **Error codes** (stock TCL numbering), a **fault** flag and **filter blocked**
- **Target temperature** as the unit reports it, including the half-degree bit
- **Heat pump link** connectivity sensor
- Raw **status frame** and **unknown bytes** text sensors (off by default) for further decoding

Full list with entity IDs: [docs/entities.md](docs/entities.md). Byte map, formulas and
confidence of each field: [docs/byte-map.md](docs/byte-map.md).

## Install

1. In your device YAML, add the package next to tclac:

   ```yaml
   packages:
     remote_package:
       url: https://github.com/sorz2122/tclac.git
       ref: master
       files: [packages/core.yaml]
     tcl_decoder:
       url: https://github.com/Bencatkinson/esphome-tcl-heatpump
       ref: main
       files: [packages/tcl-decoder.yaml]
   ```

2. If you had a hand-written `uart: debug:` decoder with its own `sensor:` and
   `binary_sensor:` template entities, remove them. The package defines the same
   entity names (except the old "Indoor coil temperature (estimated)") so history carries over.
3. Flash. In Home Assistant, delete the old "Indoor coil temperature (estimated)" entity.

A full example (secrets in `secrets.yaml`) is in [examples/officeheatpump.yaml](examples/officeheatpump.yaml).

### Options

Override in your own `substitutions:`.

| Substitution | Default | Meaning |
|---|---|---|
| `tcl_energy_interval_s` | `30` | Seconds between energy queries. `0` turns the query off (no writes to the UART at all) |
| `tcl_energy_query` | stock module frame | Use `0xBB, 0x00, 0x01, 0x0A, 0x03, 0x05, 0x00, 0x00, 0xB6` if your unit ignores the default |
| `tcl_voltage_wrap_below` | `120` | Voltage bytes below this get 256 added |

## Half-degree setpoints

Stock tclac only sends whole degrees. Add the second package, after tclac's, to get 0.5 °C
steps:

```yaml
packages:
  remote_package: ...            # tclac core.yaml, unchanged
  tcl_decoder: ...               # as above
  tclac_half_degree:
    url: https://github.com/Bencatkinson/esphome-tcl-heatpump
    ref: main
    files: [packages/tclac-half-degree.yaml]
```

It replaces tclac's climate component with a patched copy (3 small changes, see
[docs/byte-map.md](docs/byte-map.md#setpoint-resolution)). After flashing, set 21.5 °C and
check that **Target temperature (unit)** reads 21.5.

## Known gaps

- Outdoor, outdoor-coil and discharge temperatures use `b - 20`, calibrated at one point on a
  different unit. Check them against a thermometer.
- Which of Indoor coil temperature A/B is the coil and which the outlet air isn't confirmed yet.
- The energy counter's unit hasn't been checked against a meter.
- Byte 31 still has no known meaning.

## Tests

`python3 tests/host_test.py` compiles the decoder lambda on the host and feeds it
synthetic frames (split frames, bad checksums, voltage wrap, byte 30 multiplexing, error
masks, BCD energy, power). `esphome compile tests/ci-device.yaml` builds the firmware;
CI runs both.

## Credits

Frame parser and energy query after [E-t0m/esphome-local-ac-control](https://github.com/E-t0m/esphome-local-ac-control)
(MIT). Field map and error codes from [kralonur/tcl-ac-original-module-esphome](https://github.com/kralonur/tcl-ac-original-module-esphome),
which recovered them from the stock TCL Wi-Fi module firmware. Protocol notes from
[adaasch/AC-hack](https://github.com/adaasch/AC-hack).
