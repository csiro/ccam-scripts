import os
import argparse
import sys
import subprocess
from calendar import monthrange

def main(inargs):
    "Run the CCAM model"

    global d
    d = vars(inargs)
    check_inargs()
    create_directories()
    calc_dt_out()
    set_ktc_surf()

    for mth in range(0, d['ncountmax']):
        print("Reading date and time")
        get_datetime()
        print("Updating land-use")
        check_surface_files()

        if ['dmode'] != 4:
            read_inv_schmidt()
            calc_res()
            calc_dt_mod()
            print("Prepare input files")
            prep_iofiles()
            print("Set parameters")
            set_mlev_params()
            config_initconds()
            set_nudging()
            set_downscaling()
            set_cloud()
            set_ocean()
            set_atmos()
            set_surfc()
            set_aeros()
            print("Create aerosol emissions")
            create_aeroemiss_file()
            create_sulffile_file()
            print("Create CCAM namelist and perform checks")
            prepare_ccam_infiles()
            create_input_file()
            check_correct_host()
            print("Run CCAM")
            run_model()
            print("Post-process CCAM output")
            post_process_output()

        print("Update simulation date and time")
        update_yearqm()

    restart_flag()


def check_inargs():
    "Check all inargs are specified and are internally consistent"

    args2check = ['name', 'nproc', 'nnode', 'midlon', 'midlat', 'gridres', 'gridsize', 'mlev',
                  'iys', 'ims', 'iye', 'ime', 'leap', 'ncountmax', 'ktc', 'minlat', 'maxlat',
                  'minlon', 'maxlon', 'reqres', 'outlevmode', 'plevs', 'mlevs', 'dlevs', 'dmode',
                  'sib', 'aero', 'conv', 'cloud', 'bmix', 'mlo', 'casa',
                  'ncout', 'nctar', 'ncsurf', 'ktc_surf', 'machinetype', 'bcdom', 'bcsoil',
                  'sstfile', 'sstinit', 'cmip', 'insdir', 'hdir', 'wdir', 'bcdir', 'sstdir',
                  'stdat', 'aeroemiss', 'model', 'pcc2hist', 'terread', 'igbpveg', 'sibveg',
                  'ocnbath', 'casafield', 'uclemparm', 'cableparm', 'vegindex', 'soilparm',
                  'uservegfile', 'userlaifile', 'bcsoilfile']

    for i in args2check:
        if not i in d.keys():
            print('Missing input argument --'+i)
            sys.exit(1)

    d['plevs'] = d['plevs'].replace(',', ', ')
    d['mlevs'] = d['mlevs'].replace(',', ', ')
    d['dlevs'] = d['dlevs'].replace(',', ', ')
    if d['outlevmode'] == 0:
        d['use_plevs'] = 'T'
        d['use_meters'] = 'F'
    elif d['outlevmode'] == 1:
        d['use_plevs'] = 'F'
        d['use_meters'] = 'T'
    else:
        raise ValueError("Invalid choice for outlevmode")

    if d['mlo'] == 0:
        d['use_depth'] = 'F'
    elif d['mlo'] == 1:
        d['use_depth'] = 'T'
    else:
        raise ValueError("Invalid choice for mlo")


    if d['gridres'] == -999.:
        d['gridres'] = 112.*90./d['gridsize']
        print(dict2str('Update gridres to {gridres}'))
        if d['minlat'] == -999.:
            d['minlat'] = -90.
        if d['maxlat'] == -999.:
            d['maxlat'] = 90.
        if d['minlon'] == -999.:
            d['minlon'] = 0.
        if d['maxlon'] == -999.:
            d['maxlon'] = 360.

    if d['uclemparm'] == 'default':
        d['uclemparm'] = ''
    if d['cableparm'] == 'default':
        d['cableparm'] = ''
    if d['soilparm'] == 'default':
        d['soilparm'] = ''
    if d['vegindex'] == 'default':
        d['vegindex'] = ''
    if d['uservegfile'] == 'none':
        d['uservegfile'] = ''
    if d['userlaifile'] == 'none':
        d['userlaifile'] = ''


def create_directories():
    "Create output directories and go to working directory"

    dirname = dict2str('{hdir}')
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    os.chdir(dirname)

    for dirname in ['daily', 'OUTPUT', 'RESTART', 'vegdata']:
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

    run_cmdline('rm -f {hdir}/restart.qm')

    dirname = dict2str('{wdir}')
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    os.chdir(dirname)

def calc_dt_out():
    "Calculate model output timestep"

    d['dtout'] = 360  # raw cc output frequency (mins)

    if d['ncout'] == 3:
        d['dtout'] = 60 # need hourly output for CTM

    if d['ncout'] == 5:
        d['dtout'] = 60 # need hourly output for CTM

    if d['ktc'] < d['dtout']:
        d['dtout'] = d['ktc']


def set_ktc_surf():
    "Set tstep for high-frequency output"

    if d['ncsurf'] == 0:
        d['ktc_surf'] = d['dtout']


def get_datetime():
    "Determine relevant dates and timesteps for running model"

    # Load year.qm with current simulation year:
    fname = dict2str('{hdir}/year.qm')
    if os.path.exists(fname):
        yyyydd = open(fname).read()
        d['iyr'] = int(yyyydd[0:4])
        d['imth'] = int(yyyydd[4:6])
        print("ATTENTION:")
        print(dict2str("Simulation start date taken from {hdir}/year.qm"))
        print("Start date: "+str(d['iyr'])+mon_2digit(d['imth'])+'01')
        print("If this is the incorrect start date, please delete year.qm")
    else:
        d['iyr'] = d['iys']
        d['imth'] = d['ims']

    # Abort run at finish year:
    sdate = d['iyr']*100 +d['imth']
    edate = d['iye']*100 +d['ime']

    if sdate > edate:
        raise ValueError("CCAM simulation already completed. Delete year.qm to restart.")

    iyr = d['iyr']
    imth = d['imth']

    #if iyr < 2010:
    #    print("Changing emission scenario to historic")
    #    d['rcp'] = 'historic'

    # Decade start and end:
    d['ddyear'] = int(int(iyr/10)*10)
    d['deyear'] = int(d['ddyear'] + 9)

    # Calculate previous month:
    if imth == 1:
        d['imthlst'] = '12'
        d['iyrlst'] = iyr-1
    else:
        d['imthlst'] = imth-1
        d['iyrlst'] = iyr

    # Calculate the next month:
    if imth == 12:
        d['imthnxt'] = 1
        d['iyrnxt'] = iyr+1
    else:
        d['imthnxt'] = imth+1
        d['iyrnxt'] = iyr

    # Calculate the next next month (+2):
    if imth > 10:
        d['imthnxtb'] = imth-10
        d['iyrnxtb'] = iyr + 1
    else:
        d['imthnxtb'] = imth+2
        d['iyrnxtb'] = iyr

    d['imthlst_2digit'] = mon_2digit(d['imthlst'])
    d['imth_2digit'] = mon_2digit(d['imth'])
    d['imthnxt_2digit'] = mon_2digit(d['imthnxt'])
    d['imthnxtb_2digit'] = mon_2digit(d['imthnxtb'])

   # Calculate number of days in current month:
    d['ndays'] = monthrange(iyr, imth)[1]

    if (imth == 2) and (d['leap'] == 0):
        d['ndays'] = 28 #leap year turned off


def check_surface_files():
    "Ensure surface datasets exist"

    d['domain'] = dict2str('{gridsize}_{midlon}_{midlat}_{gridres}km')

    if not os.path.exists('custom.qm'):
        run_cable_all()
    else:
        filename = open('custom.qm', 'r')
        testfail = False
        if dict2str('{uclemparm}\n') != filename.readline():
            testfail = True
        if dict2str('{cableparm}\n') != filename.readline():
            testfail = True
        if dict2str('{soilparm}\n') != filename.readline():
            testfail = True
        if dict2str('{vegindex}\n') != filename.readline():
            testfail = True
        if dict2str('{uservegfile}\n') != filename.readline():
            testfail = True
        if dict2str('{userlaifile}\n') != filename.readline():
            testfail = True
        filename.close()
        if testfail is True:
            run_cable_all()

    for fname in ['topout', 'bath', 'casa']:
        if not os.path.exists(dict2str('{hdir}/vegdata/'+fname+'{domain}')):
            run_cable_all()

    for mon in range(1, 13):
        if d['cmip'] == "cmip5":
            fname = dict2str('{hdir}/vegdata/veg{domain}.'+mon_2digit(mon))
        else:
            fname = dict2str('{hdir}/vegdata/veg{domain}.{iyr}.'+mon_2digit(mon))
        if not os.path.exists(fname):
            run_cable_land()
        if check_correct_landuse(fname) is True:
            run_cable_land()


def run_cable_all():
    "Generate topography and land-use files for CCAM"

    run_topo()
    run_land()
    run_ocean()
    run_carbon()
    run_cmdline('mv -f topout{domain} {hdir}/vegdata')
    run_cmdline('mv -f veg{domain}* {hdir}/vegdata')
    run_cmdline('mv -f bath{domain} {hdir}/vegdata')
    run_cmdline('mv -f casa{domain} {hdir}/vegdata')
    update_custom_land()


def run_cable_land():
    "Generate topography and land-use files for CCAM"

    run_cmdline("ln -s {hdir}/vegdata/topout{domain} .")
    run_land()
    run_cmdline('rm -f topout{domain}')
    run_cmdline('mv -f veg{domain}* {hdir}/vegdata')
    update_custom_land()


