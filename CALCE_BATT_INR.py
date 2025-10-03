"""CALCE_BATT_INR.py

Robust preprocessing helper for CALCE battery cycling logs.

Usage (example):
    python CALCE_BATT_INR.py --input CALCE_battery_log.csv --output CALCE_Preprocessed.csv

This script attempts to be flexible with input column names and types, and
protects against common runtime errors when a file doesn't contain an
expected column.
"""

import argparse
import os
import sys
import logging
from typing import Optional
import zipfile
import tarfile
import tempfile
from pathlib import Path
import glob
import shutil
import subprocess

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def infer_time_column(df: pd.DataFrame) -> Optional[str]:
    # Common time-like column names
    candidates = [
        'Time', 'time', 'Timestamp', 'DateTime', 'datetime', 'Date', 'date',
        'timestamp', 'Seconds', 'seconds'
    ]
    for c in candidates:
        if c in df.columns:
            return c
    # fallback: try to detect datetime dtype
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
        # strings that parse to datetimes
        if df[c].dtype == object:
            sample = df[c].dropna().astype(str).head(5)
            try:
                pd.to_datetime(sample)
                return c
            except Exception:
                continue
    return None


def parse_args():
    p = argparse.ArgumentParser(description="Preprocess CALCE battery logs")
    p.add_argument('--input', '-i', required=True, help='Input CSV/Excel file path')
    p.add_argument('--output', '-o', default='CALCE_Preprocessed.csv', help='Output CSV path')
    p.add_argument('--no-plot', action='store_true', help='Skip plotting')
    return p.parse_args()


