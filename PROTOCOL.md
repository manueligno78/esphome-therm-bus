# Bosch Therm 5600 O — remote bus protocol (reverse engineered)

## Physical layer
- 2 wires, bus idles at ~11.8 V and also powers the remote.
- Async serial, **4800 baud 8N1**, idle high (logic 0 = bus pulled low).
- The heater pulls the bus to ~0 V, the remote to ~2.3 V: the low level tells who is talking.

## Frame
```
[hdr] [len] [payload ...] [chk]
hdr  F5 = heater -> remote, FA = remote -> heater
len  bytes after hdr, len and chk included
chk  (len + payload + chk) mod 256 == 0
```

## Timing
- Heater sends a 34-byte frame every ~185 ms; byte 2 cycles 21, 20, 21, 22, 21, 23, ...
- The remote answers (11 bytes) after every frame with byte 2 = 21.

## Heater -> remote (F5, 34 bytes)
| idx | idle | meaning |
|----:|------|---------|
| 2 | 20..23 | page / sequence |
| 3 | 07 | 01 for ~1 s after a remote command (ack?), else 07 |
| 4 | 01 | power: 01 on, 00 off |
| 7 | 20 | **status flags**: 0x20 appliance on, 0x01 water flowing, 0x02 fan running, 0x04 flame |
| 11 | 2C | **setpoint °C** (44) |
| 12 | 14 | **outlet water °C** (rises to 45-47 while burning) |
| 13 | 12 | **inlet water °C** (drops to 16 while water flows) |
| 14 | 14 | °C, slow (casing air / ambient?) |
| 15 | FF | ? |
| 16 | 00 | **flow l/min** (6-7 one tap fully open, 10-13 shower); consistent with b27 within 5 % |
| 17 | 00 | fan speed (?): up to 4A, post-purge ~20 s after flame off, then ramps to 0 |
| 18 | 40 | ? |
| 19 | 00 | **burner power, % of nominal**: heat to water ≈ b19 × 0.27 kW (checked at 6 l/min, ΔT 30 K); gas in = b19 × 0.30 kW, **verified on the gas meter** (10 min shower at ~70 %: meter 0.383 m³, estimate 0.383 m³). Already non-zero during ignition, before the flame flag |
| 27 | 00 | **litres drawn in this tap opening**, reset when the tap closes (shower: 105 L vs ∫b16 ≈ 110 L) |
| 31 | 24 | min setpoint 36 °C |
| 32 | 3C | max setpoint 60 °C |

Hot-water sequence (capture of one tap opening): flags 20 → 21 (flow) → 23 (fan, ignition)
→ 27 (flame, 6 s later) → 26 (tap closed) → 22 (flame off, fan post-purge) → 20 (~20 s later).

## Remote -> heater (FA, 11 bytes)
| idx | idle | meaning |
|----:|------|---------|
| 2 | 08 | constant (device id?) |
| 3 | 00 | command: 00 none, 18 set setpoint, 08 power |
| 4 | FF | arg: 00 with setpoint, 00 off / 01 on with power |
| 5 | FF | new setpoint °C (with cmd 18) |
| 8 | 04 | 04 idle, FF while sending a command |
| 9 | 55 | 55 on, 00 off |

Examples (from captures):
```
idle               FA 0A 08 00 FF FF FF FF 04 55 99
setpoint 45 °C     FA 0A 08 18 00 2D FF FF FF 55 57
setpoint 44 °C     FA 0A 08 18 00 2C FF FF FF 55 58
power off          FA 0A 08 08 00 FF FF FF FF 00 EA
power on           FA 0A 08 08 01 FF FF FF FF 55 94
idle while off     FA 0A 08 00 FF FF FF FF 04 00 EE
```
