---
authors:
- name: Jessica Krick
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.6
kernelspec:
  name: mast-tutorials
  display_name: mast-tutorials
  language: python
---

# Accessing HEASARC, IRSA, and MAST Data in the Cloud

## Learning Goals

By the end of this tutorial, you will be able to:

-   Understand cloud object storage basics.
-   Find each archive's up-to-date list of the data it hosts in the cloud.
-   Use `astroquery` to turn an archive search into cloud (S3) file locations for each of the three archives.
-   Open a FITS file directly from the cloud without downloading it, reading only the part you need.
-   Convert archive URLs to cloud locations and use command line tools for bulk downloads.

## Introduction

The three NASA astrophysics archives -- the High Energy Astrophysics Science Archive Research Center ([HEASARC](https://heasarc.gsfc.nasa.gov)), the NASA/IPAC Infrared Science Archive ([IRSA](https://irsa.ipac.caltech.edu)), and the Mikulski Archive for Space Telescopes ([MAST](https://archive.stsci.edu)) -- all host copies of their data holdings in Amazon Web Services (AWS) cloud storage through the [AWS Open Data program](https://registry.opendata.aws/).
The Fornax Science Console runs on AWS in the same region as most of these data, so reading files straight from cloud storage is usually faster than downloading them from the archives' on-premises servers.

Each archive already maintains its own, more detailed, cloud access tutorial.
This notebook does not replace them.
Instead, it teaches the concepts that are common to all three, shows that the access pattern is nearly identical across archives, and gives one short, working example per archive, all looking at the same supernova remnant.
Follow the links in each archive section to go deeper.

More data are moving to the cloud all the time, so this notebook does not list which datasets are available.
Each archive keeps its own up-to-date list, along with bucket names and access details:

-   **HEASARC:** [HEASARC data in the cloud](https://heasarc.gsfc.nasa.gov/docs/archive/cloud.html)
-   **IRSA:** [IRSA cloud data access](https://irsa.ipac.caltech.edu/cloud_access/)
-   **MAST:** [MAST public AWS data](https://outerspace.stsci.edu/display/MASTDOCS/Public+AWS+Data) and [STScI datasets on the AWS Open Data Registry](https://registry.opendata.aws/collab/stsci/)

The common pattern used throughout this notebook is:

1.  Search the archive with [astroquery](https://astroquery.readthedocs.io) as you normally would.
2.  Ask astroquery for the cloud (S3) location of the files instead of a download URL.
3.  Open the file directly from the cloud with [astropy](https://docs.astropy.org), reading only the bytes you need.

### Input

-   The sky coordinates of the supernova remnant Cassiopeia A (RA 23h23m24s, Dec +58d48m54s).

### Output

-   Three small image plots of Cassiopeia A, one per archive.

### Runtime

As of 2026-11-17, this notebook takes ~1 minute to run to completion on Fornax using the 'Small' server with 8GB RAM/ 2 CPU.
This runtime is heavily dependent on archive servers which means runtime will vary for users.

## Imports

This notebook uses the following packages:

-   `astropy` to open FITS files from the cloud and make cutouts
-   `astroquery` to search the archives and retrieve cloud file locations
-   `boto3` used by `astroquery.mast` for cloud access
-   `matplotlib` to display images
-   `reproject` to resample the three images onto the same patch of sky
-   `s3fs` to find files in an S3 bucket

:::{note}
The MAST example uses `astroquery` features that are newer than the latest release (0.4.11).
On Fornax, run this notebook with the **mast-tutorials** kernel, which already includes them.
Elsewhere, uncomment the install line below, which installs the needed development version of `astroquery`.
:::

```{code-cell} ipython3
# Uncomment the next line to install dependencies if needed.
# %pip install astropy boto3 matplotlib reproject s3fs "astroquery @ git+https://github.com/astropy/astroquery.git@bf791595eb35934957c27f6a576d0221fc9c51f5"
```

```{code-cell} ipython3
import json

import astropy.units as u
import matplotlib.pyplot as plt
import s3fs
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.visualization import simple_norm
from astropy.wcs import WCS
from astroquery.heasarc import Heasarc
from astroquery.ipac.irsa import Irsa
from astroquery.mast import Observations
from reproject import reproject_interp
```

## 1. Cloud Data Basics

### 1.1 Buckets, Objects, Keys, and Prefixes

AWS Simple Storage Service (S3) is an [object store](https://en.wikipedia.org/wiki/Object_storage).
Instead of a filesystem of directories and files, it has **buckets** that contain **objects**.
A few terms come up repeatedly:

-   **Bucket:** a top-level container, for example `nasa-heasarc`.
-   **Object:** a blob of data; for our purposes, a file.
-   **Key:** the unique name of an object within its bucket; analogous to a file's full path.
-   **Prefix:** the beginning of a key; analogous to a directory path.

A complete cloud location is written as an S3 URI: `s3://<bucket>/<key>`.
Most Python tools let you treat S3 like a regular filesystem, so `fits.open` and `pandas.read_parquet` accept S3 URIs in place of local paths.
The cloud connection itself is handled behind the scenes by libraries such as [s3fs](https://s3fs.readthedocs.io) and [fsspec](https://filesystem-spec.readthedocs.io).

### 1.2 Anonymous Access

All three archives' buckets are public, free to read, and require no credentials.
However, most tools look for AWS credentials by default and raise an error when none are found.
To avoid that, make an *anonymous* connection:

-   In Python, pass `anon=True` (for example, `s3fs.S3FileSystem(anon=True)` or `fits.open(uri, fsspec_kwargs={"anon": True})`).
-   On the command line, add `--no-sign-request` (for example, `aws s3 ls --no-sign-request s3://nasa-heasarc/`).

### 1.3 Why Read From the Cloud on Fornax

Fornax runs in the AWS `us-east-1` region, where most of these buckets also live.
Reading from them is fast, and with the right tools you can read *only part* of a file.
For FITS images, `astropy` does this when you open an S3 URI and index the HDU's `section` attribute instead of its `data` attribute: only the bytes for the requested pixels are fetched.
See [Obtaining subsets from cloud-hosted FITS files](https://docs.astropy.org/en/stable/io/fits/usage/cloud.html) for details.

:::{tip}
Partial reads only work on uncompressed files (or tile-compressed FITS).
A gzipped file such as `image.fits.gz` must be read in full, which is fine for small files but slow for large ones.
:::

### 1.4 The Example Target: Cassiopeia A

All three archive examples below look at the same object: Cassiopeia A (Cas A), the young remnant of a supernova whose light reached Earth roughly 350 years ago.
Together they show the remnant in the infrared (SPHEREx, from IRSA, and the James Webb Space Telescope (JWST), from MAST) and in X-rays (Chandra, from HEASARC).
So the three images can be compared directly, each example resamples its image onto the same 6 arcminute, north-up patch of sky defined below.

```{code-cell} ipython3
# Position of Cas A, used by all three archive searches
coord = SkyCoord("23h23m24s +58d48m54s")

# A shared 6 x 6 arcminute, north-up grid of 2 arcsecond pixels centered on Cas A.
# Each example resamples its image onto this grid so all three cover the same patch of sky.
grid_wcs = WCS({"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
                "CRVAL1": coord.ra.deg, "CRVAL2": coord.dec.deg,
                "CDELT1": -2 / 3600, "CDELT2": 2 / 3600,
                "CRPIX1": 90.5, "CRPIX2": 90.5, "NAXIS1": 180, "NAXIS2": 180})

# Cutouts are read a little larger than the grid so that images rotated relative to north still fill it
cutout_size = 9 * u.arcmin
```

## 2. IRSA

IRSA's image search, the Simple Image Access (SIA) service, returns a `cloud_access` column alongside the usual `access_url`.
Each entry is a small JSON string holding the bucket name, key, and region of that file.

```{code-cell} ipython3
# Search the SPHEREx Data Release 1 (DR1) collection for spectral images that cover Cas A
spherex_results = Irsa.query_sia(pos=(coord, 1 * u.arcsec), collection="spherex_dr1")

# SPHEREx has six detectors, each covering a different wavelength range.
# Keep the images from detector 6 (4.42 to 5.00 microns), where the remnant is brightest.
spherex_results = spherex_results[spherex_results["energy_bandpassname"] == "SPHEREx-D6"]

# Several D6 images cover Cas A; sort by observation start time (t_min) and use the most recent
spherex_results.sort("t_min")

# The cloud_access column is a JSON string; read the bucket and key of the most recent image
# and combine them into an S3 URI
cloud_info = json.loads(spherex_results["cloud_access"][-1])
spherex_uri = f"s3://{cloud_info['aws']['bucket_name']}/{cloud_info['aws']['key']}"
print(spherex_uri)

# Open the multi-extension FITS file directly from S3 (anonymously).
# Passing .section instead of .data means only the cutout pixels are transferred.
with fits.open(spherex_uri, fsspec_kwargs={"anon": True}) as hdul:
    # IMAGE holds the calibrated surface brightness (MJy/sr); its header's main WCS maps pixels to the sky
    sky_wcs = WCS(hdul["IMAGE"].header)
    image_cutout = Cutout2D(hdul["IMAGE"].section, position=coord, size=cutout_size, wcs=sky_wcs)

    # The alternate WCS "W" gives each pixel's wavelength, using the lookup table in the WCS-WAVE extension
    # (so it needs the open file, fobj). The sky distortion terms (SIP keywords A_*, B_*, AP_*, BP_*)
    # do not apply to wavelengths, so build it from a copy of the header without them.
    spectral_header = hdul["IMAGE"].header.copy()
    for key in [k for k in spectral_header if k.startswith(("A_", "B_", "AP_", "BP_"))]:
        del spectral_header[key]
    spectral_wcs = WCS(spectral_header, fobj=hdul, key="W")
    wavelength, bandwidth = spectral_wcs.pixel_to_world(*sky_wcs.world_to_pixel(coord))
print(f"Wavelength at the center of Cas A: {wavelength:.2f}")

# Resample the cutout onto the shared grid (SPHEREx images are rotated relative to north)
spherex_image, _ = reproject_interp((image_cutout.data, image_cutout.wcs), grid_wcs,
                                    shape_out=grid_wcs.array_shape)

# Display it with RA and Dec axes
ax = plt.subplot(projection=grid_wcs)
ax.imshow(spherex_image, origin="lower", cmap="gray",
          norm=simple_norm(spherex_image, stretch="asinh", percent=99.5))
ax.set_title(f"SPHEREx spectral image of Cas A at {wavelength:.2f} (IRSA)")
plt.show()
```

The full SPHEREx file holds several 2040 by 2040 pixel extensions, but only the cutout pixels from IMAGE were transferred.

This image shows how to access the data; it is not a science-ready image.
For example, it still includes the zodiacal light foreground (modeled in the file's ZODI extension), and pixels marked in the FLAGS extension have not been masked.

SPHEREx images are called *spectral* images because SPHEREx observes through filters whose wavelength changes across the detector, so each pixel sees the sky at a slightly different wavelength; the alternate WCS used above gives that wavelength.
As SPHEREx scans the sky, it observes every position many times at different wavelengths, and those observations together give a 0.75 to 5 micron spectrum at every point, including every position in this cutout.
See IRSA's [Introduction to SPHEREx spectral images](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro) for a tour of every extension in these files.

**Learn more:**

-   [IRSA cloud data access page](https://irsa.ipac.caltech.edu/cloud_access/): all buckets, prefixes, and how to map IRSA URLs to S3 keys.
-   [IRSA cloud access introduction tutorial](https://caltech-ipac.github.io/irsa-tutorials/cloud-access-intro): browsing buckets, image cutouts, and querying Parquet catalogs.
-   [Euclid cloud access tutorial](https://caltech-ipac.github.io/irsa-tutorials/euclid-cloud-access).
-   SPHEREx documentation: [SPHEREx at IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html) and the [SPHEREx archive documentation](https://caltech-ipac.github.io/spherex-archive-documentation/), which describes the data products, their processing, and what is needed to make them science ready.
-   [IRSA SPHEREx tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex): [data overview](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro), [spectral image cutouts](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts), [PSF models](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf), [source discovery tool](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo), [mosaic cube](https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic), and [HiPS all-sky cube](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube).

## 3. MAST

MAST data live in the `stpubdata` bucket.
In `astroquery.mast`, `Observations.list_cloud_datasets()` lists the missions and collections available in the cloud, and `Observations.get_cloud_uris()` converts a table of data products into S3 URIs.
If a product is not in the cloud, its URI is returned as `None`.

```{code-cell} ipython3
# List the missions and collections MAST currently hosts in the cloud
print("MAST cloud datasets:", Observations.list_cloud_datasets())

# Search for calibrated JWST NIRCam images of Cas A in the F444W (4.4 micron) filter
jwst_obs = Observations.query_criteria(coordinates=coord, radius=0.1 * u.arcmin, obs_collection="JWST",
                                       instrument_name="NIRCAM/IMAGE", filters="F444W", calib_level=3)

# More than one program may have observed Cas A; look at what came back
print(jwst_obs["obs_id", "proposal_id", "target_name", "t_exptime", "t_min"])

# Choose the most recent observation (t_min is the start time, as a Modified Julian Date)
jwst_obs.sort("t_min")
jwst_obs = jwst_obs[-1:]

# Keep only the final combined mosaic (I2D) product
jwst_products = Observations.filter_products(Observations.get_product_list(jwst_obs),
                                             productSubGroupDescription="I2D", calib_level=3)

# Ask MAST for the S3 URI of that product instead of a download URL
jwst_uris = Observations.get_cloud_uris(jwst_products)
print(jwst_uris[0])

# Open the mosaic directly from S3 and cut out the region around Cas A from the SCI extension.
# Passing .section instead of .data means only the cutout pixels are transferred.
with fits.open(jwst_uris[0], fsspec_kwargs={"anon": True}) as hdul:
    sci_hdu = hdul["SCI"]
    jwst_cutout = Cutout2D(
        sci_hdu.section, position=coord, size=cutout_size, wcs=WCS(sci_hdu.header)
    )

# Resample the cutout onto the shared grid (this mosaic is also rotated relative to north)
jwst_image, _ = reproject_interp((jwst_cutout.data, jwst_cutout.wcs), grid_wcs,
                                 shape_out=grid_wcs.array_shape)

# Display it with RA and Dec axes; corners outside the mosaic are shown in black
ax = plt.subplot(projection=grid_wcs)
ax.set_facecolor("black")
ax.imshow(jwst_image, origin="lower", cmap="gray",
          norm=simple_norm(jwst_image, stretch="asinh", percent=99.5))
ax.set_title("JWST NIRCam image of Cas A (MAST)")
plt.show()
```

JWST's sharp infrared view traces the remnant's shell of gas and dust in fine detail.
The mosaic file is about 1.5 GB because it also holds error, weight, and other extensions; reading only the science pixels needed for the cutout transferred about 165 MB.

**Learn more:**

-   [Accessing cloud-hosted data with astroquery](https://spacetelescope.github.io/mast_notebooks/notebooks/multi_mission/cloud_data_access/cloud_data_access.html): MAST's cloud tutorial, including TESS light curves with `lightkurve` and JWST spectra.
-   [`astroquery.mast` observation query documentation](https://astroquery.readthedocs.io/en/latest/mast/mast_obsquery.html).
-   [STScI datasets on the AWS Open Data Registry](https://registry.opendata.aws/collab/stsci/).

## 4. HEASARC

HEASARC data live in the `nasa-heasarc` bucket, and cosmic microwave background data from the Legacy Archive for Microwave Background Data Analysis ([LAMBDA](https://lambda.gsfc.nasa.gov)) live in `nasa-lambda`.
Both buckets are synchronized with the on-premises archive weekly, so the very newest data products may only be available from the HEASARC servers for a few days.
In `astroquery.heasarc`, `Heasarc.locate_data()` returns a table of data links for a set of observations.
Its `aws` column gives the S3 location of each observation's directory.

```{code-cell} ipython3
# Search the Chandra master observation catalog (chanmaster) for observations of Cas A,
# keep only those already in the public archive, and sort so the longest exposure is first
chandra_obs = Heasarc.query_region(coord, catalog="chanmaster", radius=5 * u.arcmin)
chandra_obs = chandra_obs[chandra_obs["status"] == "archived"]
chandra_obs.sort("exposure", reverse=True)

# Get the data links for the longest observation; the aws column is its S3 directory
chandra_links = Heasarc.locate_data(chandra_obs[:1], catalog_name="chanmaster")
obs_dir = chandra_links["aws"][0]
print(obs_dir)

# Use s3fs (anonymously) to find the full-field image file inside that directory
s3 = s3fs.S3FileSystem(anon=True)
image_key = s3.glob(f"{obs_dir}primary/*full_img2.fits*")[0]

# Open the image directly from S3 and resample it onto the shared grid.
# Chandra images are already north-up, so this mainly trims the image and changes the pixel size.
with fits.open(f"s3://{image_key}", fsspec_kwargs={"anon": True}) as hdul:
    chandra_image, _ = reproject_interp((hdul[0].data, WCS(hdul[0].header)), grid_wcs,
                                        shape_out=grid_wcs.array_shape)

# Display it with RA and Dec axes and a color bar
ax = plt.subplot(projection=grid_wcs)
im = ax.imshow(chandra_image, origin="lower", cmap="hot",
               norm=simple_norm(chandra_image, stretch="asinh", percent=99.5))
ax.set_title("Chandra ACIS image of Cas A (HEASARC)")
plt.colorbar(im, ax=ax, label="X-ray counts per Chandra image pixel")
plt.show()
```

This image is gzip-compressed (`.fits.gz`), so it is read in full rather than by section; at about 50 KB that is no problem.

**Other ways to reach HEASARC cloud data** (details on the [HEASARC data in the cloud](https://heasarc.gsfc.nasa.gov/docs/archive/cloud.html) page):

-   **From an archive URL:** HEASARC's buckets mirror its on-premises archive, so replace `https://heasarc.gsfc.nasa.gov/FTP/` at the start of a URL with `s3://nasa-heasarc/`.
    LAMBDA data work the same way with the `nasa-lambda` bucket, except that WMAP's `map` directory is named `wmap`.
-   **Bulk downloads:** use the [AWS command line](https://aws.amazon.com/cli/), already installed on Fornax, for example `aws s3 cp --recursive --no-sign-request s3://nasa-heasarc/<directory>/ <local directory>`.
    Check sizes first with `aws s3 ls`; a single Chandra observation directory can hold gigabytes.
-   **hark:** HEASARC's standalone [hark](https://heasarc.gsfc.nasa.gov/docs/archive/cloud/hark.html) tool searches observation tables offline and downloads directly from AWS; HEASARC recommends it for large downloads and pipelines.
-   **On Fornax:** the `nasa-heasarc` bucket is mounted read-only at `/archive-data/nasa-heasarc/`, so you can use `ls`, `cp`, and HEASoft tools (some of which need files on a regular filesystem) without downloading anything.

**Learn more:**

-   [HEASARC data in the cloud](https://heasarc.gsfc.nasa.gov/docs/archive/cloud.html): available missions, URL-to-S3 mapping, the AWS command line, and the `hark` download tool.
-   [HEASARC cloud tutorial notebook](https://heasarc.gsfc.nasa.gov/docs/archive/cloud/heasarc_cloud_tutorial.html): PyVO and `boto3` access to HEASARC and LAMBDA data.
-   [Using astroquery to download HEASARC observation data](https://heasarc.github.io/heasarc-tutorials/tutorials/heasarc_service_skills/heasarc_data/astroquery-data-acquisition.html): downloading whole observations from S3 with `Heasarc.download_data(..., host="aws")`.

## 5. Summary

All three archives follow the same recipe: search with `astroquery`, ask for the cloud location, then open the file with `fits.open(..., fsspec_kwargs={"anon": True})`.
Only the middle step differs:

| Archive | How to get the S3 location from `astroquery` |
| --- | --- |
| IRSA | `Irsa.query_sia(...)` returns a `cloud_access` column (JSON with bucket and key) |
| MAST | `Observations.get_cloud_uris(products)` returns S3 URIs |
| HEASARC | `Heasarc.locate_data(...)` returns an `aws` column (S3 directory for each observation) |

For more about data access options on Fornax, including the mounted buckets, see [Data Access from within Fornax](https://docs.fornax.sciencecloud.nasa.gov/data-access/).

## About this Notebook

-   **Authors:** Jessica Krick
-   **Updated:** 2026-11-17
-   **Contact:** For help with this notebook, please open a topic in the [Fornax Helpdesk](https://discourse.fornax.sciencecloud.nasa.gov/c/helpdesk).

### Acknowledgements

This notebook is built from the cloud access tutorials and documentation written by the IRSA, MAST, and HEASARC teams; see the references below.
Thanks to the MAST, HEASARC, and IRSA Fornax teams.

AI: This tutorial was generated using Claude (Anthropic's Claude Opus 5.5 model), working from the archive tutorials and documentation listed in the References below.

### References

This work made use of:

-   IRSA cloud access introduction: https://caltech-ipac.github.io/irsa-tutorials/cloud-access-intro
-   IRSA SPHEREx spectral images introduction: https://caltech-ipac.github.io/irsa-tutorials/spherex-intro
-   MAST cloud data access notebook: https://spacetelescope.github.io/mast_notebooks/notebooks/multi_mission/cloud_data_access/cloud_data_access.html
-   HEASARC data in the cloud: https://heasarc.gsfc.nasa.gov/docs/archive/cloud.html
-   HEASARC astroquery data acquisition notebook: https://heasarc.github.io/heasarc-tutorials/tutorials/heasarc_service_skills/heasarc_data/astroquery-data-acquisition.html
-   Astroquery: Ginsburg, Sipőcz, Brasseur et al. 2019, AJ, 157, 98 ([citation info](https://github.com/astropy/astroquery/blob/main/astroquery/CITATION))
-   Astropy: Astropy Collaboration 2013, 2018, 2022

