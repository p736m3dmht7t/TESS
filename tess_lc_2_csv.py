# tess_lc_2_csv.py: Exports HDU 1 binary table from a FITS file to a CSV file
# Sections:
# - resolve_path
# - parse_args
# - main

from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Optional

try:
    from astropy.io import fits
    from astropy.table import Table
    import numpy as np
except Exception as import_error:  # pragma: no cover
    sys.stderr.write(
        "Error: astropy is required to run this script.\n"
        "Install with: pip install astropy\n"
        f"Details: {import_error}\n"
    )
    sys.exit(1)


# --- resolve_path ---
# Resolve the provided string path to an absolute Path
def resolve_path(path_arg: Optional[str]) -> Path:
    """
    Resolve the provided string path to an absolute Path.
    """
    if path_arg is None or path_arg.strip() == "":
        sys.stderr.write("Error: a FITS filepath is required.\n")
        sys.exit(2)
    return Path(path_arg).expanduser().resolve()


# --- parse_args ---
# Parse command-line arguments
def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Export HDU 1 binary table from a FITS file to a CSV file."
    )
    parser.add_argument(
        "path",
        help="Path to FITS file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting the destination CSV file if it exists.",
    )
    parser.add_argument(
        "--zero-point",
        type=float,
        default=0.0,
        help="Zero point for magnitude calculation (default: 0.0).",
    )
    return parser.parse_args(argv[1:])


# --- main ---
# Main execution function
def main(argv: list[str]) -> int:
    """
    Main execution function.
    """
    args = parse_args(argv)
    input_path = resolve_path(args.path)
    if not input_path.exists():
        sys.stderr.write(f"Error: file not found: {input_path}\n")
        return 2

    csv_path = input_path.with_suffix(".csv")
    if csv_path.exists() and not args.overwrite:
        sys.stderr.write(
            f"Error: destination already exists: {csv_path}\n"
            "Re-run with --overwrite to replace it.\n"
        )
        return 6

    try:
        with fits.open(input_path, mode="readonly", memmap=False) as hdul:
            if len(hdul) <= 1:
                sys.stderr.write(
                    f"Error: {input_path} has no HDU 1. Found {len(hdul)} HDU(s).\n"
                )
                return 5
            hdu1 = hdul[1]
            if not isinstance(hdu1, (fits.BinTableHDU, fits.TableHDU)):
                sys.stderr.write(
                    f"Error: HDU 1 is {hdu1.__class__.__name__}, not a table HDU.\n"
                )
                return 5

            if getattr(hdu1, "data", None) is None:
                sys.stderr.write("Error: HDU 1 has no data to export.\n")
                return 5
            table = Table(hdu1.data)

            if "TIME" in table.colnames:
                time_col = table["TIME"]
                if hasattr(time_col, "mask") and getattr(time_col, "mask", None) is not np.ma.nomask:
                    not_masked = ~np.array(time_col.mask, dtype=bool)
                else:
                    not_masked = np.ones(len(table), dtype=bool)
                
                with np.errstate(invalid="ignore"):
                    time_vals = np.asarray(time_col, dtype=float)
                    not_nan = ~np.isnan(time_vals)
                keep_mask = not_masked & not_nan
                table = table[keep_mask]

            if "SAP_FLUX" not in table.colnames:
                sys.stderr.write(
                    "Error: SAP_FLUX column not found in HDU 1 table.\n"
                    "Cannot calculate Source_AMag_T1 column.\n"
                )
                return 5
            sap_flux_col = table["SAP_FLUX"]
            
            if hasattr(sap_flux_col, "mask") and getattr(sap_flux_col, "mask", None) is not np.ma.nomask:
                sap_not_masked = ~np.array(sap_flux_col.mask, dtype=bool)
            else:
                sap_not_masked = np.ones(len(table), dtype=bool)
            
            with np.errstate(invalid="ignore"):
                sap_flux_vals = np.asarray(sap_flux_col, dtype=float)
                sap_not_nan = ~np.isnan(sap_flux_vals)
            sap_valid_mask = sap_not_masked & sap_not_nan
            table = table[sap_valid_mask]

            if "TIME" in table.colnames:
                table["BJD_TDB"] = table["TIME"] + 2457000.0

            tess_mag = hdul[0].header.get("TESSMAG")
            if tess_mag is None:
                sys.stderr.write("Warning: TESSMAG not found in primary header. Defaulting to 0.0 offset.\n")
            
            with np.errstate(invalid="ignore", divide="ignore"):
                # Calculate raw magnitudes (temporary)
                raw_mag = -2.5 * np.log10(table["SAP_FLUX"])
                
                # Identify valid magnitudes for median calculation
                # SAP_FLUX must be > 0 for log10 to be valid (finite)
                valid_mask = np.isfinite(raw_mag)
                
                if np.any(valid_mask):
                    median_raw_mag = np.nanmedian(raw_mag[valid_mask])
                    
                    if tess_mag is not None:
                        zero_point = tess_mag - median_raw_mag
                    else:
                        zero_point = 0.0 
                        
                    table["Source_AMag_T1"] = raw_mag + zero_point
                else:
                    table["Source_AMag_T1"] = np.nan

            # Add Source_AMag_Error_T1 column
            if "SAP_FLUX_ERR" in table.colnames:
                 with np.errstate(invalid="ignore", divide="ignore"):
                    # Error propagation: sigma_mag = 1.0857 * (sigma_flux / flux)
                    # We use the same validity mask as flux, but also check for flux != 0 (already implied by log10 check above for magnitudes, but good to be safe)
                    # Actually, we should just calculate it for all rows and let numpy handle NaNs/Infs
                    mag_err = 1.0857 * (table["SAP_FLUX_ERR"] / table["SAP_FLUX"])
                    table["Source_AMag_Error_T1"] = mag_err
            else:
                 sys.stderr.write("Warning: SAP_FLUX_ERR not found. Skipping Source_AMag_Error_T1 calculation.\n")

            try:
                table.write(
                    csv_path,
                    format="ascii.csv",
                    overwrite=args.overwrite,
                )
            except Exception as io_exc:
                sys.stderr.write(f"Error writing CSV: {io_exc}\n")
                return 6
    except FileNotFoundError:
        sys.stderr.write(f"Error: file not found: {input_path}\n")
        return 2
    except OSError as ose:
        sys.stderr.write(f"Error opening FITS file: {ose}\n")
        return 3
    except Exception as unexpected:
        sys.stderr.write(f"Unexpected error: {unexpected}\n")
        return 4

    print(f"Wrote CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))