def update_custom_land():

    filename = open('custom.qm', 'w+')
    filename.write(dict2str('{uclemparm}\n'))
    filename.write(dict2str('{cableparm}\n'))
    filename.write(dict2str('{soilparm}\n'))
    filename.write(dict2str('{vegindex}\n'))
    filename.write(dict2str('{uservegfile}\n'))
    filename.write(dict2str('{userlaifile}\n'))
    filename.close()


def run_topo():

    print("Generating topography file")
    d['inv_schmidt'] = float(d['gridres']) * float(d['gridsize']) / (112. * 90.)
    write2file('top.nml', top_template(), mode='w+')
    if d['machinetype'] == 1:
        run_cmdline('srun -n 1 {terread} < top.nml > terread.log')
    else:
        run_cmdline('{terread} < top.nml > terread.log')
    xtest = (subprocess.getoutput('grep -o "terread completed successfully" terread.log')
             == "terread completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running terread. Check terread.log"))

def run_land():

    #default will disable change_landuse
    d['change_landuse'] = dict2str('')

    if d['sib'] == 2:
        print("Generating MODIS land-use data")
        write2file('sibveg.nml', sibveg_template(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n 1 {sibveg} -s 1000 < sibveg.nml > sibveg.log')
        else:
            run_cmdline('{sibveg} -s 1000 < sibveg.nml > sibveg.log')
        xtest = (subprocess.getoutput('grep -o "sibveg completed successfully" sibveg.log')
                 == "sibveg completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured while running sibveg. Check sibveg.log"))
        run_cmdline('mv -f topsib{domain} topout{domain}')
    else:
        print("Generating CABLE land-use data")
        if d['cmip'] == "cmip6":
            if d['iyr'] < 2015:
                d['change_landuse'] = dict2str('{stdat}/{cmip}/cmip/multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-landState-base-2-1-h_gn_0850-2015.nc')
            else:
                if d['rcp'] == "ssp126":
                    d['rcplabel'] = "IMAGE"
                elif d['rcp'] == "ssp245":
                    d['rcplabel'] = "MESSAGE"
                elif d['rcp'] == "ssp370":
                    d['rcplabel'] = "AIM"
                elif d['rcp'] == "ssp460":
                    d['rcplabel'] = "GCAM"
                elif d['rcp'] == "ssp585":
                    d['rcplabel'] = "MAGPIE"
                else:
                    raise ValueError(dict2str("Invalid choice for rcp"))
                d['change_landuse'] = dict2str('{stdat}/{cmip}/{rcp}/multiple-states_input4MIPs_landState_ScenarioMIP_UofMD-{rcplabel}-{rcp}-2-1-f_gn_2015-2100.nc')
        write2file('igbpveg.nml', igbpveg_template(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" KMP_STACKSIZE=1024m srun -n 1 -c {nnode} {igbpveg} -s 5000 < igbpveg.nml > igbpveg.log')
        else:
            run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" KMP_STACKSIZE=1024m {igbpveg} -s 5000 < igbpveg.nml > igbpveg.log')
        xtest = (subprocess.getoutput('grep -o "igbpveg completed successfully" igbpveg.log') == "igbpveg completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured while running igbpveg.  Check igbpveg.log for details"))
        run_cmdline('mv -f topsib{domain} topout{domain}')


def run_ocean():

    print("Processing bathymetry data")
    write2file('ocnbath.nml', ocnbath_template(), mode='w+')
    if d['machinetype'] == 1:
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" KMP_STACKSIZE=1024m srun -n 1 {ocnbath} -s 5000 < ocnbath.nml > ocnbath.log')
    else:
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" KMP_STACKSIZE=1024m {ocnbath} -s 5000 < ocnbath.nml > ocnbath.log')
    xtest = (subprocess.getoutput('grep -o "ocnbath completed successfully" ocnbath.log')
             == "ocnbath completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running ocnbath. Check ocnbath.log"))


def run_carbon():

    print("Processing CASA data")
    if d['machinetype'] == 1:
        run_cmdline('srun -n 1 {casafield} -t topout{domain} -i {insdir}/vegin/casaNP_gridinfo_1dx1d.nc -o casa{domain} > casafield.log')
    else:
        run_cmdline('{casafield} -t topout{domain} -i {insdir}/vegin/casaNP_gridinfo_1dx1d.nc -o casa{domain} > casafield.log')
    xtest = (subprocess.getoutput('grep -o "casafield completed successfully" casafield.log')
             == "casafield completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running casafield.  Check casafield.log for details"))


def read_inv_schmidt():
    "Read inverse schmidt value from NetCDF topo file and calculate grid resolution"

    topofile = dict2str('{hdir}/vegdata/topout{domain}')

    d['inv_schmidt'] = float(subprocess.getoutput('ncdump -c '+topofile+' | grep schmidt | cut -d"=" -f2 | cut -d";" -f1 | sed "s/f//g" | sed "s/ //g"'))
    d['gridsize'] = int(subprocess.getoutput('ncdump -c '+topofile+' | grep longitude | head -1 | cut -d"=" -f2 | cut -d";" -f1 | sed "s/ //g"'))
    d['lon0'] = float(subprocess.getoutput('ncdump -c '+topofile+' | grep lon0 | cut -d"=" -f2 | cut -d";" -f1 | sed "s/f//g" | sed "s/ //g"'))
    d['lat0'] = float(subprocess.getoutput('ncdump -c '+topofile+' | grep lat0 | cut -d"=" -f2 | cut -d";" -f1 | sed "s/f//g" | sed "s/ //g"'))

def calc_res():
    "Calculate resolution for high resolution area"

    gridres_m = d['gridres']*1000. # GRIDRES IN UNITS OF METERS

    res = d['reqres']
    if res == -999.:
        res = gridres_m/112000.

    if d['minlat'] == -999.:
        d['minlat'] = d['midlat']-gridres_m*d['gridsize']/200000.

    if d['maxlat'] == -999.:
        d['maxlat'] = d['midlat']+gridres_m*d['gridsize']/200000.

    if d['minlon'] == -999.:
        d['minlon'] = d['midlon']-gridres_m*d['gridsize']/200000.

    if d['maxlon'] == -999.:
        d['maxlon'] = d['midlon']+gridres_m*d['gridsize']/200000.

    d['gridres_m'] = gridres_m
    d['res'] = res

    # CHECK
    # 1. Should reqres be an input argument - how does this then relate to the pre-defind
    # inv_schmidt?
    # 2. Note above I have divided by 112000. The original code had 100000.


def calc_dt_mod():
    """Calculate model timestep.
     dt is a function of dx; dt out and ktc_surf must be integer multiples of dt"""

    # define dictionary of pre-defined dx (mtrs) : dt (sec) relationships
    d_dxdt = {60000:1200, 45000:900, 36000:720,
              30000:600, 22500:450, 20000:400, 18000:360,
              15000:300, 12000:240, 11250:225, 10000:200, 9000:180,
              7500:150, 7200:144, 6000:120, 5000:100, 4500:90, 4000:80,
              3750:75, 3600:72, 3000:60, 2500:50, 2400:48, 2250:45,
              2000:40, 1800:36, 1500:30, 1250:25, 1200:24,
              1000:20, 900:18, 800:16, 750:15, 600:12,
              500:10, 450:9, 400:8, 300:6,
              250:5, 200:4, 150:3, 100:2, 50:1}

    # determine dt based on dx, dtout and ktc_surf
    for dx in sorted(d_dxdt):
        if (d['gridres_m'] >= dx) and (60 * d['dtout'] % d_dxdt[dx] == 0) and (60 * d['ktc_surf'] % d_dxdt[dx] == 0):
            d['dt'] = d_dxdt[dx]

    if d['gridres_m'] < 50:
        raise ValueError("Minimum grid resolution of 50m has been exceeded")

    #if ( d['dtout'] % dt != 0 ):
    #    raise ValueError, "dtout must be a multiple of dt" # CHECK: Original code has dtout must be a multiple of dt/60
    #Is this not redundant code given that dt will be 1, above.

    if d['ktc'] % d['dtout'] != 0:
        raise ValueError("ktc must be a multiple of dtout")

    if d['ncsurf'] != 0:
        if d['dtout'] % d['ktc_surf'] != 0: # This order is different to original code
            raise ValueError("dtout must be a multiple of ktc_surf")


