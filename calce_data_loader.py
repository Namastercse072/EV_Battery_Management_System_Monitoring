"""
CALCE (NASA) Battery Cycle Test Data Loader & Analysis
========================================================

This module loads and analyzes real NASA CALCE battery test data
for validating and tuning the RealisticBatterySimulator.

Features:
- Load CALCE CSV data
- Extract statistical parameters
- Validate simulator against real data
- Generate synthetic data based on CALCE patterns
- Hybrid mode: Mix real CALCE with simulated data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import json
from datetime import datetime


class CALCEDataLoader:
    """Load and analyze NASA CALCE battery test data"""
    
    def __init__(self, csv_path: str):
        """
        Initialize CALCE data loader
        
        Args:
            csv_path: Path to CALCE_Preprocessed.csv
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CALCE data file not found: {csv_path}")
        
        print(f"📂 Loading CALCE data from {self.csv_path.name}...")
        self.df = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(self.df)} data points")
        self.stats = None
        self.cycles = None
    
    def analyze_voltage_characteristics(self) -> Dict:
        """Extract voltage statistics from CALCE data"""
        
        # Single cell voltage analysis (CALCE is single cell at 0.5A)
        voltage_stats = {
            'cell_voltage_min': float(self.df['Voltage'].min()),
            'cell_voltage_max': float(self.df['Voltage'].max()),
            'cell_voltage_mean': float(self.df['Voltage'].mean()),
            'cell_voltage_std': float(self.df['Voltage'].std()),
            'cell_voltage_range': float(self.df['Voltage'].max() - self.df['Voltage'].min()),
        }
        
        # Scale to 96-cell pack (series configuration)
        pack_voltage_stats = {
            'pack_voltage_min': voltage_stats['cell_voltage_min'] * 96,
            'pack_voltage_max': voltage_stats['cell_voltage_max'] * 96,
            'pack_voltage_mean': voltage_stats['cell_voltage_mean'] * 96,
            'pack_voltage_std': voltage_stats['cell_voltage_std'] * 96,
        }
        
        return {
            **voltage_stats,
            **pack_voltage_stats,
            'measurement_count': len(self.df)
        }
    
    def analyze_current_characteristics(self) -> Dict:
        """Extract current statistics from CALCE data"""
        
        return {
            'current_mean': float(self.df['Current'].mean()),
            'current_std': float(self.df['Current'].std()),
            'current_min': float(self.df['Current'].min()),
            'current_max': float(self.df['Current'].max()),
            'constant_current_test': float(self.df['Current'].std()) < 0.01,  # Very low std = constant
        }
    
    def analyze_internal_resistance(self) -> Dict:
        """Extract internal resistance evolution"""
        
        # Filter out zero values (not measured)
        ir_data = self.df[self.df['Internal_Resistance(Ohm)'] > 0]['Internal_Resistance(Ohm)']
        
        if len(ir_data) == 0:
            return {
                'ir_available': False,
                'ir_mean': 0.0,
                'note': 'No internal resistance measurements in dataset'
            }
        
        return {
            'ir_available': True,
            'ir_mean': float(ir_data.mean()),
            'ir_std': float(ir_data.std()),
            'ir_min': float(ir_data.min()),
            'ir_max': float(ir_data.max()),
            'ir_measurements': len(ir_data),
            'ir_trend': 'increasing' if ir_data.iloc[-1] > ir_data.iloc[0] else 'stable'
        }
    
    def analyze_voltage_rate(self) -> Dict:
        """Analyze dV/dt (voltage rate of change)"""
        
        dv_dt = self.df['dV/dt(V/s)']
        dv_dt_filtered = dv_dt[dv_dt.abs() > 1e-10]  # Filter near-zero values
        
        return {
            'dv_dt_mean': float(dv_dt.mean()),
            'dv_dt_std': float(dv_dt.std()),
            'dv_dt_min': float(dv_dt.min()),
            'dv_dt_max': float(dv_dt.max()),
            'dv_dt_samples': len(dv_dt_filtered),
            'voltage_stability': 'very_stable' if dv_dt.std() < 1e-4 else 'stable'
        }
    
    def analyze_cycles(self) -> Dict:
        """Analyze cycle structure"""
        
        cycle_groups = self.df.groupby('Cycle').size()
        
        return {
            'total_cycles': int(self.df['Cycle'].max()),
            'points_per_cycle_mean': float(cycle_groups.mean()),
            'points_per_cycle_std': float(cycle_groups.std()),
            'points_per_cycle_min': int(cycle_groups.min()),
            'points_per_cycle_max': int(cycle_groups.max()),
            'test_duration_seconds': float(self.df['Test_Time(s)'].max()),
            'test_duration_hours': float(self.df['Test_Time(s)'].max() / 3600),
        }
    
    def get_full_statistics(self) -> Dict:
        """Get comprehensive statistics from CALCE data"""
        
        print("\n📊 Analyzing CALCE Dataset...")
        
        self.stats = {
            'timestamp': datetime.now().isoformat(),
            'source': 'NASA CALCE Battery Test Data',
            'file': str(self.csv_path),
            'total_points': len(self.df),
            'voltage': self.analyze_voltage_characteristics(),
            'current': self.analyze_current_characteristics(),
            'internal_resistance': self.analyze_internal_resistance(),
            'voltage_dynamics': self.analyze_voltage_rate(),
            'cycles': self.analyze_cycles(),
        }
        
        return self.stats
    
    def print_summary(self):
        """Print formatted statistics summary"""
        
        if self.stats is None:
            self.get_full_statistics()
        
        print("\n" + "="*70)
        print("CALCE BATTERY TEST DATA ANALYSIS SUMMARY")
        print("="*70)
        
        print("\n📈 VOLTAGE CHARACTERISTICS")
        print(f"  Single Cell: {self.stats['voltage']['cell_voltage_min']:.4f}V - {self.stats['voltage']['cell_voltage_max']:.4f}V")
        print(f"  Pack (96s):  {self.stats['voltage']['pack_voltage_min']:.1f}V - {self.stats['voltage']['pack_voltage_max']:.1f}V")
        print(f"  Mean Cell:   {self.stats['voltage']['cell_voltage_mean']:.4f}V ± {self.stats['voltage']['cell_voltage_std']:.6f}V")
        
        print("\n⚡ CURRENT CHARACTERISTICS")
        print(f"  Mean:   {self.stats['current']['current_mean']:.4f}A")
        print(f"  Range:  {self.stats['current']['current_min']:.4f}A - {self.stats['current']['current_max']:.4f}A")
        print(f"  Type:   {'Constant Current' if self.stats['current']['constant_current_test'] else 'Variable Current'}")
        
        print("\n🔌 INTERNAL RESISTANCE")
        if self.stats['internal_resistance']['ir_available']:
            print(f"  Mean:    {self.stats['internal_resistance']['ir_mean']:.6f}Ω")
            print(f"  Range:   {self.stats['internal_resistance']['ir_min']:.6f}Ω - {self.stats['internal_resistance']['ir_max']:.6f}Ω")
            print(f"  Trend:   {self.stats['internal_resistance']['ir_trend']}")
        else:
            print("  Not available in this test")
        
        print("\n📊 VOLTAGE DYNAMICS")
        print(f"  dV/dt Mean:    {self.stats['voltage_dynamics']['dv_dt_mean']:.2e}V/s")
        print(f"  dV/dt Std:     {self.stats['voltage_dynamics']['dv_dt_std']:.2e}V/s")
        print(f"  Stability:     {self.stats['voltage_dynamics']['voltage_stability']}")
        
        print("\n🔄 CYCLE INFORMATION")
        print(f"  Total Cycles:     {self.stats['cycles']['total_cycles']}")
        print(f"  Points per Cycle: {self.stats['cycles']['points_per_cycle_mean']:.0f} ± {self.stats['cycles']['points_per_cycle_std']:.0f}")
        print(f"  Test Duration:    {self.stats['cycles']['test_duration_hours']:.2f} hours")
        
        print("\n" + "="*70)
    
    def export_statistics(self, output_path: str = None) -> str:
        """Export statistics to JSON file"""
        
        if self.stats is None:
            self.get_full_statistics()
        
        if output_path is None:
            output_path = self.csv_path.parent / "calce_statistics.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        print(f"\n💾 Statistics exported to {output_path}")
        return str(output_path)
    
    def get_sample_cycles(self, num_cycles: int = 3) -> List[Dict]:
        """Extract sample cycles for visualization"""
        
        sample_cycles = []
        cycles = self.df.groupby('Cycle')
        
        for cycle_num in self.df['Cycle'].unique()[:num_cycles]:
            cycle_data = self.df[self.df['Cycle'] == cycle_num]
            sample_cycles.append({
                'cycle_number': int(cycle_num),
                'points': len(cycle_data),
                'voltage_min': float(cycle_data['Voltage'].min()),
                'voltage_max': float(cycle_data['Voltage'].max()),
                'voltage_mean': float(cycle_data['Voltage'].mean()),
                'current_mean': float(cycle_data['Current'].mean()),
                'time_start': cycle_data.iloc[0]['Test_Time(s)'],
                'time_end': cycle_data.iloc[-1]['Test_Time(s)'],
                'duration': cycle_data.iloc[-1]['Test_Time(s)'] - cycle_data.iloc[0]['Test_Time(s)'],
            })
        
        return sample_cycles


