#!/bin/bash --login
#SBATCH --nodes=6
#SBATCH --ntasks-per-node=24
#SBATCH --ntasks-per-socket=10
#SBATCH --time=1:00:00
#SBATCH --mem=64gb
#SBATCH --job-name=ccamera50py
#SBATCH --account=director2045
#SBATCH -p debugq
#SBATCH --export=NONE

###############################################################
# MAGNUS MODULES

#module load PrgEnv-cray
#module load cray-mpich
#module load cray-netcdf/4.3.3.1
module load python/2.7.10
module load cray-netcdf

###############################################################
# This is the CCAM run script

echo 'Job '$SLURM_JOB_ID' started at '`date` | tee -a ~/job_monitoring.log
cd $SLURM_SUBMIT_DR

# Example grid sizes and processor numbers
# (NOTE: CCAM will automatically adjust the number of processors. Hence we
#  recommend setting nproc to the total number of avaliable CPUs)
# C48  nproc = 1, 2, 3, 6, 12, 24, 48, 72, 96, 144, 192, 216
# C72  nproc = 6, 12, 24, 48, 72, 96, 144, 192, 216, 288, 384
# C96  nproc = 48, 72, 96, 144, 192, 216, 288, 384, 432, 768, 864
# C144 nproc = 96, 144, 192, 216, 288, 384, 432, 768, 864, 1536, 1728
# C192 nproc = 192, 216, 288, 384, 432. 768, 864, 1536, 1728, 3072, 3456
# C288 nproc = 384, 432. 768, 864, 1536, 1728, 3072, 3456, 6144, 6912
# C384 nproc = 768, 864, 1536, 1728, 3072, 3456, 6144, 6912, 12288, 13824
# C576 nproc = 1536, 1728, 3072, 3456, 6144, 6912, 12288, 13824, 24576, 27648
# C768 nproc = 3072, 3456, 6144, 6912, 12288, 13824, 24576, 27648, 49152, 55296

###############################################################
# Specify parameters

insdir=/group/director2045/ccam              # install directory
#hdir=$insdir/scripts/scripts                 # script directory
hdir=/group/director2045/ccamera50_py        # script directory
wdir=$hdir/wdir                              # working directory
rstore=local                                 # remote machine name (local=no remote machine)
machinetype=1                                # machine type (0=generic, 1=cray)

nproc=$SLURM_NTASKS                          # number of processors

midlon=0.                                    # central longitude of domain
midlat=0.                                    # central latitude of domain
gridres=-999.                                # required resolution (km) of domain (-999.=global)
gridsize=96                                  # cubic grid size 

name=ccam_${gridres}km                       # run name

if [[ $gridres = "-999." ]]; then
  gridtxt=$(echo "scale=1; 112.*90./$gridsize" | bc -l)
  name=`echo $name | sed "s/$gridres/$gridtxt"/g`
fi

iys=2000                                     # start year
ims=1                                        # start month
iye=2000                                     # end year
ime=4                                        # end month
leap=1                                       # Use leap days (0=off, 1=on)
ncountmax=1                                  # Number of months before resubmit

ktc=360                                      # standard output period (mins)
minlat=-999.                                 # output min latitude (degrees) (-9999.=automatic)
maxlat=-999.                                 # output max latitude (degrees) (-999.=automatic)
minlon=-999.                                 # output min longitude (degrees) (-999.=automatic)
maxlon=-999.                                 # output max longitude (degrees) (-999.=automatic)
reqres=-999.                                 # required output resolution (degrees) (-999.=automatic)
outlevmode=0                                 # output mode for levels (0=pressure, 1=meters)
plevs="1000, 850, 700, 500, 300"             # output pressure levels (hPa) for outlevmode=0
mlevs="10, 20, 40, 80, 140, 200"             # output height levels (m) for outlevmode=1

dmode=0                                      # downscaling (0=spectral(GCM), 1=SST-only, 2=spectral(CCAM), 3=SST-6hr )
cmip=cmip5                                   # CMIP scenario (CMIP3 or CMIP5)
rcp=RCP45                                    # RCP scenario (historic, RCP45 or RCP85)
nstrength=0                                  # nudging strength (0=normal, 1=strong)
mlev=35                                      # number of model levels (27, 35, 54, 72, 108 or 144)
sib=1                                        # land surface (1=CABLE, 2=MODIS, 3=CABLE+SLI)
aero=1                                       # aerosols (0=off, 1=prognostic)
conv=1                                       # convection (0=2014, 1=2015a, 2=2015b, 3=2017)
cloud=2                                      # cloud microphysics (0=liq+ice, 1=liq+ice+rain, 2=liq+ice+rain+snow+graupel)
bmix=0                                       # boundary layer (0=Ri, 1=TKE-eps)
river=0                                      # river (0=off, 1=on)
mlo=0                                        # ocean (0=Interpolated SSTs, 1=Dynamical ocean)
casa=0                                       # CASA-CNP carbon cycle with prognostic LAI (0=off, 1=CASA-CNP, 2=CASA-CN+POP)

