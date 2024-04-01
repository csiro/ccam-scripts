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
outlevmode=pressure                          # output mode for levels (pressure, height, theta, combinations seperated by _ like pressure_meters)
plevs="1000, 850, 700, 500, 300"             # output pressure levels (hPa)
mlevs="10, 20, 40, 80, 140, 200"             # output height levels (m)
tlevs="280, 300, 320, 340, 360, 380, 400"    # output theta levels (K)
dlevs="5, 10, 50, 100, 500, 1000, 5000"      # ocean depth levels (m)

drsmode=off                                  # DRS output (off, on)
drshost=default                              # Host GCM for DRS otput (e.g., ACCESS1-0)
drsensemble=default                          # Host GCM ensemble number for DRS output (e.g., r1i1p1f1)
drsdomain=generic                            # DRS domain (e.g., AUS-50)
drsproject=CORDEX                            # DRS project name (e.g., CORDEX)
model_id="CSIRO-CCAM-2401"                   # CCAM version name
contact="ccam@csiro.au"                      # contact email details
rcm_version_id="v1"                          # CCAM version number

dmode=nudging_gcm                            # simulation type (nudging_gcm, sst_only, nudging_ccam, sst_6hour, generate_veg, postprocess, nudging_gcm_with_sst )
cmip=cmip6                                   # CMIP scenario (cmip5 or cmip6)
rcp=ssp245                                   # RCP scenario (historic, RCP45 or RCP85,ssp126,ssp245,ssp370,ssp460,ssp585)
mlev=54                                      # number of model levels (27, 35, 54, 72, 108 or 144)
sib=cable_vary                               # land surface (cable_vary, modis, cable_sli, cable_const, cable_modis2020, cable_sli_modis2020)
aero=prognostic                              # aerosols (off, prognostic)
conv=Mod2015a                                # convection (2014, 2015a, 2015b, 2017, Mod2015a, 2021)
cldfrac=smith                                # cloud fraction (smith, mcgregor)
cloud=liq_ice_rain_snow_graupel              # cloud microphysics (liq_ice, liq_ice_rain, liq_ice_rain_snow_graupel, lin)
rad=SE4                                      # radiation (SE3, SE4, SE4lin)
rad_year=0                                   # radiation year (0=off)
bmix=tke_eps                                 # boundary layer (ri, tke_eps, hbg)
tke_timeave_length=0                         # time averaging of TKE source terms (seconds with 0=off)
mlo=prescribed                               # ocean (prescribed, dynamical)
casa=off                                     # CASA-CNP carbon cycle with prognostic LAI (off, casa_cnp, casa_cnp_pop)
tracer=off                                   # Tracer emission directory (off=disabled)

# User defined parameters.  Delete $hdir/vegdata to update.
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

python $excdir/run_ccam.py --name $name --nproc $nproc --nnode $nnode --midlon " $midlon" --midlat " $midlat" --gridres " $gridres" \
                   --gridsize $gridsize --mlev $mlev --iys $iys --ims $ims --ids $ids --iye $iye --ime $ime --ide $ide --leap $leap \
                   --ncountmax $ncountmax --ktc $ktc --minlat " $minlat" --maxlat " $maxlat" --minlon " $minlon" \
                   --maxlon " $maxlon" --reqres " $reqres" --outlevmode $outlevmode --plevs ${plevs// /} \
		   --mlevs ${mlevs// /} --tlevs ${tlevs// /} --dlevs ${dlevs// /} --dmode $dmode \
                   --sib $sib --aero $aero --conv $conv --cloud $cloud --rad $rad --bmix $bmix --mlo $mlo \
                   --casa $casa --cldfrac $cldfrac \
		   --ncout $ncout --nctar $nctar --ncsurf $ncsurf --ktc_surf $ktc_surf  \
		   --nchigh $nchigh --ktc_high $ktc_high \
                   --machinetype $machinetype --bcdom $bcdom --bcsoil $bcsoil \
                   --bcsoilfile $bcsoilfile \
                   --sstfile $sstfile --sstinit $sstinit --cmip $cmip --rcp $rcp --insdir $insdir --hdir $hdir \
                   --wdir $wdir --bcdir $bcdir --sstdir $sstdir --stdat $stdat \
                   --aeroemiss $aeroemiss --model $model --pcc2hist $pcc2hist --terread $terread --igbpveg $igbpveg \
                   --ocnbath $ocnbath --casafield $casafield \
		   --uclemparm $uclemparm --cableparm $cableparm --soilparm $soilparm --vegindex $vegindex \
		   --uservegfile $uservegfile --userlaifile $userlaifile \
		   --drsmode $drsmode --drshost $drshost --drsdomain $drsdomain \
		   --drsensemble $drsensemble --model_id "$model_id" --contact "$contact" \
		   --rcm_version_id "$rcm_version_id" --drsproject "$drsproject" \
		   --tke_timeave_length $tke_timeave_length --tracer "$tracer" --rad_year $rad_year


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
