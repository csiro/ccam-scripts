#!/bin/bash
#SBATCH --job-name=ccam
#SBATCH --mem=96gb
#SBATCH --ntasks-per-node=50
#SBATCH --cores-per-socket=10
#SBATCH --time=24:00:00

###############################################################
# This is the CCAM run script

###############################################################
# MODULES

module load mpt            # MPI
module load netcdf/4.3.3.1 # NetCDF
module load python         # Python

###############################################################
# Specify parameters

hdir=$HOME/ccaminstall/scripts/run_ccam      # script directory
wdir=$hdir/wdir                              # working directory
rstore=local                                 # remote machine name (local=no remote machine)
machinetype=0                                # machine type (0=generic, 1=cray)

nproc=$SLURM_NTASKS                          # number of processors

midlon=0.                                    # central longitude of domain
midlat=0.                                    # central latitude of domain
gridres=-999.                                # required resolution (km) of domain (-999.=global)
gridsize=96                                  # cubic grid size (e.g., 48, 72, 96, 144, 192, 288, 384, 576, 768, etc)

name=ccam_${gridres}km                       # run name

if [[ $gridres = "-999." ]]; then
  gridtxt=$(echo "scale=1; 112.*90./$gridsize" | bc -l)
  name=`echo $name | sed "s/$gridres/$gridtxt"/g`
fi

iys=2000                                     # start year
ims=1                                        # start month
iye=2000                                     # end year
ime=12                                       # end month
leap=1                                       # Use leap days (0=off, 1=on)
ncountmax=12                                 # Number of months before resubmit

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
casa=0                                       # CASA-CNP carbon cycle with prognostic LAI (0=off, 1=CASA-CNP, 2=CASA-CN+POP, 3=CASA-CN+POP+CLIM)

ncout=2                                      # standard output format (0=none, 1=CCAM, 2=CORDEX, 3=CTM, 4=Nearest)
nctar=1                                      # TAR output files in OUTPUT directory (0=off, 1=on, 2=delete)
ncsurf=0                                     # High-freq output (0=none, 1=lat/lon, 2=raw)
ktc_surf=10                                  # High-freq file output period (mins)

###############################################################
# Host atmosphere for dmode=0, dmode=2 or dmode=3

bcdom=ccam_eraint_                           # host file prefix for dmode=0, dmode=2 or dmode=3
bcdir=$HOME/ccaminstall/erai                 # host atmospheric data (dmode=0, dmode=2 or dmode=3)

###############################################################
# Sea Surface Temperature for dmode=1

sstfile=ACCESS1-0_RCP45_bcvc_osc_ots_santop96_18_0.0_0.0_1.0.nc # sst file for dmode=1
sstinit=$bcdir/$bcdom$iys$ims.nc                                # initial conditions file for dmode=1
sstdir=$HOME/ccaminstall/gcmsst                                 # SST data (dmode=1)

###############################################################
# Specify directories and executables

insdir=$HOME/ccaminstall                     # install directory
excdir=$insdir/scripts/run_ccam              # python code directory
stdat=$insdir/ccamdata                       # eigen and radiation datafiles
terread=$insdir/src/bin/terread
igbpveg=$insdir/src/bin/igbpveg
sibveg=$insdir/src/bin/sibveg
ocnbath=$insdir/src/bin/ocnbath
casafield=$insdir/src/bin/casafield
aeroemiss=$insdir/src/bin/aeroemiss
model=$insdir/src/bin/globpea
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
  echo 'Restarting script'
  sbatch $hdir/run_ccam.sh
elif [ "`cat $hdir/restart.qm`" == "Complete" ]; then
  echo 'CCAM simulation completed normally'
fi

exit
