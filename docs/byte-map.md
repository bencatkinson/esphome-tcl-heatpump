# TCL status frame byte map

Frame offsets (`frame[0] = 0xBB`). Status reply: `BB 01 00 04 37 <55 payload bytes> <xor>`,
61 bytes. Payload index = frame index - 5 (kralonur's `P[]` numbering).

Confidence: **known** = confirmed by several projects; **stock** = from the stock TCL Wi-Fi
module firmware (kralonur); **inferred** = label guessed from live data; **tentative** = scale
guessed.

| Frame | Field | Decode | Confidence | Entity |
|---|---|---|---|---|
| 7 | Power b4, mode b0-3, eco b6, turbo b7 | | known | (tclac) |
| 8 | Setpoint low nibble + 16, fan high nibble | | known | Target temperature (unit) |
| 9 | Half-degree setpoint b1, timers b6/b7 | | known | Target temperature (unit) |
| 16 | Error bits → codes 56,57,54,55,52,53,1 | | stock | Error codes |
| 17-18 | Room temp, 10 bit | `(((b17<<2) \| ((b18>>2)&3)) - 200) / 10` | stock | Room temperature (unit) |
| 18 b5 | Selects which reading byte 30 carries | | observed | |
| 30 | Indoor coil / outlet temp (muxed) | `0.4·b - 20` | partial | Indoor coil temperature A / B |
| 31 | Unknown, changes | | | Unknown status bytes |
| 32 b7 | 8 °C frost protection | | stock | 8 °C frost protection |
| 33 b7 | Silent | | stock | Silent mode |
| 34 | Indoor fan | raw | inferred | Indoor fan speed (raw) |
| 35 | Outdoor air temp | `b - 20` | provisional (one-point) | Outdoor temperature |
| 36 | Outdoor coil temp | `b - 20` | tentative | Outdoor coil temperature |
| 37 | Compressor discharge temp | `b - 20` | tentative | Compressor discharge temperature |
| 38 | Compressor frequency | Hz | inferred, matches this unit | Compressor frequency |
| 39 | Outdoor fan | raw | tentative | Outdoor fan speed (raw) |
| 41-44 | Error bits → codes 1-26, 78 | | stock | Error codes |
| 45 | Supply voltage | V, +256 if < 120 | inferred | Supply voltage |
| 46 | Current / load index | raw | inferred | Compressor load index (raw) |
| 50 | Light sense b0, filter blocked b1, filter alarm b2, self-clean b3, soft wind b5 | | stock | Filter blocked, Filter alarm enabled |
| 51, 52 | Vertical / horizontal vane | | known | (tclac) |
| 53-54 | Target-electric limit, BCD | | stock | |
| 55 | Constant-temperature setting | | stock | |
| 56-59 | Error bits → codes 27-51, 64; b7 masks the byte's group | | stock | Error codes |

## Energy reply (command 0x0A)

Query (stock module): `BB 00 01 0A 03 02 00 05 B4`, sent 180 ms after a status reply.
Reply is valid when frame 7 bit 3 is set. Counter in packed BCD:

```
kWh = bcd(f11)·10000 + bcd(f10)·100 + bcd(f9) + bcd(f8)/100 + bcd(f21)/10^4 + bcd(f20)/10^6
```

It counts the outdoor unit only. The physical unit hasn't been checked against a meter
yet, so compare it with a plug-in or clamp meter before trusting absolute numbers.

## Setpoint resolution

The unit reports and (on the TAC-12CHSD, per kralonur) accepts **0.5 °C setpoints**: the
outgoing control frame carries a half-degree flag in **frame 11 bit 1** (Celsius; bit 2 when
the Fahrenheit flag, frame 12 bit 7, is set). Stock tclac never sets it and truncates the
setpoint to whole degrees.

`packages/tclac-half-degree.yaml` swaps in a patched tclac (branch `half-degree` of
Bencatkinson/tclac) that sets `dataTX[11] |= 0x02` for a .5 setpoint, reads frame 9 bit 1
back into `target_temperature`, and sets the climate's step to 0.5 °C.

To confirm on a unit: set 21.5 °C and check that **Target temperature (unit)** reads 21.5
(and the unit's display shows .5 if it has one). If it reads 21.0, the unit ignores the
flag and you should remove the package.
