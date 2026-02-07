# **run_ccam.py**: a python script for automating CCAM

Original author: Mitchell Black
Current contact: Marcus Thatcher (Marcus.Thatcher@csiro.au)

The following describes a python script that has been developed for automating the Conformal Cubic Atmospheric Model (CCAM).


## Overview
------

A new user can start using CCAM in a few simple steps:

1. Install CCAM.  See [https://research.csiro.au/ccam/getting-started/instructions-for-installing-ccam/].
2. Download the scripts **run_ccam.py**
3. Execute **run_ccam.py** from the command line or using the shell script **run_ccam.sh**

## run_ccam.py
------

To read a manual page for **run_ccam.py**, a user can type the following on the comand line:

`python run_ccam.py -h`


## run_ccam.sh
------

To run CCAM, the user simply needs to change the arguments within **run_ccam.sh** and then submit the job for processing. For example,

`sbatch run_ccam.sh`

## Dependencies
------

**run_ccam.py** depends the NetCDF library.  It also requires the following executables

[https://github.com/csiro/ccam-terread]
[https://github.com/csiro/ccam-igbpveg]
[https://github.com/csiro/ccam-ocnbath]
[https://github.com/csiro/ccam-casafield]
[https://github.com/csiro/ccam-aeroemiss]
[https://github.com/csiro/ccam-ccam]
[https://github.com/csiro/ccam-pcc2hist]