def prep_iofiles():
    "Prepare input and output files"

    # Define restart file:
    d['ifile'] = dict2str('Rest{name}.{iyrlst}{imthlst_2digit}')
    d['ofile'] = dict2str('{name}.{iyr}{imth_2digit}')

    # Define host model fields:
    d['mesonest'] = dict2str('{bcdom}{iyr}{imth_2digit}.nc')
    fpath = dict2str('{bcdir}/{mesonest}')

    if not os.path.exists(fpath):
        d['mesonest'] = dict2str('{bcdom}.{iyr}{imth_2digit}.nc')
        fpath = dict2str('{bcdir}/{mesonest}')

    if not os.path.exists(fpath):
        d['mesonest'] = dict2str('{bcdom}_{iyr}{imth_2digit}.nc')
        fpath = dict2str('{bcdir}/{mesonest}')

    if not os.path.exists(fpath):
        d['mesonest'] = dict2str('{bcdom}{iyr}{imth_2digit}')
        fpath = dict2str('{bcdir}/{mesonest}.tar')

    if not os.path.exists(fpath):
        d['mesonest'] = dict2str('{bcdom}.{iyr}{imth_2digit}')
        fpath = dict2str('{bcdir}/{mesonest}.tar')

    if not os.path.exists(fpath):
        d['mesonest'] = dict2str('{bcdom}_{iyr}{imth_2digit}')
        fpath = dict2str('{bcdir}/{mesonest}.tar')

    if not os.path.exists(fpath):
        d['mesonest'] = dict2str('{bcdom}.{iyr}{imth_2digit}')
        fpath = dict2str('{bcdir}/{mesonest}')

    if not os.path.exists(fpath):
        if not os.path.exists(fpath+'.000000'):
            d['mesonest'] = dict2str('{bcdom}{iyr}{imth_2digit}')
            fpath = dict2str('{bcdir}/{mesonest}')

    # Define restart file:
    d['restfile'] = dict2str('Rest{name}.{iyr}{imth_2digit}')

    # Define ozone infile:
    if d['cmip'] == "cmip5":
        if d['rcp'] == "historic" or d['iyr'] < 2005:
            d['ozone'] = dict2str('{stdat}/{cmip}/historic/pp.Ozone_CMIP5_ACC_SPARC_{ddyear}-{deyear}_historic_T3M_O3.nc')
        else:
            d['ozone'] = dict2str('{stdat}/{cmip}/{rcp}/pp.Ozone_CMIP5_ACC_SPARC_{ddyear}-{deyear}_{rcp}_T3M_O3.nc')
    else:
        if d['iyr'] < 1900:
            d['ozone'] = dict2str('{stdat}/{cmip}/cmip/vmro3_input4MIPs_ozone_CMIP_UReading-CCMI-1-0_gn_185001-189912.nc')
        elif d['iyr'] < 1950:
            d['ozone'] = dict2str('{stdat}/{cmip}/cmip/vmro3_input4MIPs_ozone_CMIP_UReading-CCMI-1-0_gn_190001-194912.nc')
        elif d['iyr'] < 2000:
            d['ozone'] = dict2str('{stdat}/{cmip}/cmip/vmro3_input4MIPs_ozone_CMIP_UReading-CCMI-1-0_gn_195001-199912.nc')
        elif d['iyr'] < 2015:
            d['ozone'] = dict2str('{stdat}/{cmip}/cmip/vmro3_input4MIPs_ozone_CMIP_UReading-CCMI-1-0_gn_200001-201412.nc')
        elif d['iyr'] < 2050:
            d['ozone'] = dict2str('{stdat}/{cmip}/{rcp}/vmro3_input4MIPs_ozone_ScenarioMIP_UReading-CCMI-{rcp}-1-0_gn_201501-204912.nc')
        else:
            d['ozone'] = dict2str('{stdat}/{cmip}/{rcp}/vmro3_input4MIPs_ozone_ScenarioMIP_UReading-CCMI-{rcp}-1-0_gn_205001-209912.nc')


    # Define CO2 infile:
    if d['cmip'] == "cmip5":
        d['co2file'] = dict2str('{stdat}/{cmip}/{rcp}_MIDYR_CONC.DAT')
        d['ch4file'] = ""
        d['n2ofile'] = ""
        d['cfc11file'] = ""
        d['cfc12file'] = ""
        d['cfc113file'] = ""
        d['hcfc22file'] = ""
        d['solarfile'] = ""
        for fname in [d['ozone'], d['co2file']]:
            check_file_exists(fname)
    else:
        if d['iyr'] < 2015:
            d['co2file'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-carbon-dioxide-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
            d['ch4file'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-methane-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
            d['n2ofile'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-nitrous-oxide-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
            d['cfc11file'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-cfc11-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
            d['cfc12file'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-cfc12-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
            d['cfc113file'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-cfc113-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
            d['hcfc22file'] = dict2str('{stdat}/{cmip}/cmip/mole-fraction-of-hcfc22-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_000001-201412.nc')
        else:
            if d['rcp'] == "ssp126":
                d['rcplabel'] = "IMAGE"
            elif d['rcp'] == "ssp245":
                d['rcplabel'] = "MESSAGE-GLOBIOM"
            elif d['rcp'] == "ssp370":
                d['rcplabel'] = "AIM"
            elif d['rcp'] == "ssp460":
                d['rcplabel'] = "GCAM4"
            elif d['rcp'] == "ssp585":
                d['rcplabel'] = "REMIND-MAGPIE"
            else:
                raise ValueError(dict2str("Invalid choice for rcp"))

            d['co2file'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-carbon-dioxide-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')
            d['ch4file'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-methane-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')
            d['n2ofile'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-nitrous-oxide-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')
            d['cfc11file'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-cfc11-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')
            d['cfc12file'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-cfc12-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')
            d['cfc113file'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-cfc113-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')
            d['hcfc22file'] = dict2str('{stdat}/{cmip}/{rcp}/mole-fraction-of-hcfc22-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{rcplabel}-{rcp}-1-2-1_gr1-GMNHSH_201501-250012.nc')

        d['solarfile'] = dict2str('{stdat}/{cmip}/solarforcing-ref-mon_input4MIPs_solar_CMIP_SOLARIS-HEPPA-3-2_gn_185001-229912.nc')
        for fname in [d['ozone'], d['co2file'], d['ch4file'], d['n2ofile'], d['cfc11file'],
                      d['cfc12file'], d['cfc113file'], d['hcfc22file'], d['solarfile']]:
            check_file_exists(fname)


def set_mlev_params():
    "Set the parameters related to the number of model levels"

    d_mlev_eigenv = {27:"eigenv27-10.300", 35:"eigenv.35b", 54:"eigenv.54b", 72:"eigenv.72b",
                     108:"eigenv.108b", 144:"eigenv.144b"}
    d_mlev_modlolvl = {27:20, 35:30, 54:40, 72:60, 108:80, 144:100}

    d.update({'nmr': 1, 'acon': 0.00, 'bcon': 0.02, 'eigenv': d_mlev_eigenv[d['mlev']],
              'mlolvl': d_mlev_modlolvl[d['mlev']]})

def config_initconds():
    "Configure initial condition file"

    d['nrungcm'] = 0

    if d['iyr'] == d['iys'] and d['imth'] == d['ims']:

        if d['dmode'] in [0, 2, 3]:
            d.update({'ifile': d['mesonest']})
        else:
            d.update({'ifile': d['sstinit']})

        if d['bcsoil'] == 0:
            d['nrungcm'] = -1
        elif d['bcsoil'] == 1:
            print("Import soil from climatology")
            d['nrungcm'] = -14
            d.update({'bcsoilfile': dict2str('{insdir}/vegin/sm{imth_2digit}')})
            check_file_exists(d['bcsoilfile']+'.000000')
        else:
            print("Recycle soil from input file")
            d['nrungcm'] = -4
            check_file_exists(d['bcsoilfile']+'.000000')


def set_nudging():
    "Set nudging strength parameters"

    if d['dmode'] == 0:
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})

    elif d['dmode'] == 1:
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})

    elif d['dmode'] == 2:
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': 1, 'ktopdav': 0, 'sigramplow': 0.05})

    elif d['dmode'] == 3:
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})


def set_downscaling():
    "Set downscaling parameters"

    if d['dmode'] == 0:
        d.update({'dmode_meth': 0, 'nud_p': 1, 'nud_q': 0, 'nud_t': 1,
                  'nud_uv': 1, 'mfix': 3, 'mfix_qg': 1, 'mfix_aero': 1,
                  'nbd': 0, 'mbd': d['mbd_base'], 'namip': 0, 'nud_aero': 0,
                  'mh_bs':3})

    elif d['dmode'] == 1:
        d.update({'dmode_meth': 1, 'nud_p': 0, 'nud_q': 0, 'nud_t': 0,
                  'nud_uv': 0, 'mfix': 3, 'mfix_qg': 1, 'mfix_aero': 1,
                  'nbd': 0, 'mbd': 0, 'namip': 14, 'nud_aero': 0,
                  'mh_bs':3})

    elif d['dmode'] == 2:
        d.update({'dmode_meth': 0, 'nud_p': 1, 'nud_q': 1, 'nud_t': 1,
                  'nud_uv': 1, 'mfix': 3, 'mfix_qg': 1, 'mfix_aero': 1,
                  'nbd': 0, 'mbd': d['mbd_base'], 'namip': 0, 'nud_aero': 1,
                  'mh_bs':3})

    elif d['dmode'] == 3:
        d.update({'dmode_meth': 0, 'nud_p': 0, 'nud_q': 0, 'nud_t': 0,
                  'nud_uv': 0, 'mfix': 3, 'mfix_qg': 1, 'mfix_aero': 1,
                  'nbd': 0, 'mbd': d['mbd_base'], 'namip': 0, 'nud_aero': 0,
                  'mh_bs':3})

def set_cloud():
    "Cloud microphysics settings"

    if d['cloud'] == 0:
        d.update({'ncloud': 0})

    elif d['cloud'] == 1:
        d.update({'ncloud': 2})

    elif d['cloud'] == 2:
        d.update({'ncloud': 3})

def set_ocean():
    "Ocean physics settings"

    if d['mlo'] == 0:
        #Interpolated SSTs
        d.update({'nmlo': 0, 'mbd_mlo': 0, 'nud_sst': 0,
                  'nud_sss': 0, 'nud_ouv': 0, 'nud_sfh': 0,
                  'kbotmlo': -1000})

    else:
        #Dynanical Ocean
        if d['dmode'] == 0 or d['dmode'] == 1 or d['dmode'] == 3:
            # Downscaling mode - GCM or SST-only:
            d.update({'nmlo': -3, 'mbd_mlo': 60, 'nud_sst': 1,
                      'nud_sss': 0, 'nud_ouv': 0, 'nud_sfh': 0,
                      'kbotmlo': -1000})

        elif d['dmode'] == 2:
            # Downscaling CCAM:
            d.update({'nmlo': -3, 'mbd_mlo': 60, 'nud_sst': 1,
                      'nud_sss': 1, 'nud_ouv': 1, 'nud_sfh': 1,
                      'kbotmlo': -1000})

def set_atmos():
    "Atmospheric physics settings"
    if d['sib'] == 1:
        d.update({'nsib': 7, 'soil_struc': 0, 'fwsoil_switch': 0, 'cable_litter': 0,
                  'gs_switch': 0})

        if d['casa'] == 0:
            d.update({'ccycle': 0, 'proglai': -1, 'progvcmax': 0, 'cable_pop': 0,
                      'cable_climate': 0})

        elif d['casa'] == 1:
            d.update({'ccycle': 3, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 0,
                      'cable_climate': 0})

        elif d['casa'] == 2:
            d.update({'ccycle': 2, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 1,
                      'cable_climate': 0})

        elif d['casa'] == 3:
            d.update({'ccycle': 2, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 1,
                      'cable_climate': 1})


    elif d['sib'] == 2:
        d.update({'nsib': 5, 'ccycle': 0, 'proglai': -1, 'progvcmax': 0,
                  'soil_struc': 0, 'fwsoil_switch': 0, 'cable_pop': 0,
                  'gs_switch': 0, 'cable_litter': 0, 'cable_climate': 0})

        if d['casa'] == 1:
            raise ValueError("casa=1 requires sib=1 or sib=3")

        if d['casa'] == 2:
            raise ValueError("casa=2 requires sib=1 or sib=3")

        if d['casa'] == 3:
            raise ValueError("casa=3 requires sib=1 or sib=3")

    elif d['sib'] == 3:
        d.update({'nsib': 7, 'soil_struc': 1, 'fwsoil_switch': 3, 'cable_litter': 1,
                  'gs_switch': 1})

        if d['casa'] == 0:
            d.update({'ccycle': 0, 'proglai': -1, 'progvcmax': 0, 'cable_pop': 0,
                      'cable_climate': 0})

        elif d['casa'] == 1:
            d.update({'ccycle': 3, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 0,
                      'cable_climate': 0})

        elif d['casa'] == 2:
            d.update({'ccycle': 2, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 1,
                      'cable_climate': 0})

        elif d['casa'] == 3:
            d.update({'ccycle': 2, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 1,
                      'cable_climate': 1})

    if d['cmip'] == "cmip5":
        d.update({'vegin': dict2str('{hdir}/vegdata'),
                  'vegprev': dict2str('veg{domain}.{imthlst_2digit}'),
                  'vegfile': dict2str('veg{domain}.{imth_2digit}'),
                  'vegnext': dict2str('veg{domain}.{imthnxt_2digit}'),
                  'vegnextb': dict2str('veg{domain}.{imthnxtb_2digit}')})
    else:
        # Use same year as LAI will not change.  Only the area fraction
        d.update({'vegin': dict2str('{hdir}/vegdata'),
                  'vegprev': dict2str('veg{domain}.{iyr}.{imthlst_2digit}'),
                  'vegfile': dict2str('veg{domain}.{iyr}.{imth_2digit}'),
                  'vegnext': dict2str('veg{domain}.{iyr}.{imthnxt_2digit}'),
                  'vegnextb': dict2str('veg{domain}.{iyr}.{imthnxtb_2digit}')})

    if d['bmix'] == 0:
        d.update({'nvmix': 3, 'nlocal': 6, 'amxlsq': 100.})

    elif d['bmix'] == 1:
        d.update({'nvmix': 6, 'nlocal': 7, 'amxlsq': 9.})

    elif d['bmix'] == 2:
        d.update({'nvmix': 7, 'nlocal': 6, 'amxlsq': 9.})

    d.update({'ngwd': -5, 'helim': 800., 'fc2': 1., 'sigbot_gwd': 0., 'alphaj': '0.000001'})

    if d['conv'] == 2:
        d.update({'ngwd': -20, 'helim': 1600., 'fc2': -0.5, 'sigbot_gwd': 1., 'alphaj': '0.025'})

    elif d['conv'] == 3:
        d.update({'ngwd': -20, 'helim': 1600., 'fc2': -0.5, 'sigbot_gwd': 1., 'alphaj': '0.025'})


def set_surfc():
    "Prepare surface files"

    d.update({'tbave': 0})

    if d['ncsurf'] != 0:
        d.update({'tbave': d['ktc_surf'] * 60 / d['dt']})

def set_aeros():
    "Prepare aerosol files"

    if d['aero'] == 0:
        # Aerosols turned off
        d.update({'iaero': 0, 'sulffile' : 'none'})

    if d['aero'] == 1:
        # Prognostic aerosols
        d.update({'iaero': 2, 'sulffile': 'aero.nc'})

        if d['cmip'] == "cmip5":
            if d['rcp'] == "historic" or d['iyr'] < 2010:
                aero = {'so2_anth': get_fpath('{stdat}/{cmip}/historic/IPCC_emissions_SO2_anthropogenic_{ddyear}*.nc'),
                        'so2_ship': get_fpath('{stdat}/{cmip}/historic/IPCC_emissions_SO2_ships_{ddyear}*.nc'),
                        'so2_biom': get_fpath('{stdat}/{cmip}/historic/IPCC_GriddedBiomassBurningEmissions_SO2_decadalmonthlymean{ddyear}*.nc'),
                        'bc_anth':  get_fpath('{stdat}/{cmip}/historic/IPCC_emissions_BC_anthropogenic_{ddyear}*.nc'),
                        'bc_ship':  get_fpath('{stdat}/{cmip}/historic/IPCC_emissions_BC_ships_{ddyear}*.nc'),
                        'bc_biom':  get_fpath('{stdat}/{cmip}/historic/IPCC_GriddedBiomassBurningEmissions_BC_decadalmonthlymean{ddyear}*.nc'),
                        'oc_anth':  get_fpath('{stdat}/{cmip}/historic/IPCC_emissions_OC_anthropogenic_{ddyear}*.nc'),
                        'oc_ship':  get_fpath('{stdat}/{cmip}/historic/IPCC_emissions_OC_ships_{ddyear}*.nc'),
                        'oc_biom':  get_fpath('{stdat}/{cmip}/historic/IPCC_GriddedBiomassBurningEmissions_OC_decadalmonthlymean{ddyear}*.nc')}

            else:
                aero = {'so2_anth': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_anthropogenic_{ddyear}*.nc'),
                        'so2_ship': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_ships_{ddyear}*.nc'),
                        'so2_biom': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_biomassburning_{ddyear}*.nc'),
                        'bc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_anthropogenic_{ddyear}*.nc'),
                        'bc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_ships_{ddyear}*.nc'),
                        'bc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_biomassburning_{ddyear}*.nc'),
                        'oc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_anthropogenic_{ddyear}*.nc'),
                        'oc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_ships_{ddyear}*.nc'),
                        'oc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_biomassburning_{ddyear}*.nc')}
        elif d['cmip'] == "cmip6":
            if d['rcp'] == "historic" or d['iyr'] < 2015:
                aero = {'so2_anth': get_fpath('{stdat}/{cmip}/cmip/SO2-em-anthro_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'so2_ship': get_fpath('{stdat}/{cmip}/cmip/SO2-em-anthro_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'so2_biom': get_fpath('{stdat}/{cmip}/cmip/SO2-em-openburning-share_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'bc_anth':  get_fpath('{stdat}/{cmip}/cmip/BC-em-anthro_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'bc_ship':  get_fpath('{stdat}/{cmip}/cmip/BC-em-anthro_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'bc_biom':  get_fpath('{stdat}/{cmip}/cmip/BC-em-openburning-share_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'oc_anth':  get_fpath('{stdat}/{cmip}/cmip/OC-em-anthro_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'oc_ship':  get_fpath('{stdat}/{cmip}/cmip/OC-em-anthro_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc'),
                        'oc_biom':  get_fpath('{stdat}/{cmip}/cmip/OC-em-openburning-share_input4MIPs_emissions_CMIP_CEDS-2017-05-18_gn_{iyr}*.nc')}
            else:
                if d['rcp'] == "ssp126":
                    d['rcplabel'] = "IMAGE"
                elif d['rcp'] == "ssp245":
                    d['rcplabel'] = "MESSAGE-GLOBIOM"
                elif d['rcp'] == "ssp370":
                    d['rcplabel'] = "AIM"
                elif d['rcp'] == "ssp460":
                    d['rcplabel'] = "GCAM4"
                elif d['rcp'] == "ssp585":
                    d['rcplabel'] = "REMIND-MAGPIE"
                else:
                    raise ValueError(dict2str("Invalid choice for rcp"))

                if d['iyr'] < 2020:
                    aero = {'so2_anth': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'so2_ship': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'so2_biom': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'bc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'bc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'bc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'oc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'oc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc'),
                            'oc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2015*.nc')}
                else:
                    aero = {'so2_anth': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'so2_ship': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'so2_biom': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'bc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'bc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'bc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'oc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'oc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc'),
                            'oc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_{ddyear}*.nc')}
        else:
            raise ValueError(dict2str("Invalid choice for cmip"))

        aero['volcano'] = dict2str('{stdat}/contineous_volc.nc')
        aero['dmsfile'] = dict2str('{stdat}/dmsemiss.nc')
        aero['dustfile'] = dict2str('{stdat}/ginoux.nc')

        for fpath in iter(aero.keys()):
            check_file_exists(aero[fpath])

        d.update(aero)


