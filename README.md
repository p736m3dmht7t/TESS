# TESS Light Curve to CSV Converter

This tool converts TESS (Transiting Exoplanet Survey Satellite) light curve FITS files into CSV format. It extracts the `SAP_FLUX` and `TIME` columns, calculates magnitudes, and performs error propagation.

## Features

- **FITS to CSV Conversion**: Extracts binary table data from HDU 1.
- **Magnitude Calculation**: Converts `SAP_FLUX` to `Source_AMag_T1` using the `TESSMAG` keyword from the primary header for zero-point calibration.
- **Error Propagation**: Calculates `Source_AMag_Error_T1` based on `SAP_FLUX_ERR`.
- **BJD Calculation**: Adds a `BJD_TDB` column (TIME + 2457000).
- **Data Filtering**: Automatically filters out invalid data (NaNs, masked values, non-finite magnitudes).

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/p736m3dmht7t/TESS.git
    cd TESS
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Requires `astropy` and `numpy`)*

## Usage

Run the script with the path to your FITS file:

```bash
python3 tess_lc_2_csv.py path/to/tess_light_curve.fits
```

### Options

- `--overwrite`: Overwrite the output CSV file if it already exists.
- `--zero-point`: (Optional) Manually specify a zero point (overrides automatic calculation, though the current logic prioritizes `TESSMAG`).

### Output

The script generates a CSV file in the same directory as the input FITS file, with the extension `.csv`.

**Columns:**
- `TIME`: Time from the FITS file.
- `TIMECORR`: Time correction.
- `CADENCENO`: Cadence number.
- `SAP_FLUX`: Simple Aperture Photometry flux.
- `SAP_FLUX_ERR`: Error in SAP flux.
- ... (other columns from the FITS table)
- `BJD_TDB`: Barycentric Julian Date (TDB).
- `Source_AMag_T1`: Calculated TESS magnitude.
- `Source_AMag_Error_T1`: Calculated magnitude error.

## License

MIT License. See [LICENSE](LICENSE) for details.
