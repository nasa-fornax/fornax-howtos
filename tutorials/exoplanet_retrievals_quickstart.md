---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.1
kernelspec:
  name: python3
  display_name: python3
  language: python
---

# Exoplanet Retrieval Quickstart


## Learning goals

By the end of this tutorial, you will be able to:

1. Set up a persistent environment for retrieval software on Fornax.
2. Install and activate dependencies for pRT retrieval workflows.
3. Run Python retrieval scripts with `mpirun`for optimal parallelization.
4. Benchmark scaling behavior to estimate realistic runtime.

## Introduction

This tutorial shows how to run an exoplanet atmospheric retrieval workflow on the Fornax Science Console, using [petitRADTRANS](https://petitradtrans.readthedocs.io/en/latest/index.html) (pRT) + [`pymultinest`](https://johannesbuchner.github.io/PyMultiNest/) + [Message Passing Interface](https://www.mpich.org) (MPI) as an example stack. 
This code follows the example basic retrieval [tutorial](https://petitradtrans.readthedocs.io/en/latest/content/notebooks/retrieval_basic.html) from pRT. 
This tutorial is intended to show the steps involved in getting exoplanet retrievals to run on a system like Fornax, and does not show the details and specifics of how to tailor existing retrieval codes to match specific datasets.

## Instructions
Use this guide as a companion reference while working in a Fornax terminal session.

```{admonition} Important
This notebook does **not** execute any of the setup or MPI commands shown below.
All commands shown in code blocks must be run manually in a terminal by copying and pasting them. 
The notebook serves only as documentation of the workflow.
```




+++

## 1. Create a persistent environment for retrieval dependencies

Retrieval workflows generally require tightly constrained scientific software stacks. 
On Fornax, use a persistent user-managed conda/micromamba environment.
Instructions for how to do that are here: https://docs.fornax.sciencecloud.nasa.gov/compute-environments/

Create a file named `conda-exo.yml` with the following contents.  
One is also provided in the examples/exoplanet_retrievals directory for convenience.  
Note that the name of the file must start with "conda-" for the setup script to find it.

```yaml
name: exo
channels:
  - conda-forge
dependencies:
  - python=3.12
  - pymultinest
  - c-compiler
  - cxx-compiler
  - fortran-compiler
  - pip
  - pip:
      - matplotlib
      - numba
      - "petitRADTRANS[retrieval]"
      - pandas
```

### 1.1 Build the environment:

From the terminal, `cd` into the directory where you saved the conda file, then build the environment with the following command:

```bash
setup-conda-env --user
```

Notes:

- The tool prompts you to confirm the environment name.
- First-time environment creation may take more than 10 minutes.
- Environments containing packages to run retrievals can consume significant storage.

### 1.2 Activate the environment:

From the terminal, activate the environment with the following command:
```bash
micromamba activate $USER_ENV_DIR/exo
```

+++

## 2. Install opacity files (required and large)

Many retrieval tools (including pRT) require local opacity files that are too large to package in this repository.

- You must download/install opacities in your own Fornax storage.
- Opacity files are **not** distributed in this repo due to size constraints.
- pRT opacity installation instructions: <https://petitradtrans.readthedocs.io/en/latest/content/available_opacities.html>

If centralized opacity hosting on Fornax would help your workflow, please share feedback with the Fornax team.

+++

## 3. Run retrieval scripts with MPI

For pRT workflows that use `pymultinest`, write retrieval wrappers as Python scripts and launch with `mpirun`.

This repository includes:

- `examples/exoplanet-retrievals/run_prt_basic_pymultinest_mpi.py`
- `examples/exoplanet-retrievals/hst_example_clear_spec.txt`

Example MPI launch commands:
Note: The --n-live-points argument sets the number of “live” samples (n_live in MultiNest terminology) maintained during nested sampling; larger values improve the stability of evidence and posterior estimates but increase runtime.
```bash
# Small validation run (recommended first test)
mpirun -np 2 python examples/exoplanet-retrievals/run_prt_basic_pymultinest_mpi.py --use-mpi --n-live-points 40

# Medium run for quick scaling checks (assuming you have ncores > 8)
mpirun -np 8 python examples/exoplanet-retrievals/run_prt_basic_pymultinest_mpi.py --use-mpi --n-live-points 40
```
### 3.1 Expected output

When you run the retrieval with mpirun, you should see:
- Validation checks confirming that the input data and model functions execute without errors.
- A MultiNest header showing the number of live points and model dimensionality.
- Periodic sampling updates (acceptance rate, total samples, and evidence ln Z estimates).
- A final summary including log evidence (ln Z ± uncertainty), total likelihood evaluations, and retrieved parameter values with uncertainties

For the small validation run (--n-live-points 40), expect on the order of ~1,000–2,000 likelihood evaluations and a runtime of a few minutes, depending on the number of MPI processes used. 
Larger n_live_points values will increase runtime substantially but produce more stable evidence estimates and posterior constraints.

Output files are written to:
`retrievals/runs/out_PMN/`
This directory contains the MultiNest chain files, posterior summaries, and generated diagnostic plots (including corner plots). 
After the run completes, check this directory for retrieval results and figures.
### 3.2 Important Fornax MPI subtleties

When running pRT retrievals with MPI on Fornax, using all available CPU cores can exhaust limited shared-memory space (`/dev/shm`) used for inter-process communication. 
This can fail jobs even when system RAM is still available.

In practice:

1. Speedup is usually sub-linear.
2. Performance gains often flatten before you reach all available cores.
3. Many workflows perform best around roughly half to three-quarters of available cores.

+++

## 4. Benchmark to estimate full retrieval runtime

Full retrieval wall time is difficult to predict in advance. 
Benchmarking your own setup (opacities, chemistry assumptions, cloud setup, live points) helps you choose compute size and estimate total runtime. 
If you anticipate that your retrieval will run longer than a few hours, enabling the [JupyterLab keep-alive feature](https://docs.fornax.sciencecloud.nasa.gov/jupyterlab/#jupyterlab-session-information) can prevent unintended shutdown. 
However, keep-alive sessions incur credit charges for their entire lifetime, regardless of active CPU usage, so plan accordingly and monitor extended runs.

### Benchmark figure 1: speedup vs nprocs

```{figure} ../examples/exoplanet-retrievals/speedup_vs_nprocs.png
:alt: Speedup versus number of MPI processes
:name: fig-speedup-vs-nprocs

Speedup is defined as the wall time for 1 processor divided by the wall time for *nprocs* processors.  
Typical behavior includes (1) non-linear scaling, (2) useful speedup up to about 0.5-0.75× of available cores, and (3) Larger gains are seen for larger n_live_points (shown as n_live in the legend), which controls the number of active samples MultiNest keeps while exploring parameter space. 
Increasing n_live_points improves posterior and evidence stability but increases runtime.
Overheads are a major cause of non-linear speedups and limits in gains as a function of `nprocs`.
```

### Benchmark figure 2: seconds per likelihood evaluation vs nprocs

```{figure} ../examples/exoplanet-retrievals/seconds_per_likelihood_eval_vs_nprocs.png
:alt: Seconds per likelihood evaluation versus number of MPI processes
:name: fig-seconds-per-like

The example figure illustrates typical scaling behavior for this configuration, but runtime depends strongly on your specific retrieval setup. 
To obtain a reliable estimate for your own science case, repeat short test runs at multiple -np values (e.g., 2, 4, 8, etc.) and a range of n_live_points, record the wall time for each, and construct a similar scaling curve. 
This allows you to estimate total runtime and select compute resources based on measured performance rather than core count alone.
```

+++

## 5. Recommended workflow checklist

1. Build and activate your persistent retrieval environment.
2. Install pRT opacities in persistent user storage.
3. Validate script execution at low `-np` first.
4. Benchmark multiple `-np` values.
5. Choose a server size based on measured scaling, not core count alone.
6. Use keep-alive for retrievals expected to exceed a few hours.

## Next steps

- Adapt the example script to your science case (parameterization, priors, cloud model, chemistry assumptions).
- Re-run scaling tests when model complexity changes.
- Archive configuration files and environment specs for reproducibility.

+++

## Acknowledgements

- [Caltech/IPAC-IRSA](https://irsa.ipac.caltech.edu/)

## About this notebook

**Authors:** IRSA Data Science Team, including Jessica Krick, Troy Raen, Brigitta Sipőcz, Andreas Faisst, Jaladh Singhal, Vandana Desai

**Updated:** 2 March 2026

**Contact:** [IRSA Helpdesk](https://irsa.ipac.caltech.edu/docs/help_desk.html) with questions or problems.

**Runtime:** This notebook is not intended to do any calculations on its own, so runtime is insignificant.

```{code-cell} ipython3

```
