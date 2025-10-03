# CALCE Battery Preprocessing

This project provides a robust preprocessing helper for CALCE battery cycling logs. The main script, `CALCE_BATT_INR.py`, is designed to handle various input formats, clean the data, and perform feature engineering for analysis.

## Project Structure

```
calce-batt-inr
├── src
│   └── CALCE_BATT_INR.py        # Main script for preprocessing battery logs
├── Dockerfile                    # Dockerfile for building the Docker image
├── docker-compose.yml            # Docker Compose configuration
├── requirements.txt              # Python dependencies
├── .dockerignore                 # Files to ignore when building the Docker image
└── README.md                     # Project documentation
```

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd calce-batt-inr
   ```

2. Build the Docker image:
   ```
   docker build -t calce-batt-inr .
   ```

### Running the Application

You can run the application using Docker Compose:

```
docker-compose up
```

### Usage

To preprocess a CALCE battery log, you can run the following command inside the Docker container:

```
python src/CALCE_BATT_INR.py --input <input_file.csv> --output <output_file.csv>
```

Replace `<input_file.csv>` with the path to your input CSV or Excel file and `<output_file.csv>` with the desired output file name.

### Example

```
python src/CALCE_BATT_INR.py --input CALCE_battery_log.csv --output CALCE_Preprocessed.csv
```

### License

This project is licensed under the MIT License. See the LICENSE file for details.