#!/bin/bash
#SBATCH --job-name=ccampp
#SBATCH --nodes=5
#SBATCH --mem=40gb
#SBATCH --ntasks-per-node=20
#SBATCH --time=24:00:00

###############################################################
# This is the CCAM run script


###############################################################
# MODULES

module load openmpi      # MPI
module load netcdf       # NetCDF
module load python       # Python

###############################################################
# Specify parameters

hdir=$HOME/ccaminstall/scripts/run_ccam      # script directory
wdir=$hdir/wdir                              # working directory
machinetype=mpirun                           # machine type (mpirun, srun)
nproc=$SLURM_NTASKS                          # number of processors
nnode=$SLURM_NTASKS_PER_NODE                 # number of processors per node

midlon=0.                                    # central longitude of domain
midlat=0.                                    # central latitude of domain
gridres=-999.                                # required resolution (km) of domain (-999.=global)
gridsize=96                                  # cubic grid size (e.g., 48, 72, 96, 144, 192, 288, 384, 576, 768, etc)
iys=2000                                     # start year
ims=1                                        # start month
ids=1                                        # start day
iye=2000                                     # end year
ime=12                                       # end month
ide=31                                       # end day
leap=leap                                    # use leap days (noleap, leap, 360)
ncountmax=12                                 # number of months before resubmit

name=ccam_${gridres}km                       # run name
if [[ $gridres = "-999." ]]; then
  gridtxt=$(echo "scale=1; 112.*90./$gridsize" | bc -l)
  name=`echo $name | sed "s/$gridres/$gridtxt"/g`
fi

# Note that turning off output should be done with ktc, ktc_surf and ktc_high
# Otherwise output will be saved but not post-processed
ncout=off                                    # standard output (off, all, ctm, basic, tracer)
ncsurf=cordex                                # CORDEX output (off, cordex)
nchigh=latlon                                # high-frequency output (off, latlon)
nctar=off                                    # TAR output files in OUTPUT directory (off, tar, delete)
ktc=360                                      # standard output period (mins)
ktc_surf=60                                  # CORDEX file output period (mins) (0=off)
ktc_high=10                                  # high-frequency output period (mins) (0=off)

minlat=-999.                                 # output min latitude (degrees) (-9999.=automatic)
maxlat=-999.                                 # output max latitude (degrees) (-999.=automatic)
minlon=-999.                                 # output min longitude (degrees) (-999.=automatic)
maxlon=-999.                                 # output max longitude (degrees) (-999.=automatic)
reqres=-999.                                 # required output resolution (degrees) (-999.=automatic)
outlevmode=pressure                          # output mode for levels (pressure, height, pressure_height)
plevs="1000, 850, 700, 500, 300"             # output pressure levels (hPa)
mlevs="10, 20, 40, 80, 140, 200"             # output height levels (m)
dlevs="5, 10, 50, 100, 500, 1000, 5000"      # ocean depth levels (m)

drsmode=off                                  # DRS output (off, on)
drshost=default                              # Host GCM for DRS otput (e.g., ACCESS1-0)
drsensemble=default                          # Host GCM ensemble number for DRS output (e.g., r1i1p1f1)
drsdomain=generic                            # DRS domain (e.g., AUS-50)
drsproject=CORDEX                            # DRS project name (e.g., CORDEX)
model_id="CSIRO-CCAM-2203"                   # CCAM version name
contact="ccam@csiro.au"                      # contact email details
rcm_version_id="v1"                          # CCAM version number

dmode=postprocess                            # simulation type (nudging_gcm, sst_only, nudging_ccam, sst_6hour, generate_veg, postprocess, nudging_gcm_with_sst )
cmip=cmip6                                   # CMIP scenario (cmip5 or cmip6)
rcp=ssp245                                   # RCP scenario (historic, RCP45 or RCP85,ssp126,ssp245,ssp370,ssp460,ssp585)

###############################################################
# Specify directories and executables

excdir=$insdir/scripts/run_ccam              # location of run_ccam.py
pcc2hist=$insdir/src/bin/pcc2hist

###############################################################

python $excdir/run_ccam.py --name $name --nproc $nproc \
                   --iys $iys --ims $ims --ids $ids --iye $iye --ime $ime --ide $ide --leap $leap \
                   --ncountmax $ncountmax --ktc $ktc --minlat " $minlat" --maxlat " $maxlat" --minlon " $minlon" \
                   --maxlon " $maxlon" --reqres " $reqres" --outlevmode $outlevmode --plevs ${plevs// /} \
		   --mlevs ${mlevs// /} --dlevs ${dlevs// /} --dmode $dmode \
                   --ncout $ncout --nctar $nctar --ncsurf $ncsurf --ktc_surf $ktc_surf  \
		   --nchigh $nchigh --ktc_high $ktc_high \
                   --machinetype $machinetype \
                   --cmip $cmip --rcp $rcp --hdir $hdir \
                   --wdir $wdir \
                   --pcc2hist $pcc2hist \
		   --drsmode $drsmode --drshost $drshost --drsdomain $drsdomain \
		   --drsensemble $drsensemble --model_id "$model_id" --contact "$contact" \
		   --rcm_version_id "$rcm_version_id" --drsproject "$drsproject" 


if [ "`cat $hdir/restart5.qm`" == "True" ]; then
  echo 'Restarting script'
  sbatch $hdir/postprocess_ccam.sh
elif [ "`cat $hdir/restart5.qm`" == "Complete" ]; then
  echo 'CCAM simulation completed normally'
fi

exit
