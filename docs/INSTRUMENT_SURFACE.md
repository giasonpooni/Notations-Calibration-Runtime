# Portable Calibration instrument surface

Calibration is the second Notation Systems repository to implement the portable
instrument contract first exercised by ClockSync.

The machine-readable files deliberately describe the existing MCUR mathematics;
they do not move that mathematics into NET.

## Identity

```text
semantic capability: measure.calibrate.v1
runtime operation:   mcur.affine-first-order.v1
provider:            org.notationsystems.calibration
execution:           python / scientific / headless / cpu
```

The portable request/result schemas are integration boundaries. The Python typed
API remains authoritative for the implementation.

## Verification specimen

`scripts/build_instrument_surface.py` reruns the canonical synthetic specimen:

```text
raw                 = 300
indicated x         = 3 kPa
gain g              = 2
offset b            = 1 kPa
corrected y         = 7 kPa
propagated variance = 22.35 kPa²
J                    = [2, 3, 1]
```

The full joint covariance over `[x,g,b]` includes nonzero cross terms. The
generated report binds the specimen and test summary to the source revision.

A passing report does **not** establish a physical calibration, certified
traceability or validity of an externally supplied calibration profile.

## Authority

The portable contract is descriptive/evidentiary only. NET may advertise it as an
unbound provider after verifying the report, but an explicit trusted adapter
binding is still required before execution.

The instrument itself cannot admit state or authorize hardware action.
