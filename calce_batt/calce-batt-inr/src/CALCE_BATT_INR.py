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

    if not os.path.isfile(input_path):
        logging.error("Input file not found: %s", input_path)
        sys.exit(2)

    # Read file (try CSV then Excel)
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