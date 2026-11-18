# Entity contract

These are the entities `packages/tcl-decoder.yaml` creates. The Home Assistant
integration in this project finds them by name, so the names are stable. Rename one
only together with the integration.

Entity IDs below assume the device's `friendly_name` is **Office Heat Pump**
(Home Assistant prefixes every entity with the device name). For another device,
swap `office_heat_pump` for your device's slug.

## Used for control

| Name | Entity ID | Unit | Notes |
|---|---|---|---|
| Room temperature (unit) | `sensor.office_heat_pump_room_temperature_unit` | °C, 0.1 | The unit's return-air sensor, full resolution (tclac's climate entity rounds it) |
| Target temperature (unit) | `sensor.office_heat_pump_target_temperature_unit` | °C, 0.5 | Setpoint the unit reports back, including the half-degree bit |
| Outdoor temperature | `sensor.office_heat_pump_outdoor_temperature` | °C, 1 | Provisional scale (`b - 20`) |
| Compressor frequency | `sensor.office_heat_pump_compressor_frequency` | Hz | 0 when the compressor is stopped |
| Compressor running | `binary_sensor.office_heat_pump_compressor_running` | on/off | Frequency > 0 |
| Energy | `sensor.office_heat_pump_energy` | kWh | Unit's own counter (outdoor unit), `total_increasing`, ready for the Energy dashboard |
| Power | `sensor.office_heat_pump_power` | W | Derived from Energy counter steps; coarse (the counter steps in 0.01 kWh) and decays between steps |
| Heat pump link | `binary_sensor.office_heat_pump_heat_pump_link` | connectivity | On while valid status frames arrive (within 30 s). Treat every other value as stale when off |

The climate entity itself stays tclac's: `climate.office_heat_pump_officeheatpump_climate`
(ESPHome id `officeheatpumpclimate`). With `packages/tclac-half-degree.yaml` its
`target_temp_step` is 0.5 and it accepts .5 setpoints; without it, whole degrees only.
Read Target temperature (unit) to see what the unit actually accepted.

## Diagnostics

| Name | Entity ID | Unit | Notes |
|---|---|---|---|
| Indoor coil temperature A | `sensor.office_heat_pump_indoor_coil_temperature_a` | °C, 0.4 | Byte 30 when byte 18 bit 5 is clear |
| Indoor coil temperature B | `sensor.office_heat_pump_indoor_coil_temperature_b` | °C, 0.4 | Byte 30 when byte 18 bit 5 is set. Which of A/B is the coil and which the outlet air is still to be confirmed on this unit |
| Outdoor coil temperature | `sensor.office_heat_pump_outdoor_coil_temperature` | °C | Tentative scale (`b - 20`) |
| Compressor discharge temperature | `sensor.office_heat_pump_compressor_discharge_temperature` | °C | Tentative scale (`b - 20`) |
| Indoor fan speed (raw) | `sensor.office_heat_pump_indoor_fan_speed_raw` | raw | |
| Outdoor fan speed (raw) | `sensor.office_heat_pump_outdoor_fan_speed_raw` | raw | |
| Supply voltage | `sensor.office_heat_pump_supply_voltage` | V | Inferred label; the byte wraps past 255, corrected below 120 |
| Compressor load index (raw) | `sensor.office_heat_pump_compressor_load_index_raw` | raw | Inferred to track current draw; unscaled |
| Error codes | `sensor.office_heat_pump_error_codes` | text | Stock TCL error numbers, comma-separated, or `none` |
| Fault | `binary_sensor.office_heat_pump_fault` | problem | On when any error code is set |
| Filter blocked | `binary_sensor.office_heat_pump_filter_blocked` | problem | |
| Filter alarm enabled | `binary_sensor.office_heat_pump_filter_alarm_enabled` | on/off | Whether the filter reminder feature is on |
| 8 °C frost protection | `binary_sensor.office_heat_pump_8_c_frost_protection` | on/off | |
| Silent mode | `binary_sensor.office_heat_pump_silent_mode` | on/off | |

Disabled by default (enable while decoding): **Status frame (raw)**, **Unknown status bytes**
(position:value of non-zero bytes with no known meaning), **Energy reply byte 22 (raw)**.

## Changes from the original hand-written config

All names from the original config are kept except **Indoor coil temperature
(estimated)**, which mixed two readings with the wrong scale. It is replaced by
Indoor coil temperature A and B. Delete the old entity in Home Assistant after updating.