def create_aeroemiss_file():
    "Write arguments to 'aeroemiss' namelist file"

    if d['aero'] == 1:
        write2file('aeroemiss.nml', aeroemiss_template(), mode='w+')


def create_sulffile_file():
    "Create the aerosol forcing file"

    # Remove any existing sulffile:
    run_cmdline('rm -rf {sulffile}')

    # Create new sulffile:
    if d['machinetype'] == 1:
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" KMP_STACKSIZE=1024m srun -n 1 {aeroemiss} -o {sulffile} < aeroemiss.nml > aero.log || exit')
    else:
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" KMP_STACKSIZE=1024m {aeroemiss} -o {sulffile} < aeroemiss.nml > aero.log || exit')

    xtest = (subprocess.getoutput('grep -o "aeroemiss completed successfully" aero.log')
             == "aeroemiss completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running aeroemiss.  Check aero.log for details"))


def create_input_file():
    "Write arguments to the CCAM 'input' namelist file"

    # Number of steps between output:
    d['nwt'] = int(d['dtout']*60/d['dt'])

    # Number of steps in run:
    d['ntau'] = int(d['ndays']*86400/d['dt'])

    # Start date string:
    d['kdates'] = str(d['iyr']*10000 + d['imth']*100 + 1)

    write2file('input', input_template_1(), mode='w+')

    if d['conv'] == 0:
        write2file('input', input_template_2())
    elif d['conv'] == 1:
        write2file('input', input_template_3())
    elif d['conv'] == 2:
        write2file('input', input_template_4())
    elif d['conv'] == 3:
        write2file('input', input_template_5())
    elif d['conv'] == 4:
        write2file('input', input_template_3a())

    write2file('input', input_template_6())