ncout=2                                      # standard output format (0=none, 1=CCAM, 2=CORDEX, 3=CTM)
nctar=1                                      # TAR output files in OUTPUT directory (0=off, 1=on)
ncsurf=0                                     # High-freq output (0=none, 1=lat/lon, 2=raw)
ktc_surf=10                                  # High-freq file output period (mins)

###############################################################
# Host atmosphere for dmode=0, dmode=2 or dmode=3

bcdom=ccam_eraint_                           # host file prefix for dmode=0, dmode=2 or dmode=3
bcdir=$insdir/ccamdata/eraint                # host atmospheric data (dmode=0, dmode=2 or dmode=3)

###############################################################
# Sea Surface Temperature for dmode=1

sstfile=ACCESS1-0_RCP45_bcvc_osc_ots_santop96_18_0.0_0.0_1.0.nc # sst file for dmode=1
sstinit=$bcdir/$bcdom$iys$ims.nc                                # initial conditions file for dmode=1
sstdir=$insdir/gcmsst                                           # SST data (dmode=1)

###############################################################
# Specify directories

excdir=$insdir/scripts/scripts        # python code directory
stdat=$insdir/ccamdata                # eigen and radiation datafiles

###############################################################
# Specify executables

terread=$insdir/src/bin/terread
igbpveg=$insdir/src/bin/igbpveg
sibveg=$insdir/src/bin/sibveg
ocnbath=$insdir/src/bin/ocnbath
casafield=$insdir/src/bin/casafield
aeroemiss=$insdir/src/bin/aeroemiss
model=$insdir/src/bin/globpea.1707f
pcc2hist=$insdir/src/bin/pcc2hist

###############################################################

python $excdir/run_ccam.py --name $name --nproc $nproc --midlon " $midlon" --midlat " $midlat" --gridres " $gridres" \
                   --gridsize $gridsize --mlev $mlev --iys $iys --ims $ims --iye $iye --ime $ime --leap $leap \
                   --ncountmax $ncountmax --ktc $ktc --minlat " $minlat" --maxlat " $maxlat" --minlon " $minlon" \
                   --maxlon " $maxlon" --reqres " $reqres" --outlevmode $outlevmode --plevs ${plevs// /} \
		   --mlevs ${mlevs// /} --dmode $dmode --nstrength $nstrength \
                   --sib $sib --aero $aero --conv $conv --cloud $cloud --bmix $bmix --river $river --mlo $mlo \
                   --casa $casa --ncout $ncout --nctar $nctar --ncsurf $ncsurf --ktc_surf $ktc_surf \
                   --machinetype $machinetype --bcdom $bcdom \
                   --sstfile $sstfile --sstinit $sstinit --cmip $cmip --rcp $rcp --insdir $insdir --hdir $hdir \
                   --wdir $wdir --rstore $rstore --bcdir $bcdir --sstdir $sstdir --stdat $stdat \
                   --aeroemiss $aeroemiss --model $model --pcc2hist $pcc2hist --terread $terread --igbpveg $igbpveg \
                   --sibveg $sibveg --ocnbath $ocnbath --casafield $casafield

if [ "`cat $hdir/restart.qm`" == "True" ]; then
  echo 'Completed job '$PBS_JOBID' at '`date` | tee -a ~/job_monitoring.log
  echo 'Restarting script '$PBS_JOBNAME' at month '`cat $hdir/year.qm`'. Submitted job:' | tee -a ~/job_monitoring.log
# Need to print which realm it's submitting as well as job number. Realm is inferred from job name.
  sbatch $hdir/run_ccam_magnus_debug.sh | tee -a ~/job_monitoring.log #Prints job ID of submitted job
elif [ "`cat $hdir/restart.qm`" == "Complete" ]; then
  echo 'CCAM simulation completed normally at '`date` | tee -a ~/job_monitoring.log
fi

exit
