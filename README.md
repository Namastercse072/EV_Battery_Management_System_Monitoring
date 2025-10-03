# EV_Battery_Management_System_Monitoring
For Data Science - Da Analysis - AI Engineering

# Data for analysis: https://calce.umd.edu/battery-data#INR
Data path: ..\EVResarch
1./ sample INR 18650-20R Battery

##########################################################
Battery (Parameters)	Specifications (Value)
Capacity Rating	2000 mAh
Cell Chemistry	LiNiMnCo/Graphite
Weight (w/o safety circuit)	45 g
Diameter	18.33 mm ± 0.07 mm
Length	64.85 mm ± 0.15 mm
Special Notes	Tab length not included in the dimensions
pwsh: $f = Get-ChildItem -Path '.\data' -Include '*.csv','*.xlsx' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1; if ($f) { python .\CALCE_BATT_INR.py --input $f.FullName --output '.\CALCE_Preprocessed.csv' --no-plot } else { Write-Error 'No CSV/XLSX found in .\data' }
#########################################################