def prepare_ccam_infiles():
    "Prepare and check CCAM input data"

    if d['dmode'] == 0 or d['dmode'] == 2 or d['dmode'] == 3:
        fpath = dict2str('{bcdir}/{mesonest}')
        if os.path.exists(fpath):
            run_cmdline('ln -s '+fpath+' .')
        elif os.path.exists(fpath+'.000000'):
            run_cmdline('ln -s '+fpath+'.?????? .')
        else:
            check_file_exists(fpath+'.tar')
            run_cmdline('tar xvf '+fpath+'.tar')

    if d['dmode'] == 1:
        fpath = dict2str('{sstinit}')
        if os.path.exists(fpath):
            run_cmdline('ln -s '+fpath+' .')
        elif os.path.exists(fpath+'.000000'):
            run_cmdline('ln -s '+fpath+'.?????? .')
        else:
            check_file_exists(fpath+'.tar')
            run_cmdline('tar xvf '+fpath+'.tar')

    if not os.path.exists(d['ifile']) and not os.path.exists(d['ifile']+'.000000'):
        raise ValueError(dict2str('Cannot locate {ifile} or {ifile}.000000. ')+
                         'If this is the start of a new run, please check that year.qm has been deleted')

    if d['dmode'] != 1:
        if not os.path.exists(d['mesonest']) and not os.path.exists(d['mesonest']+'.000000'):
            raise ValueError(dict2str('Cannot locate {mesonest} or {mesonest}.000000'))

    for file in ['topout{domain}', '{vegprev}', '{vegfile}', '{vegnext}', '{vegnextb}']:
        check_file_exists(dict2str('{vegin}/'+file))

    if d['nmlo'] != 0 and not os.path.exists(dict2str('{vegin}/bath{domain}')):
        raise ValueError(dict2str('Cannot locate {vegin}/bath{domain}'))

    if d['aero'] != 0 and not os.path.exists(d['sulffile']):
        raise ValueError('Cannot locate '+d['sulffile'])

    if d['dmode'] == 1 and not os.path.exists(dict2str('{sstdir}/{sstfile}')):
        raise ValueError(dict2str('Cannot locate {sstdir}/{sstfile}'))


def check_correct_host():
    "Check if host is CCAM"

    if d['dmode'] in [0, 2]:
        for fname in [d['mesonest'], d['mesonest']+'.000000']:
            if os.path.exists(fname):
                ccam_host = (subprocess.getoutput('ncdump -c '+fname+' | grep -o :version') == ":version")
                break
        if ccam_host is True and d['dmode'] == 0:
            raise ValueError('CCAM is the host model. Use dmode = 2')
        if ccam_host is False and d['dmode'] == 2:
            raise ValueError('CCAM is not the host model. Use dmode = 0')

    if d['dmode'] == 1:
        if d['inv_schmidt'] < 0.2:
            raise ValueError('CCAM grid stretching is too high for dmode=0.  Try reducing grid resolution or increasing grid size')

    if d['dmode'] == 2:
        fname = d['mesonest']+'.000000'
        if os.path.exists(fname):
            host_inv_schmidt = float(subprocess.getoutput('ncdump -c '+fname+' | grep schmidt | cut -d"=" -f2 | cut -d";" -f1 | sed "s/f//g" | sed "s/ //g"'))
            host_gridsize = float(subprocess.getoutput('ncdump -c '+fname+' | grep il_g | cut -d"=" -f2 | cut -d";" -f1 | sed "s/ //g"'))
            host_grid_res = host_inv_schmidt * 112. * 90. / host_gridsize
            nest_grid_width = float(d['gridsize']) * float(d['gridres_m'])
            host_grid_dx = 3. * host_grid_res
            if nest_grid_width < host_grid_dx:
                raise ValueError('Too large a jump beteen nest and host grid.  Try reducing grid resolution or increasing grid size')


def check_correct_landuse(fname):
    "Check that land-use data matches what the user wants"

    testfail = False

    cable_data = (subprocess.getoutput('ncdump -c '+fname+' | grep -o cableversion') == "cableversion")
    if d['sib'] == 1 and cable_data is False:
        testfail = True

    modis_data = (subprocess.getoutput('ncdump -c '+fname+' | grep -o sibvegversion') == "sibvegversion")
    if d['sib'] == 2 and modis_data is False:
        testfail = True

    cable_data = (subprocess.getoutput('ncdump -c '+fname+' | grep -o cableversion') == "cableversion")
    if d['sib'] == 3 and cable_data is False:
        testfail = True

    return testfail


def run_model():
    "Execute the CCAM model"

    if d['machinetype'] == 1:
        run_cmdline('srun -n {nproc} {model} > prnew.{kdates}.{name} 2> err.{iyr}')
    else:
        run_cmdline('mpirun -np {nproc} {model} > prnew.{kdates}.{name} 2> err.{iyr}')

    prfile = dict2str('prnew.{kdates}.{name}')
    xtest = (subprocess.getoutput('grep -o "globpea completed successfully" '+prfile)
             == "globpea completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running CCAM.  Check prnew.{kdates}.{name} for details"))

    run_cmdline('rm {mesonest}.?????? {mesonest}')

def post_process_output():
    "Post-process the CCAM model output"

    if d['ncout'] == 1:
        write2file('cc.nml', cc_template_1(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n {nproc} {pcc2hist} > pcc2hist.log')
        else:
            run_cmdline('mpirun -np {nproc} {pcc2hist} > pcc2hist.log')
        xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" pcc2hist.log')
                 == "pcc2hist completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured while running pcc2hist.  Check pcc2hist.log for details"))

    if d['ncout'] == 2:
        write2file('cc.nml', cc_template_1(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n {nproc} {pcc2hist} --cordex > pcc2hist.log')
        else:
            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > pcc2hist.log')
        xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" pcc2hist.log')
                 == "pcc2hist completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured while running pcc2hist. Check pcc2hist.log"))

    if d['ncout'] == 3 or d['ncout'] == 5:
        for iday in range(1, d['ndays']+1):
            d['cday'] = mon_2digit(iday)
            d['iend'] = iday*1440
            d['istart'] = (iday*1440)-1440
            d['outctmfile'] = dict2str("ccam_{iyr}{imth_2digit}{cday}.nc")
            write2file('cc.nml', cc_template_2(), mode='w+')
            if d['machinetype'] == 1:
                run_cmdline('srun -n {nproc} {pcc2hist} > pcc2hist_ctm.log')
            else:
                run_cmdline('mpirun -np {nproc} {pcc2hist} > pcc2hist_ctm.log')
            xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" pcc2hist_ctm.log')
                     == "pcc2hist completed successfully")
            if xtest is False:
                raise ValueError(dict2str("An error occured while running pcc2hist.  Check pcc2hist_ctm.log for details"))
        if d['ncout'] == 3:
            run_cmdline('tar cvf {hdir}/daily/ctm_{iyr}{imth_2digit}.tar ccam_{iyr}{imth_2digit}??.nc')
            run_cmdline('rm ccam_{iyr}{imth_2digit}??.nc')
        elif d['ncout'] == 5:
            run_cmdline('mv ccam_{iyr}{imth_2digit}??.nc {hdir}/daily')

    if d['ncout'] == 4:
        write2file('cc.nml', cc_template_1(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n {nproc} {pcc2hist} --interp=nearest > pcc2hist.log')
        else:
            run_cmdline('mpirun -np {nproc} {pcc2hist} --interp=nearest > pcc2hist.log')
        xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" pcc2hist.log')
                 == "pcc2hist completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured while running pcc2hist.  Check pcc2hist.log for details"))

    if d['ncout'] == 6:
        write2file('cc.nml', cc_template_4(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n {nproc} {pcc2hist} --cordex > pcc2hist.log')
        else:
            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > pcc2hist.log')
        xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" pcc2hist.log')
                 == "pcc2hist completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured running pcc2hist. Check pcc2hist.log"))

    # surface files

    d['ktc_units'] = d['ktc_surf']
    fname = dict2str('surf.{ofile}.000000')
    seconds_check = (subprocess.getoutput('ncdump -c '+fname+' | grep time | grep units | grep -o seconds') == "seconds")
    if seconds_check is True:
        d['ktc_units'] = d['ktc_units']*60

    if d['ncsurf'] == 1:
        write2file('cc.nml', cc_template_3(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n {nproc} {pcc2hist} > surf.pcc2hist.log')
        else:
            run_cmdline('mpirun -np {nproc} {pcc2hist} > surf.pcc2hist.log')
        xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" surf.pcc2hist.log')
                 == "pcc2hist completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured running pcc2hist. Check surf.pcc2hist.log"))

    if d['ncsurf'] == 3:
        write2file('cc.nml', cc_template_5(), mode='w+')
        if d['machinetype'] == 1:
            run_cmdline('srun -n {nproc} {pcc2hist} --cordex > surf.pcc2hist.log')
        else:
            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > surf.pcc2hist.log')
        xtest = (subprocess.getoutput('grep -o "pcc2hist completed successfully" surf.pcc2hist.log')
                 == "pcc2hist completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured running pcc2hist. Check surf.pcc2hist.log"))

    # store output
    if d['nctar'] == 0:
        run_cmdline('mv {ofile}.?????? {hdir}/OUTPUT')
        if d['ncsurf'] != 0:
            run_cmdline('mv surf.{ofile}.?????? {hdir}/OUTPUT')

    if d['nctar'] == 1:
        run_cmdline('tar cvf {hdir}/OUTPUT/{ofile}.tar {ofile}.??????')
        run_cmdline('rm {ofile}.??????')
        if d['ncsurf'] != 0:
            run_cmdline('tar cvf {hdir}/OUTPUT/surf.{ofile}.tar surf.{ofile}.??????')
            run_cmdline('rm surf.{ofile}.??????')

    if d['nctar'] == 2:
        run_cmdline('rm {ofile}.??????')
        if d['ncsurf'] != 0:
            run_cmdline('rm surf.{ofile}.??????')

    # update counter for next simulation month and remove old files
    d['imth'] = d['imth'] + 1

    if d['imth'] < 12:
        run_cmdline('rm Rest{name}.{iyrlst}12.??????')

    elif d['imth'] > 12:
        run_cmdline('tar cvf {hdir}/RESTART/Rest{name}.{iyr}12.tar Rest{name}.{iyr}12.??????')
        run_cmdline('rm Rest{name}.{iyr}0?.?????? Rest{name}.{iyr}10.?????? Rest{name}.{iyr}11.??????')
        run_cmdline('rm prnew.{iyr}*')
        run_cmdline('rm {name}*{iyr}??')
        run_cmdline('rm {name}*{iyr}??.nc')
        d['imth'] = 1
        d['iyr'] = d['iyr'] + 1

