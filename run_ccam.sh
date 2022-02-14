#!/bin/bash
#SBATCH --job-name=ccam
#SBATCH --nodes=5
#SBATCH --mem=40gb
#SBATCH --ntasks-per-node=20
#SBATCH --time=24:00:00

###############################################################
# This is the CCAM run script


###############################################################
# MODULES

module load openmpi/3.1.4-ofed45      # MPI
module load netcdf/4.3.3.1            # NetCDF
module load python/3.7.2              # Python

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
ids=1                                        # start day
ihs=0                                        # start hour
iye=2000                                     # end year
ime=12                                       # end month
ide=31                                       # end day
leap=1                                       # use leap days (0=off, 1=on)
ncountmax=12                                 # number of months before resubmit

name=ccam_${gridres}km                       # run name
if [[ $gridres = "-999." ]]; then
  gridtxt=$(echo "scale=1; 112.*90./$gridsize" | bc -l)
  name=`echo $name | sed "s/$gridres/$gridtxt"/g`
fi

# Note that turning off output should be done with ktc, ktc_surf and ktc_high
# Otherwise output will be saved but not post-processed
ncout=0                                      # standard output format (0=none, 1=all, 5=CTM, 7=basic)
ncsurf=3                                     # CORDEX output (0=none, 3=CORDEX)
nchigh=1                                     # high-frequency output (0=none, 1=lat/lon)
nctar=0                                      # TAR output files in OUTPUT directory (0=off, 1=on, 2=delete)
ktc=360                                      # standard output period (mins)
ktc_surf=60                                  # CORDEX file output period (mins) (0=off)
ktc_high=10                                  # high-frequency output period (mins)

minlat=-999.                                 # output min latitude (degrees) (-9999.=automatic)
maxlat=-999.                                 # output max latitude (degrees) (-999.=automatic)
minlon=-999.                                 # output min longitude (degrees) (-999.=automatic)
maxlon=-999.                                 # output max longitude (degrees) (-999.=automatic)
reqres=-999.                                 # required output resolution (degrees) (-999.=automatic)
outlevmode=0                                 # output mode for levels (0=pressure, 1=meters)
plevs="1000, 850, 700, 500, 300"             # output pressure levels (hPa) for outlevmode=0
mlevs="10, 20, 40, 80, 140, 200"             # output height levels (m) for outlevmode=1
dlevs="5, 10, 50, 100, 500, 1000, 5000"      # ocean depth levels (m)
drsmode=0                                    # DRS output (0=off, 1=on)
drshost=none                                 # Host GCM for DRS otput (e.g., ACCESS1-0)
drsensemble=none                             # Host GCM ensemble number for DRS output (e.g., r1i1p1f1)
drsdomain=none                               # DRS domain (e.g., AUS-50)

dmode=0                                      # simulation type (0=downscale spectral(GCM), 1=SST-only, 2=downscale spectral(CCAM), 3=SST-6hr, 4=veg-only, 5=postprocess-only, 6=Spectral(GCM)+SST )
cmip=cmip6                                   # CMIP scenario (cmip5 or cmip6)
rcp=ssp245                                   # RCP scenario (historic, RCP45 or RCP85,ssp126,ssp245,ssp370,ssp460,ssp585)
mlev=54                                      # number of model levels (27, 35, 54, 72, 108 or 144)
sib=1                                        # land surface (1=CABLE+varying landuse, 2=MODIS, 3=CABLE+SLI, 4=CABLE+const landuse)
aero=1                                       # aerosols (0=off, 1=prognostic)
conv=4                                       # convection (0=2014, 1=2015a, 2=2015b, 3=2017, 4=Mod2015a)
cloud=2                                      # cloud microphysics (0=liq+ice, 1=liq+ice+rain, 2=liq+ice+rain+snow+graupel)
rad=1                                        # radiation (0=SEA-ESF3, 1=SEA-ESF4)
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
# Host atmosphere for dmode=0, dmode=2, dmode=3 or dmode=6
# and soil data options

bcdom=ccam_eraint_                           # host file prefix for dmode=0, dmode=2 or dmode=3
bcdir=$HOME/ccaminstall/erai                 # host atmospheric data (dmode=0, dmode=2 or dmode=3)
bcsoil=1                                     # use climatology for initial soil moisture (1=climatology, 2=recycle)
bcsoilfile=none                              # soil data for recycling with bcsoil=2

###############################################################
# Sea Surface Temperature for dmode=1 or dmode=6

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
                   --gridsize $gridsize --mlev $mlev --iys $iys --ims $ims --ids $ids --ihs $ihs --iye $iye --ime $ime --ide $ide --leap $leap \
                   --ncountmax $ncountmax --ktc $ktc --minlat " $minlat" --maxlat " $maxlat" --minlon " $minlon" \
                   --maxlon " $maxlon" --reqres " $reqres" --outlevmode $outlevmode --plevs ${plevs// /} \
		   --mlevs ${mlevs// /} --dlevs ${dlevs// /} --dmode $dmode \
                   --sib $sib --aero $aero --conv $conv --cloud $cloud --rad $rad --bmix $bmix --mlo $mlo \
                   --casa $casa --ncout $ncout --nctar $nctar --ncsurf $ncsurf --ktc_surf $ktc_surf  \
		   --nchigh $nchigh --ktc_high $ktc_high \
                   --machinetype $machinetype --bcdom $bcdom --bcsoil $bcsoil \
                   --bcsoilfile $bcsoilfile \
                   --sstfile $sstfile --sstinit $sstinit --cmip $cmip --rcp $rcp --insdir $insdir --hdir $hdir \
                   --wdir $wdir --bcdir $bcdir --sstdir $sstdir --stdat $stdat \
                   --aeroemiss $aeroemiss --model $model --pcc2hist $pcc2hist --terread $terread --igbpveg $igbpveg \
                   --sibveg $sibveg --ocnbath $ocnbath --casafield $casafield \
		   --uclemparm $uclemparm --cableparm $cableparm --soilparm $soilparm --vegindex $vegindex \
		   --uservegfile $uservegfile --userlaifile $userlaifile \
		   --drsmode $drsmode --drshost $drshost --drsdomain $drsdomain \
		   --drsensemble $drsensemble

if [ $dmode -eq 5 ]; then
  restname=restart5.qm
else
  restname=restart.qm
fi

if [ "`cat $hdir/$restname`" == "True" ]; then
  echo 'Restarting script'
  rm $hdir/$restname
  sbatch $hdir/run_ccam.sh
elif [ "`cat $hdir/$restname`" == "Complete" ]; then
  echo 'CCAM simulation completed normally'
  rm $hdir/$restname
fi

exit