def main():
    args = parse_args()
    input_path = args.input
    output_path = args.output

    # allow archives (.zip, .tar, .tar.gz, .tgz, .tar.bz2) containing a CSV/XLSX.
    if not os.path.exists(input_path):
        logging.error("Input path not found: %s", input_path)
        sys.exit(2)

    def _find_tabular_in_dir(d: Path) -> Optional[Path]:
        for pat in ("**/*.csv", "**/*.xlsx", "**/*.xls"):
            found = list(d.glob(pat))
            if found:
                return found[0]
        return None

    # if archive, extract to tempdir and pick first tabular file
    lower = input_path.lower()
    is_archive = lower.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2"))
    if is_archive:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_p = Path(tmpdir)
            try:
                if lower.endswith(".zip"):
                    with zipfile.ZipFile(input_path, "r") as z:
                        z.extractall(tmpdir)
                else:
                    with tarfile.open(input_path, "r:*") as t:
                        t.extractall(tmpdir)
            except Exception as e:
                logging.error("Failed to extract archive %s: %s", input_path, e)
                sys.exit(3)

            candidate = _find_tabular_in_dir(tmpdir_p)
            if candidate is None:
                logging.error("No CSV/XLSX file found inside archive: %s", input_path)
                sys.exit(4)
            input_path = str(candidate)

            # now read the extracted file (inside same tempdir context)
            try:
                df = pd.read_csv(input_path)
                logging.info("Loaded CSV from archive: %s", input_path)
            except Exception as e_csv:
                try:
                    df = pd.read_excel(input_path)
                    logging.info("Loaded Excel from archive: %s", input_path)
                except Exception as e_xlsx:
                    logging.error("Failed to read extracted file as CSV or Excel. CSV error: %s; Excel error: %s", e_csv, e_xlsx)
                    raise
            # rest of processing continues while tempdir exists
            # (TemporaryDirectory will be cleaned up after main exits or the with-block ends)
    else:
        # Read file (try CSV then Excel) for non-archive input
        try:
            df = pd.read_csv(input_path)
            logging.info("Loaded CSV: %s", input_path)
        except Exception as e_csv:
            try:
                df = pd.read_excel(input_path)
                logging.info("Loaded Excel: %s", input_path)
            except Exception as e_xlsx:
                logging.error("Failed to read input as CSV or Excel. CSV error: %s; Excel error: %s", e_csv, e_xlsx)
                raise

    logging.info("Columns: %s", list(df.columns))
    logging.info("Preview:\n%s", df.head().to_string())

    # Standardize known names
    rename_map = {
        'Voltage(V)': 'Voltage',
        'Current(A)': 'Current',
        'Capacity(Ah)': 'Capacity',
        'Temperature(°C)': 'Temperature',
        'Cycle_Index': 'Cycle',
    }
    df.rename(columns={c: rename_map.get(c, c) for c in df.columns}, inplace=True)

    # Identify time column and convert to seconds from start
    time_col = infer_time_column(df)
    if time_col is None:
        logging.warning("No time-like column found; creating a simple index-based Time column")
        df = df.reset_index(drop=True)
        df['Time'] = np.arange(len(df)).astype(float)
    else:
        if pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df['Time'] = (df[time_col] - df[time_col].iloc[0]).dt.total_seconds()
        else:
            # try to parse strings to datetime
            if df[time_col].dtype == object:
                try:
                    parsed = pd.to_datetime(df[time_col])
                    df['Time'] = (parsed - parsed.iloc[0]).dt.total_seconds()
                except Exception:
                    # if not datetime, try numeric
                    try:
                        df['Time'] = pd.to_numeric(df[time_col], errors='coerce')
                        if df['Time'].isna().any():
                            logging.warning("Some Time values could not be parsed to numeric; filling forward")
                            df['Time'].fillna(method='ffill', inplace=True)
                    except Exception:
                        logging.warning("Could not parse time column '%s'; creating index-based Time instead", time_col)
                        df = df.reset_index(drop=True)
                        df['Time'] = np.arange(len(df)).astype(float)
            else:
                # numeric already
                df['Time'] = pd.to_numeric(df[time_col], errors='coerce')
                if df['Time'].isna().any():
                    logging.warning("Time column contains NaNs after numeric coercion; filling by forward-fill")
                    df['Time'].fillna(method='ffill', inplace=True)

    # Clean data: drop rows missing critical measures
    critical_cols = []
    if 'Voltage' in df.columns:
        critical_cols.append('Voltage')
    if 'Current' in df.columns:
        critical_cols.append('Current')
    if critical_cols:
        before = len(df)
        df = df.dropna(subset=critical_cols)
        logging.info("Dropped %d rows missing %s", before - len(df), critical_cols)

    # Remove obviously invalid rows
    if 'Voltage' in df.columns:
        df = df[df['Voltage'] > 0]

    # Normalize units if necessary (heuristic)
    if 'Current' in df.columns:
        try:
            current_max = df['Current'].abs().max()
            if pd.notna(current_max) and current_max > 1000:
                logging.info("Current values appear large (max=%s). Assuming mA and converting to A.", current_max)
                df['Current'] = df['Current'] / 1000.0
        except Exception:
            logging.debug("Could not inspect/convert Current units")

    # Feature engineering
    # Compute Power using available Voltage/Current (if both exist)
    if 'Voltage' in df.columns and 'Current' in df.columns:
        df['Power_W'] = df['Voltage'] * df['Current']
    else:
        df['Power_W'] = np.nan

    # Compute delta time (seconds) and Energy in Wh
    df = df.sort_values('Time').reset_index(drop=True)
    dt = df['Time'].diff().fillna(0).astype(float)
    df['Energy_Wh'] = (df['Power_W'] * dt).cumsum() / 3600.0

    # Derive dV/dt where possible
    if 'Voltage' in df.columns:
        dv = df['Voltage'].diff()
        with np.errstate(invalid='ignore', divide='ignore'):
            df['dV_dt'] = dv / dt.replace({0: np.nan})
        df['dV_dt'] = df['dV_dt'].fillna(0)

    # Normalize selected features for ML models (only existing columns)
    cols_to_norm = [c for c in ['Voltage', 'Current', 'Temperature', 'Capacity'] if c in df.columns]
    if cols_to_norm:
        try:
            scaler = MinMaxScaler()
            df[cols_to_norm] = scaler.fit_transform(df[cols_to_norm])
            logging.info("Normalized columns: %s", cols_to_norm)
        except Exception as e:
            logging.warning("Failed to scale columns %s: %s", cols_to_norm, e)

    # Save preprocessed dataset
    try:
        df.to_csv(output_path, index=False)
        logging.info("Preprocessed dataset saved to %s", output_path)
    except Exception as e:
        logging.error("Failed to save output CSV: %s", e)

    # Simple visualization (raw Power and Voltage/Current when available)
    if not args.no_plot:
        plt.figure(figsize=(10, 5))
        plotted = False
        if 'Time' in df.columns and 'Voltage' in df.columns:
            plt.plot(df['Time'], df['Voltage'], label='Voltage')
            plotted = True
        if 'Time' in df.columns and 'Current' in df.columns:
            plt.plot(df['Time'], df['Current'], label='Current')
            plotted = True
        if not plotted and 'Time' in df.columns and 'Power_W' in df.columns:
            plt.plot(df['Time'], df['Power_W'], label='Power (W)')
            plotted = True

        if plotted:
            plt.xlabel('Time (s)')
            plt.ylabel('Value')
            plt.title('CALCE Battery Data')
            plt.legend()
            plt.tight_layout()
            plt.show()


