#!/usr/bin/env python3
"""Run the petitRADTRANS "Basic retrieval" setup as a script, with optional MPI.

This is intended as a practical smoke test for:
- PyMultiNest + MultiNest library loading
- MPI launch (multiple ranks start)
- basic scaling (wall-time decreases as ranks increase)

Notes
-----
- This script uses the built-in model function ``isothermal_transmission``.
- It sets ``OMP_NUM_THREADS=1`` by default to avoid thread oversubscription
  when running multiple MPI ranks.
- Opacity files are not stored in this repository due to size constraints.
  Download and configure your own opacity files following:
  https://petitradtrans.readthedocs.io/en/latest/content/available_opacities.html
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed CLI arguments for paths and retrieval runtime options.
    """
    # Collect the runtime knobs users typically tune while benchmarking.
    p = argparse.ArgumentParser(
        description="pRT basic retrieval (PyMultiNest) with optional MPI."
    )
    p.add_argument(
        "--prt-data",
        type=str,
        default="/home/jkrick/fornax-demo-notebooks/pRT/prt_data",
        help="Directory containing hst_example_clear_spec.txt ",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default="./retrievals/runs",
        help="Directory to write retrieval outputs (default: ./retrievals/runs).",
    )
    p.add_argument(
        "--name",
        type=str,
        default="hst_example_clear_spec",
        help="Retrieval name (default: hst_example_clear_spec).",
    )
    p.add_argument(
        "--use-mpi",
        action="store_true",
        help="Enable MPI mode (pass use_mpi=True to pRT Retrieval).",
    )
    p.add_argument(
        "--n-live-points",
        type=int,
        default=40,
        help="Number of live points for MultiNest (default: 40). Increase to see scaling.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Resume an existing run if present (default: False = start fresh).",
    )
    p.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Run in evaluate mode (plots only) instead of retrieve mode.",
    )
    p.add_argument(
        "--omp-threads",
        type=int,
        default=1,
        help="Set OMP_NUM_THREADS (default: 1). Keep 1 for MPI tests.",
    )
    return p.parse_args()


def _mpi_banner() -> None:
    """Print MPI rank/size if ``mpi4py`` is available.

    Notes
    -----
    If ``mpi4py`` is not installed, this function logs a brief message and
    continues, since retrieval can still run under ``mpirun`` without the banner.
    """
    # mpi4py is optional; this banner is just a launch diagnostic.
    try:
        from mpi4py import MPI  # type: ignore
    except ImportError:
        host = os.uname().nodename
        print(
            f"[mpi] mpi4py unavailable; no rank banner (host={host})",
            file=sys.stderr,
            flush=True,
        )
        return

    # Report rank/size so users can verify mpirun launched all workers.
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    host = os.uname().nodename
    print(f"[mpi] rank {rank}/{size} on {host}", file=sys.stderr, flush=True)


def main() -> int:
    """Run the retrieval workflow.
Documentation on how to use pRT is here: https://petitradtrans.readthedocs.io/en/latest/
    Returns
    -------
    int
        Process exit code. Returns ``0`` on success.

    Raises
    ------
    FileNotFoundError
        If the expected input data file does not exist in ``--prt-data``.
    ImportError
        If required retrieval dependencies (for example ``petitRADTRANS``)
        are not available in the active Python environment.
    """
    # Parse user options before setting up retrieval state.
    args = _parse_args()

    # Point pRT to the user-supplied opacity/data directory.
    os.environ["PRT_INPUT_DATA_PATH"] = args.prt_data
    os.environ["pRT_input_data_path"] = args.prt_data  # harmless if unused
    print(
        f"[prt] PRT_INPUT_DATA_PATH={os.environ.get('PRT_INPUT_DATA_PATH')}",
        file=sys.stderr,
        flush=True,
    )
    print(
        "[prt] ENV dump:",
        {
            k: os.environ.get(k)
            for k in [
                "PRT_INPUT_DATA_PATH",
                "pRT_input_data_path",
                "PRT_DATA",
                "PETITRADTRANS_INPUT_DATA_PATH",
            ]
        },
        file=sys.stderr,
        flush=True,
    )

    # Keep one OpenMP thread per rank unless user explicitly overrides.
    os.environ["OMP_NUM_THREADS"] = str(args.omp_threads)

    # Optional: print MPI info to confirm you launched multiple ranks
    _mpi_banner()

    # Import retrieval dependencies only after environment variables are set.
    import numpy as np  # noqa: F401
    from petitRADTRANS import physical_constants as cst
    from petitRADTRANS.retrieval import Retrieval, RetrievalConfig
    from petitRADTRANS.retrieval.models import isothermal_transmission

    # Resolve user paths and confirm expected tutorial data file exists.
    prt_data_dir = Path(args.prt_data).expanduser().resolve()
    data_file = prt_data_dir / "hst_example_clear_spec.txt"
    if not data_file.exists():
        raise FileNotFoundError(
            f"Cannot find data file: {data_file}\n"
            "Expected hst_example_clear_spec.txt in --prt-data directory."
        )

    # Ensure output path exists before initializing pRT retrieval objects.
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Toggle between full retrieval and evaluate-only mode from CLI.
    run_mode = "evaluate" if args.evaluate_only else "retrieve"

    # Build the retrieval configuration to match the notebook-style example.
    retrieval_config = RetrievalConfig(
        retrieval_name=args.name,
        run_mode=run_mode,
        amr=False,
        scattering_in_emission=False,
    )

    # Fixed stellar radius for this example target.
    retrieval_config.add_parameter(
        "stellar_radius",
        False,
        value=0.651 * cst.r_sun,
    )

    # Free parameters with explicit prior transforms from unit cube.
    retrieval_config.add_parameter(
        "log_g",
        True,
        transform_prior_cube_coordinate=lambda x: 2.0 + 3.5 * x,
    )

    retrieval_config.add_parameter(
        "planet_radius",
        True,
        transform_prior_cube_coordinate=lambda x: (0.2 + 0.2 * x) * cst.r_jup_mean,
    )

    retrieval_config.add_parameter(
        "temperature",
        True,
        transform_prior_cube_coordinate=lambda x: 300.0 + 2000.0 * x,
    )

    retrieval_config.add_parameter(
        "log_Pcloud",
        True,
        transform_prior_cube_coordinate=lambda x: -6.0 + 8.0 * x,
    )

    # Set opacity sources and line lists used in the transmission model.
    retrieval_config.set_rayleigh_species(["H2", "He"])
    retrieval_config.set_continuum_opacities(["H2--H2", "H2--He"])

    retrieval_config.set_line_species(
        [
            "H2O__POKAZATEL",
            "CH4__HITEMP",
            "CO-NatAbund__HITEMP",
        ],
        eq=False,
        abund_lim=(-6.0, 0.0),
    )

    # Register the tutorial spectrum and model wrapper with retrieval config.
    retrieval_config.add_data(
        "HST",
        str(data_file),
        model_generating_function=isothermal_transmission,
        line_opacity_mode="c-k",
        data_resolution=60,
        model_resolution=120,
    )

    # Instantiate retrieval object and force PyMultiNest backend.
    retrieval = Retrieval(
        retrieval_config,
        output_directory=str(output_dir),
        use_mpi=bool(args.use_mpi),
        evaluate_sample_spectra=False,
        use_prt_plot_style=True,
        ultranest=False,
    )

    # Execute the nested sampling run with user-selected runtime controls.
    retrieval.run(
        n_live_points=args.n_live_points,
        const_efficiency_mode=False,
        resume=bool(args.resume),
    )
    print("\nDone.")
    print(f"Outputs written to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
