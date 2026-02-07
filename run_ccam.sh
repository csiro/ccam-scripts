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

module load openmpi      # MPI
module load netcdf       # NetCDF
module load python       # Python

###############################################################
# Specify parameters

hdir=$HOME/ccaminstall/scripts/run_ccam      # script directory
wdir=$hdir/wdir                              # working directory
machinetype=mpirun                           # machine type (mpirun, srun)
nproc=$SLURM_NTASKS                          # total number of processors
nnode=$SLURM_NTASKS_PER_NODE                 # number of processors per node

dmode=nudging_gcm                            # simulation type (nudging_gcm, sst_only, nudging_ccam, sst_6hour, generate_veg, postprocess, nudging_gcm_with_sst )

midlon=0.                                    # central longitude of domain
midlat=0.                                    # central latitude of domain
gridres=-999.                                # required resolution (km) of domain (-999.=global)
gridsize=96                                  # cubic grid size (e.g., 48, 72, 96, 144, 192, 288, 384, 576, 768, 1152, 1536, etc)
iys=2000                                     # start year
ims=1                                        # start month
ids=1                                        # start day
iye=2000                                     # end year
ime=12                                       # end month
ide=31                                       # end day
leap=auto                                    # calendar (auto, noleap, leap, 360)
ncountmax=12                                 # number of months before resubmit

name=ccam_${gridres}km                       # run name
if [[ $gridres = "-999." ]]; then
  gridtxt=$(echo "scale=1; 112.*90./$gridsize" | bc -l)
  name=`echo $name | sed "s/$gridres/$gridtxt"/g`
fi

# Output frequency.  Note ktc, ktc_surf and ktc_high only saves output.
# Post-processing requires ncout, ncsurf and nchigh to be enabled.
ktc=360                                      # standard output period (mins)
ktc_surf=60                                  # CORDEX file output period (mins) (0=off)
ktc_high=5                                   # high-frequency output period (mins) (0=off)
nctar=off                                    # TAR output files in OUTPUT directory (off, tar, delete)

# Post-processing.  Needed for data to be converted from the raw cubic grid to
# lat/lon.
ncout=off                                    # standard output (off, all, ctm, basic, tracer)
ncsurf=cordex                                # CORDEX output (off, cordex)
nchigh=off                                   # high-frequency output (off, latlon, shep)

# Output domain
minlat=-999.                                 # output min latitude (degrees) (-9999.=automatic)
maxlat=-999.                                 # output max latitude (degrees) (-999.=automatic)
minlon=-999.                                 # output min longitude (degrees) (-999.=automatic)
maxlon=-999.                                 # output max longitude (degrees) (-999.=automatic)
reqres=-999.                                 # required output resolution (degrees) (-999.=automatic)
outlevmode=pressure                          # output mode for levels (pressure, height, theta, combinations seperated by _ like pressure_meters)
plevs="1000, 850, 700, 500, 300"             # output pressure levels (hPa)
mlevs="10, 20, 40, 80, 140, 200"             # output height levels (m)
tlevs="280, 300, 320, 340, 360, 380, 400"    # output theta levels (K)
dlevs="5, 10, 50, 100, 500, 1000, 5000"      # ocean depth levels (m)

# DRS data.  default will source metadata from CCAM output.
drsmode=off                                  # DRS output (off, on)
drshost=default                              # Host GCM for DRS otput (e.g., ACCESS1-0)
drsensemble=default                          # Host GCM ensemble number for DRS output (e.g., r1i1p1f1)
drsdomain=generic                            # DRS domain (e.g., AUS-50)
drsproject=CORDEX                            # DRS project name (e.g., CORDEX)
model_id="CSIRO-CCAM-2506"                   # CCAM version name
contact="ccam@csiro.au"                      # contact email details
rcm_version_id="v1"                          # CCAM version number

# Simulation configuration options
cmip=cmip6                                   # CMIP scenario (cmip5 or cmip6)
rcp=ssp245                                   # RCP scenario (historic, RCP45 or RCP85,ssp126,ssp245,ssp370,ssp460,ssp585)
mlev=54                                      # number of model levels (27, 35, 54, 72, 108 or 144)
sib=cable_modis2020                          # land surface (cable_vary, cable_const, cable_modis2020, cable_modis2020_const)
aero=prognostic                              # aerosols (off, prognostic)
conv=2017                                    # convection (2014, 2015a, 2015b, 2017, Mod2015a, 2021, grell)
cldfrac=tiedtke                              # cloud fraction (smith, mcgregor, tiedtke)
cloud=lin                                    # cloud microphysics (liq_ice, liq_ice_rain, liq_ice_rain_snow_graupel, lin)
rad=SE4                                      # radiation (SE3, SE4, SE4lin)
rad_year=0                                   # special option for overriding radiation year (0=off)
bmix=tke_eps                                 # boundary layer (ri, tke_eps, hbg)
tke_timeave_length=0                         # special option for time averaging of TKE source terms (seconds) 0=off
mlo=dynamical                                # ocean (prescribed, dynamical)
casa=casa_cnp                                # CASA-CNP carbon cycle with prognostic LAI (off, casa_cnp, casa_cnp_pop)
tracer=off                                   # Tracer emission directory (off=disabled)

