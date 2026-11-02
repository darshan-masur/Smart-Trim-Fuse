# Safety, standards and limitations

**Smart Trim & Fuse is a research prototype built on synthetic data.** It is not a production tool. It has never
run on a tester, programmed a fuse, or seen data from a real chip.

## What this project does not claim

- **Not real-world results.** Every number is a simulation on synthetic data (see
  [`RESULTS_SOURCE_OF_TRUTH.md`](RESULTS_SOURCE_OF_TRUTH.md)). No real test-time saving, yield gain, revenue gain or
  quality level is claimed.
- **Not production-ready.** The app reads CSV files and proposes trim codes, products and fuse-word verdicts. It
  does not drive a tester, and it must not be used to program real fuses or OTP memory.
- **No functional-safety compliance.** The work was not developed under ISO 26262, IEC 61508, AEC-Q100 or any
  customer quality process, and it makes no claim of compliance. MCU-C is described as "automotive" only because the
  synthetic dataset gives it that label.
- **No guarantee that a rule check is complete.** The fuse and OTP rules catch the error types the data generator
  injects (6 fuse error types, 5 OTP rule types). Real errors may be of other kinds.
- **"0 over-graded" does not mean zero risk.** 0 events in 1,540 held-out SoC chips gives a 95% upper bound of about
  0.19%. A real process would need far more data, and a target agreed with quality engineering.

## How the prototype limits harm

| Control | Where | Status |
|---|---|---|
| Wafer-grouped split; no wafer in both training and test | `src/common.py`, `tests/test_wafer_split.py` | Done |
| Predict, then verify: every AI trim code is checked once. If the check fails, the chip falls back to the conventional search | try model in the notebooks and app | Simulated only |
| Rows with missing or impossible inputs are never predicted ("not predicted; conventional review required") | `src/batch.py clean` | Done |
| Fuse word **PASS** only if the word is exactly 64 bits, the schema covers all 64 bits exactly once, the die_id is unique and found in the sort records with the same product, and every rule passes, including the per-die trim fields and the TS_CAL1 temperature-sensor reading (all 64 bits are covered by a rule). Otherwise **REVIEW** or **BLOCK** | `src/mcu.py`, `src/batch.py run_fuse`, `tests/test_fuse_rules.py` | Done |
| Out-of-range inputs flagged and sent to the conventional method | notebook 06 | Simulated only |
| Sensor Tight grade keeps the full 3-temperature test; 5% monitoring sample | notebook 03 / 06 | Simulated only |
| SoC chips near a product boundary get the real speed test (80 MHz margin chosen on validation wafers) | notebook 06 | Simulated only |

## What would be needed before any production use

1. **Real data.** Train and validate on real sort and final-test data from several lots, wafers, testers and time
   periods. Re-derive every number in the source-of-truth table, and repeat for each new product version.
2. **Shadow mode.** Run beside the existing flow for a defined period without acting. Compare every proposed code,
   product and fuse verdict with what the conventional flow decided.
3. **Escape analysis.** Agree on acceptable escape rates (in DPPM) with quality engineering, and show them with
   statistical confidence on enough real units. Include final test, burn-in and field returns for the drift-aware
   MCU-C target.
4. **Fuse / OTP programming controls.**
   - Independent read-back and verify after programming.
   - Fuse maps generated and checked from a controlled, versioned schema.
   - Two-person or system sign-off on schema changes.
   - Hard interlocks in the tester program (not in this app).
   - Full traceability of die_id → word → programmed result.
5. **Functional-safety work, for automotive parts.** A hazard analysis and safety case under ISO 26262 (or the
   customer's process), tool qualification for any software that influences safety-relevant settings, and a
   documented change process.
6. **Software engineering.**
   - Version control and code review.
   - A controlled model registry: training data hash, version, approval.
   - Input validation at the tester interface.
   - Monitoring of fallback rates per wafer, with alarms (the notebook-06 alarm is only a sketch).
   - A rollback plan.
7. **Security.** Fuse words control debug lock and read-out protection. Real use would need access control, audit
   logs and protection of the schema and sort records against tampering.