def update_yearqm():
    "Update the year.qm file"

    yyyymm = d['iyr'] * 100 + d['imth']
    d['yyyymm'] = yyyymm
    write2file(d['hdir']+'/year.qm', "{yyyymm}", mode='w+')

def restart_flag():
    "Create restart.qm containing flag for restart. This flag signifies that CCAM completed previous month"

    # Abort run at finish year:
    sdate = d['iyr']*100 +d['imth']
    edate = d['iye']*100 +d['ime']

    if sdate > edate:
        write2file(d['hdir']+'/restart.qm', "Complete", mode='w+')
        sys.exit(0)
    else:
        write2file(d['hdir']+'/restart.qm', "True", mode='w+')


def run_cmdline(arg):
    "Run a command line argument from within python"

    os.system(dict2str(arg))

def dict2str(str_template):
    "Create a string that includes dictionary elements"

    return str_template.format(**d)

def write2file(fname, args_template, mode='a'):
    "Write arguments to namelist file"

    with open(fname, mode) as ofile:
        ofile.write(args_template.format(**d))

    ofile.close()

def get_fpath(fpath):
    "Get relevant file path(s)"
    return subprocess.getoutput(dict2str('ls -1tr '+fpath+' | tail -1'))

def check_file_exists(path):
    "Check that the specified file path exists"

    if not os.path.exists(path):
        raise ValueError('File not found: '+path)

def mon_2digit(imth):
    "Create 2-digit numerical string for given month"

    imth = int(imth)

    if imth < 10:
        return '0'+str(imth)

    return str(imth)

def top_template():
    "Template for writing top.nml namelist file"

    return """\
    &topnml
     il={gridsize}
     debug=t idia=29 jdia=48 id=2 jd=4
     fileout="topout{domain}" luout=50
     rlong0={midlon} rlat0={midlat} schmidt={inv_schmidt:0.4f}
     dosrtm=f do1km=t do250=t netout=t topfilt=t    
     filepath10km="{insdir}/vegin"
     filepath1km="{insdir}/vegin"
     filepath250m="{insdir}/vegin"
     filepathsrtm="{insdir}/vegin"
    &end
    """

def igbpveg_template():
    "Template for writing igbpveg.nml namelist file"

    return """\
    &vegnml
     month=0
     year={iyr}
     topofile="topout{domain}"
     newtopofile="topsib{domain}"
     landtypeout="veg{domain}"
     veginput="{insdir}/vegin/gigbp2_0ll.img"
     soilinput="{insdir}/vegin/usda4.img"
     laiinput="{insdir}/vegin"
     albvisinput="{insdir}/vegin/salbvis223.img"
     albnirinput="{insdir}/vegin/salbnir223.img"
     change_landuse="{change_landuse}"
     fastigbp=t
     igbplsmask=t
     ozlaipatch=f
     binlimit=2
     tile=t
     outputmode="cablepft"
     mapconfig="{vegindex}"
     pftconfig="{cableparm}"
     atebconfig="{uclemparm}"
     soilconfig="{soilparm}"
     user_veginput="{uservegfile}"
     user_laiinput="{userlaifile}"
    &end
    """

def sibveg_template():
    "Template for writing sibveg.nml namelist file"

    return """\
    &vegnml
     month=0
     topofile="topout{domain}"
     newtopofile="topsib{domain}"
     landtypeout="veg{domain}"
     datapath="{insdir}/vegin"
     fastsib=t
     siblsmask=f
     ozlaipatch=f
     binlimit=2
     zmin=20.
     usedean=t
     deanlake=f
    &end
    """

def ocnbath_template():
    "Template for writing ocnbath.nml namelist file"

    return """\
    &ocnnml
     topofile="topout{domain}"
     bathout="bath{domain}"
     bathdatafile="{insdir}/vegin/etopo1_ice_c.flt"
     riverdatapath="{insdir}/vegin"
     fastocn=t
     bathfilt=t
     binlimit=4
     rtest=1.
    &end
    """

def aeroemiss_template():
    "Template for writing aeroemiss.nml namelist file"

    return """\
    &aero
     month={imth_2digit}
     topofile='{vegin}/topout{domain}'
     so2_anth='{so2_anth}'
     so2_ship='{so2_ship}'
     so2_biom='{so2_biom}'
     bc_anth= '{bc_anth}'
     bc_ship= '{bc_ship}'
     bc_biom= '{bc_biom}'
     oc_anth= '{oc_anth}'
     oc_ship= '{oc_ship}'
     oc_biom= '{oc_biom}'
     volcano= '{stdat}/contineous_volc.nc'
     dmsfile= '{stdat}/dmsemiss.nc'
     dustfile='{stdat}/ginoux.nc'
    &end
    """

def input_template_1():
    "First part of template for 'input' namelist file"

    template1 = """\
    &defaults &end
    &cardin
     COMMENT='date and runlength'
     kdate_s={kdates} ktime_s=0000 leap={leap}
     dt={dt} nwt={nwt} ntau={ntau}
     nmaxpr=999999 newtop=1 nrungcm={nrungcm}
     namip={namip} rescrn=1 zo_clearing=0.05

     COMMENT='dynamical core'
     epsp=0.1 epsu=0.1 epsh=1.
     precon=-10000 restol=2.e-7 nh=5 knh=9
     nstagu=1 khor=0 nhorps=-1 nhorjlm=0
     mh_bs={mh_bs}

     COMMENT='mass fixer'
     mfix_qg={mfix_qg} mfix={mfix} mfix_aero={mfix_aero}

     COMMENT='nudging'
     nbd={nbd} mbd={mbd} mbd_maxscale={mbd_maxscale} mbd_maxgrid={mbd_maxgrid}
     nud_p={nud_p} nud_q={nud_q} nud_t={nud_t} nud_uv={nud_uv}
     nud_aero={nud_aero} nud_hrs=1
     nud_period=60
     kbotdav={kbotdav} ktopdav={ktopdav} sigramplow={sigramplow}
     mbd_maxscale_mlo=1000 mbd_mlo={mbd_mlo}
     nud_sst={nud_sst} nud_sss={nud_sss} nud_ouv={nud_ouv} nud_sfh={nud_sfh}
     ktopmlo=1 kbotmlo={kbotmlo} mloalpha=12

     COMMENT='ocean, lakes and rivers'
     nmlo={nmlo} ol={mlolvl} tss_sh=0.3 nriver=-1

     COMMENT='land, urban and carbon'
     nsib={nsib} nurban=1 vmodmin=0.1 nsigmf=0 jalbfix=0

     COMMENT='radiation and aerosols'
     nrad=5 iaero={iaero}

     COMMENT='boundary layer'
     nvmix={nvmix} nlocal={nlocal}

     COMMENT='station'
     mstn=0 nstn=0

     COMMENT='file'
     localhist=.true. unlimitedhist=.false. synchist=.false.
     compression=1 tbave={tbave}
    &end
    &skyin
     mins_rad=-1 qgmin=2.E-7
     ch_dust=3.E-10
    &end
    &datafile
     ifile=      '{ifile}'
     mesonest=   '{mesonest}'
     topofile=   '{vegin}/topout{domain}'
     vegprev=    '{vegin}/{vegprev}'
     vegfile=    '{vegin}/{vegfile}'
     vegnext=    '{vegin}/{vegnext}'
     vegnext2=   '{vegin}/{vegnextb}'
     bathfile=   '{vegin}/bath{domain}'
     cnsdir=     '{stdat}'
     radfile=    '{co2file}'
     ch4file=    '{ch4file}'
     n2ofile=    '{n2ofile}'
     cfc11file=  '{cfc11file}'
     cfc12file=  '{cfc12file}'
     cfc113file= '{cfc113file}'
     hcfc22file= '{hcfc22file}'
     solarfile=  '{solarfile}'
     eigenv=     '{stdat}/{eigenv}'
     o3file=     '{ozone}'
     so4tfile=   '{sulffile}'
     oxidantfile='{stdat}/oxidants.nc'
     ofile=      '{ofile}'
     restfile=   'Rest{name}.{iyr}{imth_2digit}'
     sstfile=    '{sstdir}/{sstfile}'
     casafile=   '{vegin}/casa{domain}'
     phenfile=   '{stdat}/modis_phenology_csiro.nc'
     casapftfile='{stdat}/pftlookup.csv'
     surf_00    ='{bcsoilfile}'
     surf_cordex=1
     """

    template2 = """
     surfile=    'surf.{ofile}'
     """

    template3 = """
    &end
    """

    if d['ncsurf'] == 0:
        template = template1 + template3
    else:
        template = template1 + template2 + template3

    return template

