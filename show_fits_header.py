from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Optional

try:
    from astropy.io import fits
    from astropy.table import Table
except Exception as import_error:  # pragma: no cover
    sys.stderr.write(
        "Error: astropy is required to run this script.\n"
        "Install with: pip install astropy\n"
        f"Details: {import_error}\n"
    )
    sys.exit(1)


def print_hdu_headers(hdul: "fits.HDUList") -> None:
    """
    Print basic info for each HDU and the full header content.
    """
    hdul.info()
    for index, hdu in enumerate(hdul):
        print(f"\n=== HDU {index}: {hdu.__class__.__name__} ===")
        # repr(header) produces a compact multi-line string of the card list
        print(repr(hdu.header))


def print_table_preview(hdu: "fits.BinTableHDU | fits.TableHDU", num_rows: int) -> None:
    """
    Print the first num_rows of a table HDU.
    """
    if getattr(hdu, "data", None) is None:
        print("This HDU has no data to preview.")
        return
    try:
        table = Table(hdu.data)
        # Slice safely even if num_rows exceeds length
        preview = table[: max(0, num_rows)]
        print(f"\n--- First {len(preview)} rows of HDU table preview (all columns) ---")
        preview.pprint_all()
    except Exception as exc:
        sys.stderr.write(f"Could not render table preview: {exc}\n")
        # Fall back to numpy structured array print
        try:
            print(hdu.data[: max(0, num_rows)])
        except Exception as exc2:
            sys.stderr.write(f"Fallback preview also failed: {exc2}\n")


def resolve_path(path_arg: Optional[str]) -> Path:
    """
    Resolve the provided string path to an absolute Path.
    """
    if path_arg is None or path_arg.strip() == "":
        return Path(            
            "./tess2019199201929-s0014-s0026-0000000020212631-00353_dvt.fits"
        )
    return Path(path_arg).expanduser().resolve()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print FITS HDU info and headers; optionally preview table rows."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to FITS file (defaults to the embedded dataset path).",
    )
    parser.add_argument(
        "--preview-hdu",
        type=int,
        default=None,
        help="If set, print the first N rows from this HDU (for table HDUs).",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=10,
        help="Number of rows to preview when --preview-hdu is provided (default: 10).",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    """
    Open the FITS file and print HDU info and headers.
    Usage:
        python show_fits_header.py [optional_path_to_fits] [--preview-hdu N] [--rows M]
    """
    args = parse_args(argv)
    input_path = resolve_path(args.path)
    if not input_path.exists():
        sys.stderr.write(f"Error: file not found: {input_path}\n")
        return 2

    try:
        with fits.open(input_path, mode="readonly", memmap=True) as hdul:
            print_hdu_headers(hdul)
            if args.preview_hdu is not None:
                index = args.preview_hdu
                if index < 0 or index >= len(hdul):
                    sys.stderr.write(
                        f"Invalid HDU index {index}. File has {len(hdul)} HDUs.\n"
                    )
                    return 5
                hdu = hdul[index]
                if not isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                    print(
                        f"\nHDU {index} is {hdu.__class__.__name__}; "
                        "it is not a table HDU with rows to preview."
                    )
                else:
                    print_table_preview(hdu, args.rows)
    except FileNotFoundError:
        sys.stderr.write(f"Error: file not found: {input_path}\n")
        return 2
    except OSError as ose:
        # astropy raises OSError for invalid/corrupt FITS files
        sys.stderr.write(f"Error opening FITS file: {ose}\n")
        return 3
    except Exception as unexpected:
        sys.stderr.write(f"Unexpected error: {unexpected}\n")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


