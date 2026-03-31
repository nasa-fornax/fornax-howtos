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

# Setting Up a Conda Environment on Fornax

## Learning Goals

By the end of this tutorial, you will be able to:

1. Create a conda environment specification file.
2. Build a persistent conda environment on Fornax using `setup-conda-env`.
3. Activate your environment in a terminal.

## Introduction

Fornax comes with several pre-installed software environments for common astronomy workflows.
However, you may need packages that are not already installed — for example, a specialized retrieval code or a specific version of a library.

On Fornax, you can create your own **persistent conda environment** that survives between sessions and is available both in the terminal and as a Jupyter kernel.
This tutorial walks through the steps to do that.

## Instructions

This notebook does **not** execute any of the commands shown below.
All commands shown in code blocks must be run manually in a terminal by copying and pasting them.
The notebook serves only as documentation of the workflow.
```

+++

## 1. Understand the two types of environments on Fornax

Fornax supports two kinds of user-managed environments:

- **Pip-based environments** — managed with the `uv` package manager
- **Conda-based environments** — managed with `micromamba`

This tutorial covers conda environments, which are a good choice when your software requires non-Python dependencies (compiled libraries, Fortran code, MPI, etc.) or when you need tightly pinned version combinations that are easier to express in a conda YAML file.

For more details, see the [Fornax compute environments documentation](https://docs.fornax.sciencecloud.nasa.gov/compute-environments/).

+++

## 2. Create a conda environment file

A conda environment is defined by a YAML file that lists the environment name, package channels, and dependencies.

**Important:** The file name must start with `conda-` for the Fornax `setup-conda-env` tool to recognize it.

Here is a simple example — a general-purpose astronomy environment.
A copy of this file (`conda-myenv.yml`) is included in the `tutorials/environment_setup/` directory for convenience.

```yaml
name: myenv
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy
  - astropy
  - matplotlib
  - pandas
```

Save this file as `conda-myenv.yml` in the directory where you will run the setup command.

A few notes on the file format:

- The environment name is derived from the file name by stripping the `conda-` prefix (e.g., `conda-myenv.yml` creates an environment named `myenv`). We recommend setting the `name:` field in the YAML to match, although it is not strictly required.
  You will use the environment name to activate the environment.
- `channels` tells conda where to look for packages.
  `conda-forge` is a large community channel with a wide selection of astronomy software.
- `dependencies` lists the packages to install.
  Use conda packages whenever possible; only use a `pip:` subsection for packages unavailable through conda channels, and pip packages should be listed last.

+++

## 3. Build the environment

Once your YAML file is ready, open a terminal on Fornax and navigate to the directory containing your `conda-*.yml` file.
Then run:

```bash
setup-conda-env --user
```

```{admonition} Important
The `--user` flag is important — it installs the environment into your personal storage directory (`$USER_ENV_DIR`) so that it persists between Fornax sessions.
```

What to expect:

- The tool will find your `conda-*.yml` file and prompt you to confirm the environment name.
- First-time environment creation can take **more than 10 minutes**, especially for larger dependency sets.
- You will see progress output as packages are solved and installed.
- In addition to the conda environment, the tool also registers a Jupyter kernel, making the environment available for use in notebooks.
- If an environment with the same name already exists, the tool will error. Delete the environment first (see below) before re-running.

If you have multiple `conda-*.yml` files in the same directory, the tool will create an environment for each one.

+++

## 4. Activate the environment in a terminal

After the build completes, activate your environment with:

```bash
micromamba activate $USER_ENV_DIR/myenv
```

Replace `myenv` with the `name` field from your YAML file.

Once activated, the environment name will appear in your terminal prompt (e.g., `(myenv)`), and `python`, `pip`, and all installed packages will come from your new environment.

To deactivate and return to the default environment:

```bash
micromamba deactivate
```

+++

## 5. Summary checklist

1. Write a `conda-<name>.yml` file with your desired packages.
2. Run `setup-conda-env --user` from the directory containing the file.
3. Activate with `micromamba activate $USER_ENV_DIR/<name>`.

## Next steps

- To install additional packages into an existing environment, activate it and use `micromamba install <package>`. Avoid using `pip install` when possible — installing conda packages after pip can cause conflicts.
- To update the environment from a modified YAML file, delete the existing environment first (see below), then re-run `setup-conda-env --user`.
- To delete an environment and its Jupyter kernel, run:

  ```bash
  rm -rf $USER_ENV_DIR/<name>
  rm -rf ~/.local/share/jupyter/kernels/<name>
  ```
- For pip-based environments (lighter-weight, faster to create), see the [Fornax compute environments documentation](https://docs.fornax.sciencecloud.nasa.gov/compute-environments/).

+++

## Acknowledgements

- [Caltech/IPAC-IRSA](https://irsa.ipac.caltech.edu/)
- Portions of this tutorial were developed with the assistance of AI tools.

## About this notebook

**Authors:** Jessica Krick, Troy Raen, Brigitta Sipőcz

**Updated:** 31 March 2026

**Contact:** For help with this notebook, please open a topic in the [Fornax Helpdesk](https://discourse.fornax.sciencecloud.nasa.gov/c/helpdesk/6).

**Runtime:** This notebook is not intended to do any calculations on its own, so runtime is insignificant.