def input_template_2():
    "Second part of template for 'input' namelist file"

    return """
    &kuonml
     alfsea=1.10 alflnd=1.25
     convfact=1.05 convtime=-2030.60
     tied_con=0.85 mdelay=0
     fldown=-0.3
     iterconv=3
     ksc=0 kscsea=0 kscmom=1 dsig2=0.1
     mbase=0 nbase=10
     methprec=5 detrain=0.15 methdetr=3
     ncvcloud=0
     nevapcc=0 entrain=0.1
     nuvconv=-3
     rhcv=0.1 rhmois=0. tied_over=-26.
     nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l=0.8 rcrit_s=0.8
    &end
    """

def input_template_3():
    "Third part of template for 'input' namelist file"

    return """
    &kuonml
     alfsea=1.05 alflnd=1.20
     convfact=1.05 convtime=-2030.60
     fldown=-0.3
     iterconv=3
     ksc=0 kscsea=0 kscmom=1 dsig2=0.1
     mbase=4 nbase=-2
     methprec=5 detrain=0.1 methdetr=-2
     mdelay=0
     ncvcloud=0
     nevapcc=0 entrain=-0.5
     nuvconv=-3
     rhmois=0. rhcv=0.1
     tied_con=0. tied_over=2626.
     nclddia=12
     nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l=0.8 rcrit_s=0.8
    &end
    """

def input_template_3a():
    "Third part (mod) of template for 'input' namelist file"

    return """
    &kuonml
     alfsea=1.1 alflnd=1.1
     convfact=1.05 convtime=-2525.60
     fldown=-0.3
     iterconv=3
     ksc=0 kscsea=0 kscmom=1 dsig2=0.1
     mbase=4 nbase=-2
     methprec=5 detrain=0.1 methdetr=-2
     mdelay=0
     ncvcloud=0
     nevapcc=0 entrain=-0.5
     nuvconv=-3
     rhmois=0. rhcv=0.1
     tied_con=0. tied_over=2626. tied_rh=0.
     nclddia=12
     nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l=0.8 rcrit_s=0.8
    &end
    """

def input_template_4():
    "Fourth part of template for 'input' namelist file"

    return """
    &kuonml
     nkuo=23 sig_ct=1. rhcv=0.1 rhmois=0. convfact=1.05 convtime=-2030.60
     alflnd=1.2 alfsea=1.10 fldown=-0.3 iterconv=3 ncvcloud=0 nevapcc=0
     nuvconv=-3
     mbase=4 mdelay=0 methprec=5 nbase=-10 detrain=0.1 entrain=-0.5
     methdetr=-1 detrainx=0. dsig2=0.1 dsig4=1.
     ksc=0 kscsea=0 sigkscb=0.95 sigksct=0.8 tied_con=0. tied_over=2626.
     ldr=1 nclddia=12 nstab_cld=0 nrhcrit=10 sigcll=0.95
     nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l=0.8 rcrit_s=0.8
    &end
    """

def input_template_5():
    "Fifth part of template for 'input' namelist file"

    return """
    &kuonml
     nkuo=21 iterconv=3 ksc=0 kscsea=0 mdelay=0
     alflnd=1.10 alfsea=1.10 convfact=1.05 convtime=-3030.60
     detrain=0.15 detrainx=0. dsig4=1. entrain=-0.5 fldown=-0.3
     mbase=1 nbase=3
     methdetr=-1 methprec=5 ncvcloud=0 nevapcc=0 nuvconv=-3
     rhcv=0. rhmois=0. tied_con=0. tied_over=2626.
     ldr=1 nclddia=12 nstab_cld=0 nrhcrit=10 sigcll=0.95
     dsig2=0.1 kscmom=0 sig_ct=1. sigkscb=0.95 sigksct=0.8 tied_rh=0.
     nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l=0.8 rcrit_s=0.8
    &end
    """

def input_template_6():
    "Sixth part of template for 'input' namelist file"

    return """
    &turbnml
     buoymeth=1 tkemeth=1
     mintke=1.5e-4 mineps=1.e-6 minl=5. maxl=500.
     qcmf=1.e-4 ezmin=10.
     ent0=0.5 ent1=0. ent_min=0.001
     be=1. b1=1. b2=2. m0=0.1
     dvmodmin=0.01 amxlsq={amxlsq}
     ngwd={ngwd} helim={helim} fc2={fc2}
     sigbot_gwd={sigbot_gwd} alphaj={alphaj}
    &end
    &landnml
     proglai={proglai} progvcmax={progvcmax} ccycle={ccycle}
     soil_struc={soil_struc} fwsoil_switch={fwsoil_switch}
     cable_pop={cable_pop} gs_switch={gs_switch}
     cable_litter={cable_litter} cable_climate={cable_climate}
     ateb_intairtmeth=1 ateb_intmassmeth=2
     ateb_zoroof=0.05 ateb_zocanyon=0.05
    &end
    &mlonml
     mlodiff=1 otaumode=1 mlojacobi=7 mlomfix=2
     usetide=0 mlosigma=6 nodrift=1
     ocnsmag=0.8 zomode=0 ocneps=0.2
     rivermd=1
    &end
    &tin &end
    &soilin &end
    """

def cc_template_1():
    "First part of template for 'cc.nml' namelist file"

    template = """\
    &input
     ifile = "{ofile}"
     ofile = "{hdir}/daily/{ofile}.nc"
     hres  = {res}
     kta={ktc}   ktb=999999  ktc={ktc}
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
     use_plevs = {use_plevs}
     use_meters = {use_meters}     
     use_depth = {use_depth}
     plevs = {plevs}
     mlevs = {mlevs}
     dlevs = {dlevs}
    &end
    &histnl
     htype="inst"
     hnames= "all"  hfreq = 1
    &end
    """

    return template

def cc_template_2():
    "Second part of template for 'cc.nml' namelist file"

    template1 = """\
    &input
     ifile = "{ofile}"
     ofile = "{outctmfile}"
     hres  = {res}
     kta={istart} ktb={iend} ktc=60
     minlat = {minlat}, maxlat = {maxlat}
     minlon = {minlon}, maxlon = {maxlon}
     use_plevs = F
     use_meters = F
     use_depth = F
    &end
    &histnl
     htype="inst"
    """

    template2 = """\
    hnames="land_mask","vegt","soilt","lai","zolnd","zs","sigmf","tscr_ave",\
"temp","u","v","omega","mixr","qlg","qfg","ps","rnd","rnc","pblh","fg","eg",\
"taux","tauy","cld","qgscrn","tsu","wb1_ave","wb2_ave","wb3_ave","wb4_ave",\
"wb5_ave","wb6_ave","tgg1","tgg2","tgg3","tgg4","tgg5","tgg6","ustar","rsmin",\
"cbas_ave","ctop_ave","u10"
     hfreq = 1
    &end
    """

    template3 = """\
    hnames="land_mask","vegt","soilt","lai","zolnd","zs","sigmf","tscr_ave",\
"temp","u","v","omega","mixr","qlg","qfg","ps","rnd","rnc","pblh","fg","eg",\
"taux","tauy","cld","qgscrn","tsu","wb1_ave","wb2_ave","wb3_ave","wb4_ave",\
"wb5_ave","wb6_ave","tgg1","tgg2","tgg3","tgg4","tgg5","tgg6","ustar","rs",\
"cbas_ave","ctop_ave","u10"
     hfreq = 1
    &end
    """

    if d['sib'] == 1:
        template = template1 + template3

    if d['sib'] == 2:
        template = template1 + template2

    if d['sib'] == 3:
        template = template1 + template3

    return template

def cc_template_3():
    "Third part of template for 'cc.nml' namelist file"

    template1 = """\
    &input
     ifile = "surf.{ofile}"
    """

    template2 = """\
     ofile = "{hdir}/daily/surf.{ofile}.nc"
    """

    template3 = """\
     hres  = {res}
     kta={ktc_units}   ktb=2999999  ktc={ktc_units}
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
    &end
    &histnl
     htype="inst"
     hnames= "uas","vas","tscrn","tdscrn","rhscrn","psl","ps","rnd","sno","grpl","d10","u10","dni","sgdn_ave","rgdn_ave","eg_ave","fg_ave","sgn_ave","rgn_ave","epot_ave","tsu","pblh","taux","tauy","runoff","mrros","snd","snm","rtu_ave","sint_ave","sot_ave"
     hfreq = 1
    &end
    """

    template = template1 + template2 + template3

    return template

