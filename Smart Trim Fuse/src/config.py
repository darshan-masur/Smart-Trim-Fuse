"""Paths and shared constants. Every value here matches the Colab notebooks (00-05)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODELS = ROOT / "models"
SEED = 42  # same seed as the notebooks, so the wafer splits are identical

PCM = ["pcm_vth_n_mV", "pcm_vth_p_mV", "pcm_rs_ohm_sq", "pcm_tox_A", "pcm_mobility_rel"]
POS = ["x_mm", "y_mm", "radius_mm"]

# the 9 datasets: short name -> (file, chip, what it is, method used, page)
DATASETS = {
    "mcu": ("mcu_trim_fuse.csv", "MCU", "Bandgap, oscillator and LDO trims, drift, fuse maps", "ML model", "MCU"),
    "schema": ("mcu_fuse_schema.csv", "MCU", "Bit layout of the 64-bit fuse word", "Reference table", "MCU"),
    "audit": ("mcu_fuse_map_audit.csv", "MCU", "Fuse words, 25 % with injected errors", "Rules", "MCU"),
    "pmic": ("pmic_trim_otp.csv", "PMIC", "Reference + 4 rail trims, thresholds, current sense", "ML model", "PMIC"),
    "otp_req": ("pmic_otp_config_requests.csv", "PMIC", "Customer OTP configuration requests", "Rules", "PMIC"),
    "sensor": ("sensor_calibration.csv", "Sensor", "Accelerometer calibration at -40 / 25 / 85 °C", "ML model",
               "Sensor"),
    "soc": ("soc_binning_harvesting.csv", "SoC", "Per-core speed, defects, voltage bin, product", "ML + optimiser",
            "SoC"),
    "sku": ("soc_sku_demand.csv", "SoC", "Product prices and weekly demand", "Optimiser input", "SoC"),
    "repair": ("memory_repair_bitmaps.csv", "SoC", "Cache fail bitmaps, greedy vs exact repair", "Optimisation",
               "SoC"),
}