# User defined input datasets (e.g., for vegetation and urban)
uclemparm=default                            # urban parameter file (default for standard values)
cableparm=default                            # CABLE vegetation parameter file (default for standard values)
soilparm=default                             # soil parameter file (default for standard values)
vegindex=default                             # Define vegetation indices for user vegetation (default for standard values)
uservegfile=none                             # User specified vegetation map (none for no user file)
userlaifile=none                             # User specified LAI map (none for no user file)

###############################################################
# Host atmosphere for dmode=nudging_gcm, nudging_ccam, sst_6hour
# and soil data options

bcdom=ccam_eraint_                           # host file prefix for dmode=nudging_gcm, nudging_ccam or sst_6hour
bcdir=$HOME/ccaminstall/erai                 # host atmospheric data (dmode=nudging_gcm, nudging_ccam, sst_6hour)
bcsoil=climatology                           # use climatology for initial soil moisture (constant, climatology, recycle)
bcsoilfile=none                              # soil data for recycling with bcsoil=recycle

###############################################################
# Sea Surface Temperature for dmode=sst_only

sstfile=ACCESS1-0_RCP45_bcvc_osc_ots_santop96_18_0.0_0.0_1.0.nc # sst file for dmode=sst_only
sstinit=$bcdir/$bcdom$iys$ims.nc                                # initial conditions file for dmode=sst_only
sstdir=$HOME/ccaminstall/gcmsst                                 # SST data (dmode=sst_only)

###############################################################
# Specify directories and executables

insdir=$HOME/ccaminstall                     # install directory
excdir=$insdir/scripts/run_ccam              # location of run_ccam.py
stdat=$insdir/ccamdata                       # eigen and radiation datafiles
terread=$insdir/src/bin/terread
igbpveg=$insdir/src/bin/igbpveg
ocnbath=$insdir/src/bin/ocnbath
casafield=$insdir/src/bin/casafield
aeroemiss=$insdir/src/bin/aeroemiss
model=$insdir/src/bin/globpea
pcc2hist=$insdir/src/bin/pcc2hist

###############################################################

# Call python for simulation
python $excdir/run_ccam.py --name $name --nproc $nproc --nnode $nnode \
                   --midlon " $midlon" --midlat " $midlat" \
                   --gridres " $gridres" --gridsize $gridsize \
                   --mlev $mlev --iys $iys --ims $ims --ids $ids \
                   --iye $iye --ime $ime --ide $ide --leap $leap \
                   --ncountmax $ncountmax --dmode $dmode \
                   --ktc $ktc --ktc_surf $ktc_surf --ktc_high $ktc_high \
                   --sib $sib --aero $aero --conv $conv --cloud $cloud \
                   --rad $rad --bmix $bmix --mlo $mlo --casa $casa \
                   --cldfrac $cldfrac --tracer "$tracer" \
                   --tke_timeave_length $tke_timeave_length \
                   --rad_year $rad_year --machinetype $machinetype \
                   --bcdom $bcdom --bcsoil $bcsoil --bcsoilfile $bcsoilfile \
                   --sstfile $sstfile --sstinit $sstinit \
                   --cmip $cmip --rcp $rcp \
                   --insdir $insdir --hdir $hdir --wdir $wdir --bcdir $bcdir \
                   --sstdir $sstdir --stdat $stdat \
                   --aeroemiss $aeroemiss --model $model --terread $terread \
                   --igbpveg $igbpveg --ocnbath $ocnbath \
                   --casafield $casafield --pcc2hist $pcc2hist \
                   --uclemparm $uclemparm --cableparm $cableparm \
                   --soilparm $soilparm --vegindex $vegindex \
                   --uservegfile $uservegfile --userlaifile $userlaifile \
                   --minlat " $minlat" --maxlat " $maxlat" \
                   --minlon " $minlon" --maxlon " $maxlon" \
                   --reqres " $reqres" \
                   --outlevmode $outlevmode --plevs ${plevs// /} \
                   --mlevs ${mlevs// /} --tlevs ${tlevs// /} \
                   --dlevs ${dlevs// /} \
                   --ncout $ncout --nctar $nctar --ncsurf $ncsurf \
                   --nchigh $nchigh \
		   --drsmode $drsmode --drsdomain $drsdomain \
		   --drsensemble $drsensemble --model_id "$model_id" \
		   --contact "$contact" --rcm_version_id "$rcm_version_id" \
                   --drsproject "$drsproject" --drshost $drshost

# Process instructions from python

if [ $dmode == "postprocess" ]; then
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