class CALCEDataValidator:
    """Validate RealisticBatterySimulator against CALCE data"""
    
    def __init__(self, calce_loader: CALCEDataLoader, simulator_class):
        """
        Initialize validator
        
        Args:
            calce_loader: CALCEDataLoader instance
            simulator_class: RealisticBatterySimulator class
        """
        self.loader = calce_loader
        self.simulator_class = simulator_class
        self.validation_results = {}
    
    def compare_voltage_ranges(self) -> Dict:
        """Compare simulator voltage range to CALCE data"""
        
        calce_stats = self.loader.stats['voltage']
        
        # Simulate some data points
        sim = self.simulator_class()
        sim_voltages = []
        for _ in range(1000):
            data = sim.generate_data()
            sim_voltages.append(data['voltage'])
        
        sim_voltages = np.array(sim_voltages)
        
        return {
            'calce_voltage_min': calce_stats['pack_voltage_min'],
            'calce_voltage_max': calce_stats['pack_voltage_max'],
            'simulator_voltage_min': float(sim_voltages.min()),
            'simulator_voltage_max': float(sim_voltages.max()),
            'simulator_voltage_mean': float(sim_voltages.mean()),
            'range_match': 'GOOD' if (calce_stats['pack_voltage_min'] <= sim_voltages.min() < 
                                      sim_voltages.max() <= calce_stats['pack_voltage_max'] * 1.1) else 'CHECK',
        }
    
    def compare_current_ranges(self) -> Dict:
        """Compare simulator current range to CALCE data"""
        
        calce_stats = self.loader.stats['current']
        
        # Simulate data
        sim = self.simulator_class()
        sim_currents = []
        for _ in range(1000):
            data = sim.generate_data()
            sim_currents.append(data['current'])
        
        sim_currents = np.array(sim_currents)
        
        return {
            'calce_current_mean': calce_stats['current_mean'],
            'calce_current_std': calce_stats['current_std'],
            'simulator_current_mean': float(sim_currents.mean()),
            'simulator_current_std': float(sim_currents.std()),
            'simulator_current_min': float(sim_currents.min()),
            'simulator_current_max': float(sim_currents.max()),
            'note': f"CALCE: {calce_stats['current_mean']:.2f}A (constant) vs Simulator: {sim_currents.mean():.0f}A (variable - realistic cycling)"
        }
    
    def validate_all(self) -> Dict:
        """Run all validations"""
        
        print("\n🔍 VALIDATING SIMULATOR AGAINST CALCE DATA...")
        
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'voltage_comparison': self.compare_voltage_ranges(),
            'current_comparison': self.compare_current_ranges(),
        }
        
        return self.validation_results
    
    def print_validation_report(self):
        """Print formatted validation report"""
        
        if not self.validation_results:
            self.validate_all()
        
        print("\n" + "="*70)
        print("SIMULATOR VALIDATION AGAINST CALCE DATA")
        print("="*70)
        
        print("\n✅ VOLTAGE VALIDATION")
        vc = self.validation_results['voltage_comparison']
        print(f"  CALCE Range:     {vc['calce_voltage_min']:.1f}V - {vc['calce_voltage_max']:.1f}V")
        print(f"  Simulator Range: {vc['simulator_voltage_min']:.1f}V - {vc['simulator_voltage_max']:.1f}V")
        print(f"  Status:          {vc['range_match']}")
        
        print("\n⚡ CURRENT VALIDATION")
        cc = self.validation_results['current_comparison']
        print(f"  {cc['note']}")
        
        print("\n" + "="*70)


