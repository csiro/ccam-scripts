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
module load python/3.5.0   # Python

###############################################################
# Specify parameters

hdir=$HOME/ccaminstall/scripts/run_ccam      # script directory
wdir=$hdir/wdir                              # working directory
machinetype=0                                # machine type (0=mpirun, 1=srun)
nproc=$SLURM_NTASKS                          # number of processors
nnode=$SLURM_NTASKS_PER_NODE                 # number of processors per node

midlon=0.                                    # central longitude of domain
midlat=0.                                    # central latitude of domain
gridres=-999.                                # required resolution (km) of domain (-999.=global)
gridsize=96                                  # cubic grid size (e.g., 48, 72, 96, 144, 192, 288, 384, 576, 768, etc)
iys=2000                                     # start year
ims=1                                        # start month
iye=2000                                     # end year
ime=12                                       # end month
leap=1                                       # use leap days (0=off, 1=on)
ncountmax=12                                 # number of months before resubmit

name=ccam_${gridres}km                       # run name
if [[ $gridres = "-999." ]]; then
  gridtxt=$(echo "scale=1; 112.*90./$gridsize" | bc -l)
  name=`echo $name | sed "s/$gridres/$gridtxt"/g`
fi

ncout=2                                      # standard output format (0=none, 1=CCAM, 2=CORDEX, 3=CTM-tar, 4=Nearest, 5=CTM-raw, 6=CORDEX-surface)
nctar=1                                      # TAR output files in OUTPUT directory (0=off, 1=on, 2=delete)
ktc=360                                      # standard output period (mins)
minlat=-999.                                 # output min latitude (degrees) (-9999.=automatic)
maxlat=-999.                                 # output max latitude (degrees) (-999.=automatic)
minlon=-999.                                 # output min longitude (degrees) (-999.=automatic)
maxlon=-999.                                 # output max longitude (degrees) (-999.=automatic)
reqres=-999.                                 # required output resolution (degrees) (-999.=automatic)
outlevmode=0                                 # output mode for levels (0=pressure, 1=meters)
plevs="1000, 850, 700, 500, 300"             # output pressure levels (hPa) for outlevmode=0
mlevs="10, 20, 40, 80, 140, 200"             # output height levels (m) for outlevmode=1
dlevs="5, 10, 50, 100, 500, 1000, 5000"      # ocean depth levels (m)
ncsurf=0                                     # high-freq output (0=none, 1=lat/lon, 2=raw)
ktc_surf=10                                  # high-freq file output period (mins)

dmode=0                                      # simulation type (0=downscale spectral(GCM), 1=SST-only, 2=downscale spectral(CCAM), 3=SST-6hr, 4=veg-only )
cmip=cmip5                                   # CMIP scenario (cmip5 or cmip6)
rcp=RCP45                                    # RCP scenario (historic, RCP45 or RCP85,ssp126,ssp245,ssp370,ssp460,ssp585)
mlev=54                                      # number of model levels (27, 35, 54, 72, 108 or 144)
sib=1                                        # land surface (1=CABLE, 2=MODIS, 3=CABLE+SLI)
aero=1                                       # aerosols (0=off, 1=prognostic)
conv=4                                       # convection (0=2014, 1=2015a, 2=2015b, 3=2017, 4=Mod2015a)
cloud=2                                      # cloud microphysics (0=liq+ice, 1=liq+ice+rain, 2=liq+ice+rain+snow+graupel)
bmix=1                                       # boundary layer (0=Ri, 1=TKE-eps)
mlo=0                                        # ocean (0=Interpolated SSTs, 1=Dynamical ocean)
casa=0                                       # CASA-CNP carbon cycle with prognostic LAI (0=off, 1=CASA-CNP, 2=CASA-CN+POP, 3=CASA-CN+POP+CLIM)

# User defined parameters.  Delete $hdir/vegdata to update.
uclemparm=default                            # urban parameter file (default for standard values)
cableparm=default                            # CABLE vegetation parameter file (default for standard values)
soilparm=default                             # soil parameter file (default for standard values)
vegindex=default                             # Define vegetation indices for user vegetation (default for standard values)
uservegfile=none                             # User specified vegetation map (none for no user file)
userlaifile=none                             # User specified LAI map (none for no user file)

###############################################################
# Host atmosphere for dmode=0, dmode=2 or dmode=3
# and soil data options

bcdom=ccam_eraint_                           # host file prefix for dmode=0, dmode=2 or dmode=3
bcdir=$HOME/ccaminstall/erai                 # host atmospheric data (dmode=0, dmode=2 or dmode=3)
bcsoil=0                                     # use climatology for initial soil moisture (0=constant, 1=climatology, 2=recycle)
bcsoilfile=none                              # soil data for recycling with bcsoil=2

###############################################################
# Sea Surface Temperature for dmode=1

sstfile=ACCESS1-0_RCP45_bcvc_osc_ots_santop96_18_0.0_0.0_1.0.nc # sst file for dmode=1
sstinit=$bcdir/$bcdom$iys$ims.nc                                # initial conditions file for dmode=1
sstdir=$HOME/ccaminstall/gcmsst                                 # SST data (dmode=1)

###############################################################
# Specify directories and executables

insdir=$HOME/ccaminstall                     # install directory
excdir=$insdir/scripts/run_ccam              # location of run_ccam.py
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

python $excdir/run_ccam.py --name $name --nproc $nproc --nnode $nnode --midlon " $midlon" --midlat " $midlat" --gridres " $gridres" \
                   --gridsize $gridsize --mlev $mlev --iys $iys --ims $ims --iye $iye --ime $ime --leap $leap \
                   --ncountmax $ncountmax --ktc $ktc --minlat " $minlat" --maxlat " $maxlat" --minlon " $minlon" \
                   --maxlon " $maxlon" --reqres " $reqres" --outlevmode $outlevmode --plevs ${plevs// /} \
		   --mlevs ${mlevs// /} --dlevs ${dlevs// /} --dmode $dmode \
                   --sib $sib --aero $aero --conv $conv --cloud $cloud --bmix $bmix --mlo $mlo \
                   --casa $casa --ncout $ncout --nctar $nctar --ncsurf $ncsurf --ktc_surf $ktc_surf \
                   --machinetype $machinetype --bcdom $bcdom --bcsoil $bcsoil \
                   --bcsoilfile $bcsoilfile \
                   --sstfile $sstfile --sstinit $sstinit --cmip $cmip --rcp $rcp --insdir $insdir --hdir $hdir \
                   --wdir $wdir --bcdir $bcdir --sstdir $sstdir --stdat $stdat \
                   --aeroemiss $aeroemiss --model $model --pcc2hist $pcc2hist --terread $terread --igbpveg $igbpveg \
                   --sibveg $sibveg --ocnbath $ocnbath --casafield $casafield \
		   --uclemparm $uclemparm --cableparm $cableparm --soilparm $soilparm --vegindex $vegindex \
		   --uservegfile $uservegfile --userlaifile $userlaifile

if [ "`cat $hdir/restart.qm`" == "True" ]; then
  echo 'Restarting script'
  rm $hdir/restart.qm
  sbatch $hdir/run_ccam.sh
elif [ "`cat $hdir/restart.qm`" == "Complete" ]; then
  echo 'CCAM simulation completed normally'
  rm $hdir/restart.qm
fi

exit
