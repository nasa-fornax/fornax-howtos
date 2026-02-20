# fornax-howtos


The Fornax Initiative is a NASA Astrophysics Archives project to collaboratively among the three archives HEASARC, IRSA, and MAST, create cloud systems, cloud software, and cloud standards for the astronomical community.

The Fornax Science Console is a cloud compute system near to NASA data on the AWS cloud which provides a place where astronomers can do data-intensive research with reduced barriers. 
The Fornax Initiative provides increased compute, increased memory, increased ease of use by pre-installing astronomical software, increased reproducibility of big data results, and increased inclusion by removing some of these barriers to entry, tutorial notebooks, and documentation.

This repo houses a collection of hands-on, “how-to” notebooks for working effectively in the Fornax Science Console (ForSC). 
Tutorials in this repo focus on topics common to many Fornax users. 
These tutorials are designed for scientists. They emphasize reliable, reproducible patterns and performance-aware practices. 
For examples of how to do science workflows starting with an idea, working through the project, ending with a reproducible plot, see https://github.com/nasa-fornax/fornax-demo-notebooks.

## Documentation

The documentation of the Fornax Initiative are currently available at https://docs.fornax.sciencecloud.nasa.gov, while the source code for the documentation can be found in the [fornax-documentation repository](https://github.com/nasa-fornax/fornax-documentation/).

## Content contributing

In this repository, we follow the standard practice of the Scientific Python ecosystem and use Jupytext and MyST Markdown Notebooks.

Please visit the upstream documentation to learn more about the reasoning behind the choice. In summary, we chose MyST Markdown because we need a clear and human-readable format that makes version control, diffs, and collaborative reviews of code and narrative straightforward. It is also ideal for tutorials and CI-backed projects where reproducible, build-time execution of code ensures continued functionality.

We also highlight that you can easily have the same user experience in JupyterLab if these two dependencies are installed:

- `jupytext` library
- `jupyterlab-myst` JupyterLab extension

If you already have an ipynb file (called in yournotebook.ipynb in the command below), convert it to Markdown using the following command, and commit only the markdown file to the repo:

`jupytext --from notebook --to myst yournotebook.ipynb`