class CALCEHybridSimulator:
    """Hybrid simulator: Uses CALCE patterns with realistic physics"""
    
    def __init__(self, calce_loader: CALCEDataLoader, realistic_simulator_class):
        """
        Initialize hybrid simulator
        
        Args:
            calce_loader: CALCEDataLoader instance
            realistic_simulator_class: RealisticBatterySimulator class
        """
        self.loader = calce_loader
        self.realistic_sim = realistic_simulator_class()
        self.stats = calce_loader.stats
        self.message_count = 0
    
    def generate_hybrid_data(self) -> Dict:
        """
        Generate data using hybrid approach:
        - Use RealisticBatterySimulator physics
        - Tune parameters based on CALCE statistics
        - Ensure outputs match CALCE observed ranges
        """
        
        # Get realistic physics-based data
        data = self.realistic_sim.generate_data()
        
        # Validate against CALCE ranges
        calce_v = self.stats['voltage']
        if data['voltage'] < calce_v['pack_voltage_min'] * 0.95:
            data['voltage'] = calce_v['pack_voltage_min'] * 0.95
        elif data['voltage'] > calce_v['pack_voltage_max'] * 1.05:
            data['voltage'] = calce_v['pack_voltage_max'] * 1.05
        
        # Add CALCE validation metadata
        data['validated_against_calce'] = True
        data['message_count'] = self.message_count
        
        self.message_count += 1
        return data
    
    def generate_anomaly(self) -> Dict:
        """Generate anomaly with CALCE-validated parameters"""
        
        return self.realistic_sim.generate_anomaly()


def main():
    """Example usage"""
    
    csv_path = Path(__file__).parent / "CALCE_Preprocessed.csv"
    
    # Load and analyze CALCE data
    loader = CALCEDataLoader(str(csv_path))
    loader.get_full_statistics()
    loader.print_summary()
    loader.export_statistics()
    
    # Print sample cycles
    print("\n📋 Sample Cycles:")
    samples = loader.get_sample_cycles(5)
    for cycle in samples:
        print(f"  Cycle {cycle['cycle_number']}: {cycle['points']} points, "
              f"V={cycle['voltage_min']:.4f}-{cycle['voltage_max']:.4f}V, "
              f"Duration: {cycle['duration']:.1f}s")


if __name__ == "__main__":
    main()