def cc_template_4():
    "First part of template for 'cc.nml' namelist file"

    template1 = """\
    &input
     ifile = "{ofile}"
    """

    template2 = """\
     ofile = "{hdir}/daily/{ofile}.nc"
    """

    template3 = """\
     hres  = {res}
     kta={ktc}   ktb=999999  ktc={ktc}
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
     use_plevs = F
     use_meters = F
     use_depth = F
    &end
    &histnl
     htype="inst"
     hnames= "he","pr","ps","ts","alb","clh","cll","clm","clt","cor","d10","dni","lai","prc","psl","sic","snc","snd","snm","snw","tas","epan","evap","grid","grpl","hfls","hfss","hurs","huss","mrro","mrso","orog","prsn","rlds","rlus","rlut","rsds","rsdt","rsus","rsut","sund","tauu","tauv","tpan","vegt","zmla","clivi","clwvi","mrfso","mrros","prmax","qstar","rnd24","sftlf","siced","sigmf","sigmu","soilt","tstar","uscrn","ustar","zolnd","tasmax","tasmin","u10max","v10max","uriver","vriver","wetfac","dew_ave","evspsbl","sfcWind","anth_ave","cape_ave","cape_max","cbas_ave","ctop_ave","epan_ave","rhmaxscr","rhminscr","rnet_ave","sdischarge","tdscrn","urbantas","evspsblpot","sfcWindmax","thetavstar","urbantasmax","urbantasmin","anth_elecgas_ave","anth_heat_ave","anth_cool_ave"
     hfreq = 1
    &end
    """

    template = template1 + template2 + template3

    return template

def cc_template_5():
    "Fifth part of template for 'cc.nml' namelist file"

    template1 = """\
    &input
     ifile = "surf.{ofile}"
    """

    template2 = """\
     ofile = "{hdir}/daily/surf.{ofile}.nc"
    """

    template3 = """\
     hres  = {res}
     kta={ktc_units}   ktb=2999999  ktc={ktc_units}
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
    &end
    &histnl
     htype="inst"
     hnames= "tas","tasmax","tasmin","pr","ps","psl","huss","hurs","sfcWind","sfcWindmax","clt","sund","rsds","rlds","hfls","hfss","rsus","evspsbl","evspsblpot","mrfso","mrros","mrro","mrso","snw","snm","prhmax","prc","rlut","rsdt","rsut","uas","vas","tauu","tauv","ts","zmla","prw","clwvi","clivi","ua850","va850","ta850","hus850","ua500","va500","ta500","zg500","ua200","va200","ta200","zg200","clh","clm","cll","snc","snd","sic","prsn","orog","sftlf"
     hfreq = 1
    &end
    """

    template = template1 + template2 + template3

    return template


if __name__ == '__main__':

    extra_info = """
    Usage:
        python run_ccam.py [-h]

    Author:
        Mitchell Black, mitchell.black@csiro.au
    Modifications:
        Marcus Thatcher, marcus.thatcher@csiro.au	
    """
    description = 'Run the CCAM model'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info,
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--name", type=str, help=" run name")
    parser.add_argument("--nproc", type=int, help=" number of processors")
    parser.add_argument("--nnode", type=int, help=" number of processors per node")

    parser.add_argument("--midlon", type=float, help=" central longitude of domain")
    parser.add_argument("--midlat", type=float, help=" central latitude of domain")
    parser.add_argument("--gridres", type=float, help=" required resolution (km) of domain")
    parser.add_argument("--gridsize", type=int, help=" cubic grid size")
    parser.add_argument("--mlev", type=int, choices=[27, 35, 54, 72, 108, 144], help=" number of model levels (27, 35, 54, 72, 108 or 144)")

    parser.add_argument("--iys", type=int, help=" start year [YYYY]")
    parser.add_argument("--ims", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], help=" start month [MM]")
    parser.add_argument("--iye", type=int, help=" end year [YYYY]")
    parser.add_argument("--ime", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], help=" end month [MM]")
    parser.add_argument("--leap", type=int, choices=[0, 1], help=" Use leap days (0=off, 1=on)")
    parser.add_argument("--ncountmax", type=int, help=" Number of months before resubmit")

    parser.add_argument("--ktc", type=int, help=" standard output period (mins)")
    parser.add_argument("--minlat", type=float, help=" output min latitude (degrees)")
    parser.add_argument("--maxlat", type=float, help=" output max latitude (degrees)")
    parser.add_argument("--minlon", type=float, help=" output min longitude (degrees)")
    parser.add_argument("--maxlon", type=float, help=" output max longitude (degrees)")
    parser.add_argument("--reqres", type=float, help=" required output resolution (degrees) (-1.=automatic)")
    parser.add_argument("--outlevmode", type=int, choices=[0, 1], help=" Output level mode (0=pressure, 1=meters)")
    parser.add_argument("--plevs", type=str, help=" output pressure levels (hPa)")
    parser.add_argument("--mlevs", type=str, help=" output height levels (m)")
    parser.add_argument("--dlevs", type=str, help=" output ocean depth (m)")

    parser.add_argument("--dmode", type=int, choices=[0, 1, 2, 3, 4], help=" downscaling (0=spectral(GCM), 1=SST-only, 2=spectral(CCAM), 3=SST-6hr), 4=Veg-only")
    parser.add_argument("--sib", type=int, choices=[1, 2, 3], help=" land surface (1=CABLE, 2=MODIS, 3=CABLE+SLI)")
    parser.add_argument("--aero", type=int, choices=[0, 1], help=" aerosols (0=off, 1=prognostic)")
    parser.add_argument("--conv", type=int, choices=[0, 1, 2, 3, 4], help=" convection (0=2014, 1=2015a, 2=2015b, 3=2017, 4=Mod2015a)")
    parser.add_argument("--cloud", type=int, choices=[0, 1, 2], help=" cloud microphysics (0=liq+ice, 1=liq+ice+rain, 2=liq+ice+rain+snow+graupel)")
    parser.add_argument("--bmix", type=int, choices=[0, 1, 2], help=" boundary layer (0=Ri, 1=TKE-eps, 2=HBG)")
    parser.add_argument("--mlo", type=int, choices=[0, 1], help=" ocean (0=Interpolated SSTs, 1=Dynamical ocean)")
    parser.add_argument("--casa", type=int, choices=[0, 1, 2, 3], help=" CASA-CNP carbon cycle with prognostic LAI (0=off, 1=CASA-CNP, 2=CASA-CN+POP, 3=CASA-CN+POP+CLIM)")
    parser.add_argument("--ncout", type=int, choices=[0, 1, 2, 3, 4, 5, 6], help=" standard output format (0=none, 1=CCAM, 2=CORDEX, 3=CTM(tar), 4=Nearest, 5=CTM(raw), 6=CORDEX-surface)")
    parser.add_argument("--nctar", type=int, choices=[0, 1, 2], help=" TAR output files in OUTPUT directory (0=off, 1=on, 2=delete)")
    parser.add_argument("--ncsurf", type=int, choices=[0, 1, 3], help=" High-freq output (0=none, 1=lat/lon, 3=cordex)")
    parser.add_argument("--ktc_surf", type=int, help=" High-freq file output period (mins)")

    parser.add_argument("--uclemparm", type=str, help=" User defined UCLEMS parameter file (default for standard values)")
    parser.add_argument("--cableparm", type=str, help=" User defined CABLE vegetation parameter file (default for standard values)")
    parser.add_argument("--soilparm", type=str, help=" User defined soil parameter file (default for standard values)")
    parser.add_argument("--vegindex", type=str, help=" User defined vegetation indices for user vegetation (default for standard values)")
    parser.add_argument("--uservegfile", type=str, help=" User defined vegetation map (none for no file)")
    parser.add_argument("--userlaifile", type=str, help=" User defined LAI map (none for no file)")

    parser.add_argument("--machinetype", type=int, choices=[0, 1], help=" Machine type (0=generic, 1=cray)")
    parser.add_argument("--bcsoil", type=int, choices=[0, 1, 2], help=" Initial soil moisture (0=constant, 1=climatology)")

    ###############################################################
    # Specify directories, datasets and executables

    parser.add_argument("--bcdom", type=str, help=" host file prefix for dmode=0, dmode=2 or dmode=3")

    parser.add_argument("--sstfile", type=str, help=" sst file for dmode=1")
    parser.add_argument("--sstinit", type=str, help=" initial conditions file for dmode=1")

    parser.add_argument("--cmip", type=str, choices=['cmip5', 'cmip6'], help=" CMIP scenario")
    parser.add_argument("--rcp", type=str, choices=['historic', 'RCP26', 'RCP45', 'RCP85', 'ssp126', 'ssp245', 'ssp370', 'ssp460', 'ssp585'], help=" RCP/SSP scenario")
    parser.add_argument("--insdir", type=str, help=" install directory")
    parser.add_argument("--hdir", type=str, help=" script directory")
    parser.add_argument("--wdir", type=str, help=" working directory")
    parser.add_argument("--bcdir", type=str, help=" host atmospheric data (for dmode=0, dmode=2 or dmode=3)")
    parser.add_argument("--sstdir", type=str, help=" SST data (for dmode=1)")
    parser.add_argument("--bcsoilfile", type=str, help=" Input file for soil recycle")
    parser.add_argument("--stdat", type=str, help=" eigen and radiation datafiles")

    parser.add_argument("--terread", type=str, help=" path of terread executable")
    parser.add_argument("--igbpveg", type=str, help=" path of igbpveg executable")
    parser.add_argument("--sibveg", type=str, help=" path of sibveg executable")
    parser.add_argument("--ocnbath", type=str, help=" path of ocnbath executable")
    parser.add_argument("--casafield", type=str, help=" path of casafield executable")
    parser.add_argument("--aeroemiss", type=str, help=" path of aeroemiss executable")
    parser.add_argument("--model", type=str, help=" path of globpea executable")
    parser.add_argument("--pcc2hist", type=str, help=" path of pcc2hist executable")

    args = parser.parse_args()

    main(args)