if __name__ == '__main__':
    main()

# python
# test_CALCE_BATT_INR.py
# Detailed plan above; now the tests.

import sys
import csv
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

# Absolute import of the function to test (module lives alongside this test file)
from CALCE_BATT_INR import main


def _run_main_with_args(infile: Path, outfile: Path, monkeypatch):
    argv = ["CALCE_BATT_INR.py", "--input", str(infile), "--output", str(outfile), "--no-plot"]
    monkeypatch.setattr(sys, "argv", argv)
    # call main (it will read argv)
    main()


def test_main_creates_output_and_features(tmp_path, monkeypatch):
    # Create simple CSV with Time, Voltage, Current
    in_path = tmp_path / "input1.csv"
    out_path = tmp_path / "out1.csv"
    df = pd.DataFrame({
        "Time": [0, 1, 2],
        "Voltage": [3.0, 3.1, 3.2],
        "Current": [0.5, 0.6, 0.7],
    })
    df.to_csv(in_path, index=False)

    _run_main_with_args(in_path, out_path, monkeypatch)

    assert out_path.exists(), "Output file was not created"
    df_out = pd.read_csv(out_path)
    # expected engineered columns
    assert "Power_W" in df_out.columns
    assert "Energy_Wh" in df_out.columns
    assert "dV_dt" in df_out.columns


def test_normalization_applied_to_voltage_and_current(tmp_path, monkeypatch):
    # Create CSV where Voltage and Current have clear ranges
    in_path = tmp_path / "input2.csv"
    out_path = tmp_path / "out2.csv"
    df = pd.DataFrame({
        "Time": [0, 1, 2, 3],
        "Voltage": [1.0, 2.0, 3.0, 4.0],
        "Current": [10.0, 20.0, 30.0, 40.0],
    })
    df.to_csv(in_path, index=False)

    _run_main_with_args(in_path, out_path, monkeypatch)

    df_out = pd.read_csv(out_path)
    # After MinMaxScaler, Voltage and Current should be in [0,1]
    assert "Voltage" in df_out.columns and "Current" in df_out.columns
    v = df_out["Voltage"].astype(float)
    c = df_out["Current"].astype(float)
    assert pytest.approx(0.0, rel=1e-6) <= v.min() <= pytest.approx(0.0, rel=1e-3)
    assert pytest.approx(1.0, rel=1e-6) >= v.max() >= pytest.approx(1.0, rel=1e-3)
    assert pytest.approx(0.0, rel=1e-6) <= c.min() <= pytest.approx(0.0, rel=1e-3)
    assert pytest.approx(1.0, rel=1e-6) >= c.max() >= pytest.approx(1.0, rel=1e-3)


def test_missing_time_column_creates_index_time(tmp_path, monkeypatch):
    # CSV without any time-like column; main should create Time as index-based 0..n-1
    in_path = tmp_path / "input3.csv"
    out_path = tmp_path / "out3.csv"
    df = pd.DataFrame({
        "Voltage": [3.0, 3.1, 3.2, 3.3],
        "Current": [0.1, 0.2, 0.1, 0.3],
    })
    df.to_csv(in_path, index=False)

    _run_main_with_args(in_path, out_path, monkeypatch)

    df_out = pd.read_csv(out_path)
    assert "Time" in df_out.columns
    # Time should be sequential starting at 0
    time_vals = df_out["Time"].astype(float).to_list()
    assert time_vals == [0.0, 1.0, 2.0, 3.0]


def test_run_with_real_excel(tmp_path):
    # locate repository root from this test file:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "CALCE_BATT_INR.py"
    assert script.exists(), f"Script not found at {script}"

    input_xlsx = repo_root / "data" / "10_16_2015_Initial capacity_SP20-1.xlsx"
    assert input_xlsx.exists(), f"Test data not found at {input_xlsx}"

    out_csv = tmp_path / "preprocessed.csv"

    cmd = [
        sys.executable,
        str(script),
        "--input",
        str(input_xlsx),
        "--output",
        str(out_csv),
        "--no-plot",
    ]

    # run the script; fail the test with captured output if it errors
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise AssertionError(f"Script failed:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")

    assert out_csv.exists(), "Output CSV was not created"

    df = pd.read_csv(out_csv)
    # basic sanity checks: expected engineered columns
    for col in ("Power_W", "Energy_Wh", "dV_dt", "Time"):
        assert col in df.columns, f"Missing column {col} in output"
