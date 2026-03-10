#!/usr/bin/env python3
"""Download and prepare pRT opacity files required for the exoplanet retrieval tutorial.

Run this script once, before running the retrieval:

    python setup_opacities.py

This script:
- Creates an input_data/ directory alongside this script
- Updates the pRT config to point to that directory
- Downloads the R1000 opacity files from the Keeper repository
- Rebins line opacities to R120 (the resolution used in this tutorial)
- Fixes a known naming mismatch in the rebinned CO opacity file
"""

import os
import shutil
from pathlib import Path

from petitRADTRANS.cli.prt_cli import download_input_data
from petitRADTRANS.config import petitradtrans_config_parser

# Create input_data/ alongside this script and register it with pRT.
# Note: set_input_data_path permanently updates ~/.petitradtrans/petitradtrans_config_file.ini,
# changing the global pRT input data path for all pRT usage on this system.
# If you already have pRT configured with your own opacity data elsewhere, you can
# restore your original path by calling set_input_data_path('/your/original/path') again.
input_data_dir = Path(__file__).parent / "input_data"
input_data_dir.mkdir(parents=True, exist_ok=True)
petitradtrans_config_parser.set_input_data_path(str(input_data_dir))

print(f"pRT input data path set to: {input_data_dir}")
print("Downloading opacity files. Each file may be several hundred MB.")
print("This may take significant time depending on your connection.\n")

# Set env var before importing pRT modules (pRT reads it at import time).
os.environ["PRT_INPUT_DATA_PATH"] = str(input_data_dir)

# The pRT config URL is missing 'files/' which is required for direct downloads
# from Keeper. We override it here.
keeper_url = "https://keeper.mpdl.mpg.de/d/ccf25082fda448c8a0d0/files/?p="

# R1000 line opacity files and CIA files — confirmed available on Keeper.
# R120 versions are not available on Keeper; they are created by rebinning below.
opacity_files = [
    "opacities/lines/correlated_k/H2O/1H2-16O/1H2-16O__POKAZATEL.R1000_0.3-50mu.ktable.petitRADTRANS.h5",
    "opacities/lines/correlated_k/CH4/12C-1H4/12C-1H4__HITEMP.R1000_0.1-250mu.ktable.petitRADTRANS.h5",
    "opacities/lines/correlated_k/CO/C-O-NatAbund/C-O-NatAbund__HITEMP.R1000_0.1-250mu.ktable.petitRADTRANS.h5",
    "opacities/continuum/collision_induced_absorptions/H2--H2/H2--H2-NatAbund/H2--H2-NatAbund__BoRi.R831_0.6-250mu.ciatable.petitRADTRANS.h5",
    "opacities/continuum/collision_induced_absorptions/H2--He/H2--He-NatAbund/H2--He-NatAbund__BoRi.DeltaWavenumber2_0.5-500mu.ciatable.petitRADTRANS.h5",
]

for relative_path in opacity_files:
    destination = str(input_data_dir / relative_path)
    download_input_data(
        destination=destination,
        path_input_data=str(input_data_dir),
        url_input_data=keeper_url,
    )

# Rebin line opacities from R1000 to R120, which is the model_resolution used in this tutorial.
# This runs in a single process to avoid the MPI race condition that occurs when
# multiple ranks try to rebin the same file simultaneously.
print("\nRebinning line opacities to R120...")
from petitRADTRANS.__file_conversion import rebin_ck_line_opacities  # noqa: E402  # pRT internal utility for rebinning correlated-k opacity tables using exo_k

line_r1000_files = [
    input_data_dir / "opacities/lines/correlated_k/H2O/1H2-16O/1H2-16O__POKAZATEL.R1000_0.3-50mu.ktable.petitRADTRANS.h5",
    input_data_dir / "opacities/lines/correlated_k/CH4/12C-1H4/12C-1H4__HITEMP.R1000_0.1-250mu.ktable.petitRADTRANS.h5",
    input_data_dir / "opacities/lines/correlated_k/CO/C-O-NatAbund/C-O-NatAbund__HITEMP.R1000_0.1-250mu.ktable.petitRADTRANS.h5",
]

for r1000_file in line_r1000_files:
    rebin_ck_line_opacities(str(r1000_file), target_resolving_power=120)

# Fix a known naming mismatch for CO: exo_k rebins using the isotopologue-specific
# name (12C-16O-NatAbund) but pRT looks for the generic name (C-O-NatAbund).
# Create a copy with the name pRT expects.
co_dir = input_data_dir / "opacities/lines/correlated_k/CO/C-O-NatAbund"
misnamed = list(co_dir.glob("12C-16O-NatAbund__HITEMP.R120*.h5"))
if misnamed:
    source = misnamed[0]
    correct_name = source.name.replace("12C-16O-NatAbund", "C-O-NatAbund")
    correct_path = co_dir / correct_name
    if not correct_path.exists():
        shutil.copy2(str(source), str(correct_path))
        print(f"Fixed CO R120 filename: {correct_path.name}")

print(f"\nAll opacity files ready in: {input_data_dir}")
print("You are ready to run the retrieval.")
