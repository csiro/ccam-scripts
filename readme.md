# **run_ccam.py**: a python script for automating CCAM

Author: [Mitchell Black](mailto:mitchell.black@csiro.au)

The following describes a python script that has been developed for automating the Conformal Cubic Atmospheric Model (CCAM).


## Overview
------

A new user can start using CCAM in a few simple steps:

1. [Install CCAM](https://bitbucket.csiro.au/users/bla375/repos/ccam_code/browse/ccam_install.md)
2. [Download the scripts **run_ccam.py**](https://bitbucket.csiro.au/users/bla375/repos/ccam_code/browse/run_ccam.py)
3. [Execute **run_ccam.py** from the command line or using the shell script **run_ccam.sh**](https://bitbucket.csiro.au/users/bla375/repos/ccam_code/browse/run_ccam.sh)
4. For an example of how to downscale ERA-Interim reanalysis data for SPARK or SWIFT, see [here](https://bitbucket.csiro.au/users/bla375/repos/ccam_code/browse/downscaling_example.md).

## run_ccam.py
------

An up-to-date version of **run_ccam.py** is available [here](https://bitbucket.csiro.au/users/bla375/repos/ccam_code/browse/run_ccam.py).

There is no need for the user to make changes to this code. All input arguments are provided via the command line.

To read a manual page for **run_ccam.py**, a user can type the following on the comand line:

`python run_ccam.py -h`


## run_ccam.sh
------

Previously, the CCAM model has been automated using a bash script similar to [pd60_run.sh](http://www.hpc.csiro.au/users/244528/ccaminstall/scripts/clim/pd60_run.sh).

Existing CCAM users who are familiar with this shell environment can use the new script **run_ccam.sh** as a shell interface for **run_ccam.py**.

An up-to-date version of **run_ccam.sh** is available [here](https://bitbucket.csiro.au/users/bla375/repos/ccam_code/browse/run_ccam.sh).

To run CCAM, the user simply needs to change the arguments within **run_ccam.sh** and then submit the job for processing. For example,

`sbatch run_ccam.sh`


