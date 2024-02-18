import os
import argparse
import sys
import subprocess
from calendar import monthrange
import json

# CCAM simulation python code

def main(inargs):
    "Main CCAM simulation script"

    global d

    print("Reading arguments")
    d = vars(inargs)
    convert_old_settings()
    check_inargs()

    print("Verifying directories")
    create_directories()

    print("Defining simulation settings")
    calc_dt_output()
    calc_res()
    calc_dt_model()

    print("Loop over simulation months ",d['ncountmax'])
    for mth in range(0, d['ncountmax']):

        print("---------------------")

        if d['preprocess_test'] is True:

            # Find date for downscaling
            get_datetime()
            print("Reading date and time ",d['iyr'],d['imth_2digit'])
            d['ofile'] = dict2str('{name}.{iyr}{imth_2digit}')

            # Create surface files if needed
            check_surface_files()

        if d['simulation_test'] is True:

            # Define input and output files
            print("Define input and output filenames")
            prep_iofiles()

            # Determine model parameters
            print("Set model parameters")
            set_mlev_params()
            config_initconds()
            set_nudging()
            set_downscaling()
            set_cloud()
            set_radiation()
            set_ocean()
            set_atmos()
            set_surfc()
            set_aeros()
            set_aquaplanet()

            # Create emission datasets
            create_aeroemiss_file()
            locate_tracer_emissions()

            # Create CCAM namelist and system checks
            print("Create CCAM namelist and perform system checks")
            prepare_ccam_infiles()
            create_input_file()
            check_correct_host()

            # Run CCAM simulation
            print("Run CCAM")
            run_model()

        if d['postprocess_test'] is True:
            print("Post-process CCAM output")
            post_process_output()

        if d['preprocess_test'] is True:
            update_monthyear()
            print("Update simulation date and time")
            update_yearqm()

    print("---------------------")
    print("Simulation loop completed")

    # Check if restart is required
    print("Update simulation restart status")
    restart_flag()

    print("Script completed sucessfully")


def convert_old_settings():
    "Convert dmode for new format"

    dmode_dict = { 0:"nudging_gcm", 1:"sst_only", 2:"nudging_ccam", 3:"sst_6hour",
                   4:"generate_veg", 5:"postprocess", 6:"nudging_gcm_with_sst",
                   7:"aquaplanet1", 8:"aquaplanet2", 9:"aquaplanet3",
                   10:"aquaplanet4", 11:"aquaplanet5", 12:"aquaplanet6",
                   13:"aquaplanet7", 14:"aquaplanet8" }
    d['dmode'] = find_mode(d['dmode'],dmode_dict,"dmode")

    machinetype_dict = { 0:"mpirun", 1:"srun" }
    d['machinetype'] = find_mode(d['machinetype'],machinetype_dict,"machinetype")

    leap_dict = { 0:"noleap", 1:"leap", 2:"360", 3:"auto" }
    d['leap'] = find_mode(d['leap'],leap_dict,"leap")

    sib_dict = { 1:"cable_vary", 3:"cable_sli", 4:"cable_const",
                 5:"cable_modis2020", 6:"cable_sli_modis2020",
                 7:"cable_modis2020_const"}
    d['sib'] = find_mode(d['sib'],sib_dict,"sib")

    aero_dict = { 0:"off", 1:"prognostic" }
    d['aero'] = find_mode(d['aero'],aero_dict,"aero")

    conv_dict = { 0:"2014", 1:"2015a", 2:"2015b", 3:"2017", 4:"Mod2015a", 5:"2021" }
    d['conv'] = find_mode(d['conv'],conv_dict,"conv")

    cldfrac_dict = { 0:"smith", 1:"mcgregor" }
    d['cldfrac'] = find_mode(d['cldfrac'],cldfrac_dict,"cldfrac")

    cloud_dict = { 0:"liq_ice", 1:"liq_ice_rain", 2:"liq_ice_rain_snow_graupel", 3:"lin" }
    d['cloud'] = find_mode(d['cloud'],cloud_dict,"cloud")

    rad_dict = { 0:"SE3", 1:"SE4", 2:"SE4lin" }
    d['rad'] = find_mode(d['rad'],rad_dict,"rad")

    bmix_dict = { 0:"ri", 1:"tke_eps", 2:"hbg" }
    d['bmix'] = find_mode(d['bmix'],bmix_dict,"bmix")

    mlo_dict = { 0:"prescribed", 1:"dynamical" }
    d['mlo'] = find_mode(d['mlo'],mlo_dict,"mlo")

    casa_dict = { 0:"off", 1:"casa_cnp", 2:"casa_cnp_pop" }
    d['casa'] = find_mode(d['casa'],casa_dict,"casa")

    bcsoil_dict = { 0:"constant", 1:"climatology", 2:"recycle" }
    d['bcsoil'] = find_mode(d['bcsoil'],bcsoil_dict,"bcsoil")

    ncout_dict = { 0:"off", 1:"all", 5:"ctm", 7:"basic", 8:"tracer", 9:"all_s", 10:"basic_s" }
    d['ncout'] = find_mode(d['ncout'],ncout_dict,"ncout")

    ncsurf_dict = { 0:"off", 3:"cordex", 4:"cordex_s" }
    d['ncsurf'] = find_mode(d['ncsurf'],ncsurf_dict,"ncsurf")

    nchigh_dict = { 0:"off", 1:"latlon", 2:"latlon_s" }
    d['nchigh'] = find_mode(d['nchigh'],nchigh_dict,"nchigh")

    nctar_dict = { 0:"off", 1:"tar", 2:"delete" }
    d['nctar'] = find_mode(d['nctar'],nctar_dict,"nctar")

    outlevmode_dict = { 0:"pressure", 1:"height", 2:"pressure_height" }
    d['outlevmode'] = find_mode(d['outlevmode'],outlevmode_dict,"outlevmode")

    drsmode_dict = { 0:"off", 1:"on" }
    d['drsmode'] = find_mode(d['drsmode'],drsmode_dict,"drsmode")


def find_mode(nt, nt_dict, nt_name):
    "Correct and test arguments"

    itest = False
    for ct in nt_dict:
        if nt == str(ct):
            nt = nt_dict[ct]
        if nt == nt_dict[ct]:
            itest = True
    if itest is False:
        print("Invalid option for "+nt_name)
        sys.exit(1)
    return nt


def check_inargs():
    "Check all inargs are specified and are internally consistent"

    # split arguments needed for downscaling and arguments needed for post-processing
    # args2common for all modes
    # args2preprocess for preprocess_test
    # args2simulation for simulation_test
    # args2postprocess for postprocessing_test 

    args2common = ['name', 'nproc', 'ncountmax', 'dmode', 'iys', 'ims', 'ids', 'iye', 'ime',
                   'ide', 'ktc', 'ktc_surf', 'ktc_high', 'machinetype', 'cmip', 'insdir',
                   'hdir' ]

    args2preprocess = ['midlon', 'midlat', 'gridres', 'gridsize', 'wdir', 'terread',
                      'igbpveg', 'ocnbath', 'casafield', 'uclemparm',
                      'cableparm', 'vegindex', 'soilparm', 'uservegfile', 'userlaifile',
                      'bcsoilfile', 'nnode', 'sib', 'aero', 'conv', 'cloud', 'rad', 'bmix',
                      'mlo', 'casa', 'cldfrac', 'leap' ]

    args2simulation = ['bcdom', 'bcsoil', 'sstfile', 'sstinit', 'bcdir', 'sstdir', 'stdat',
                       'aeroemiss', 'model', 'tracer', 'rad_year' ]

    args2postprocess = ['minlat', 'maxlat', 'minlon', 'maxlon', 'reqres', 'outlevmode',
                        'plevs', 'mlevs', 'dlevs', 'drsmode', 'drsdomain', 'model_id',
                        'contact', 'rcm_version_id', "drsproject", 'pcc2hist', 'ncout',
                        'nctar', 'ncsurf', 'nchigh' ]

    # determine what simulation modes should be active

    d['preprocess_test'] = False
    if d['dmode'] != "postprocess":
        d['preprocess_test'] = True

    d['simulation_test'] = False
    if not d['dmode'] in ["generate_veg", "postprocess"]:
        d['simulation_test'] = True

    d['postprocess_test'] = False
    if d['dmode'] != "generate_veg":
        d['postprocess_test'] = True

    # check arguments

    for i in args2common:
        if not i in d.keys():
            print('Missing input argument --'+i)
            sys.exit(1)

    if d['preprocess_test'] is True:
        for i in args2preprocess:
            if not i in d.keys():
                print('Missing input argument --'+i)
                sys.exit(1)

    if d['simulation_test'] is True:
        for i in args2simulation:
            if not i in d.keys():
                print('Missing input argument --'+i)
                sys.exit(1)

    if d['postprocess_test'] is True:
        for i in args2postprocess:
            if not i in d.keys():
                print('Missing input argument --'+i)
                sys.exit(1)


    # process some input options

    d['plevs'] = d['plevs'].replace(',', ', ')
    d['mlevs'] = d['mlevs'].replace(',', ', ')
    d['dlevs'] = d['dlevs'].replace(',', ', ')

    if d['dmode'] in ["aquaplanet1", "aquaplanet2", "aquaplanet3",
                      "aquaplanet4", "aquaplanet5", "aquaplanet6",
                      "aquaplanet7", "aquaplanet8"]:
        d['aero'] = "off"
        d['mlo'] = "prescribed"

    if d['mlo'] == "prescribed":
        d['use_depth'] = 'F'
    elif d['mlo'] == "dynamical":
        d['use_depth'] = 'T'
    else:
        raise ValueError("Invalid choice for mlo")

    if d['gridres'] == -999.:
        d['gridres'] = 112.*90./d['gridsize']
        print(dict2str('-> Update gridres to {gridres}'))
        if d['minlat'] == -999.:
            d['minlat'] = -90.
        if d['maxlat'] == -999.:
            d['maxlat'] = 90.
        if d['minlon'] == -999.:
            d['minlon'] = 0.
        if d['maxlon'] == -999.:
            d['maxlon'] = 360.

    d['domain'] = dict2str('{gridsize}_{midlon}_{midlat}_{gridres}km')
    d['inv_schmidt'] = float(d['gridres']) * float(d['gridsize']) / (112. * 90.)

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

    # store input rad_year as rad_year_input
    d['rad_year_input'] = d['rad_year']


def create_directories():
    "Create output directories and go to working directory"

    dirname = dict2str('{hdir}')
    if not os.path.isdir(dirname):
        print("-> Creating ",dirname)
        os.mkdir(dirname)

    os.chdir(dirname)

    for dirname in ['OUTPUT', 'RESTART', 'vegdata']:
        if not os.path.isdir(dirname):
            print("-> Creating ",dirname)
            os.mkdir(dirname)

    if d['outlevmode'] in ["pressure", "pressure_height"]:
        dirname = 'daily'
        if not os.path.isdir(dirname):
            print("-> Creating ",dirname)
            os.mkdir(dirname)

    if d['outlevmode'] in ["height", "pressure_height"]:
        dirname = 'daily_h'
        if not os.path.isdir(dirname):
            print("-> Creating ",dirname)
            os.mkdir(dirname)

    if (d['ktc_surf']>0) and (d['ncsurf']!="off"):
        dirname = 'cordex'
        if not os.path.isdir(dirname):
            print("-> Creating ",dirname)
            os.mkdir(dirname)

    if (d['ktc_high']>0) and (d['nchigh']!="off"):
        dirname = 'highfreq'
        if not os.path.isdir(dirname):
            print("-> Creating ",dirname)
            os.mkdir(dirname)

    if d['dmode'] == "postprocess":
        run_cmdline('rm -f {hdir}/restart5.qm')    
        dirname = dict2str('{hdir}/OUTPUT')
        if not os.path.isdir(dirname):
            raise ValueError("dmode=postprocess requires existing data in OUTPUT directory")
    else:
        run_cmdline('rm -f {hdir}/restart.qm')    
        dirname = dict2str('{wdir}')
        if not os.path.isdir(dirname):
            print("-> Creating ",dirname)
            os.mkdir(dirname)

    # change to working directory, depending on dmode
    os.chdir(dirname)


def calc_dt_output():
    "Calculate model output timestep"

    # raw cc output frequency (mins)
    d['dtout'] = 360  
    if d['ktc'] < d['dtout']:
        d['dtout'] = d['ktc']

    # need hourly output for CTM
    if d['ncout'] == "ctm":
        if d['dtout'] > 60:
            print("-> Adjusting ncout for CTM to 60 mins")
            d['dtout'] = 60 


def calc_res():
    "Calculate resolution for high resolution area"

    # GRIDRES IN UNITS OF METERS
    gridres_m = d['gridres']*1000. 
    d['gridres_m'] = gridres_m

    res = d['reqres']
    if res == -999.:
        res = gridres_m/112000.
        print("-> Adjust reqres to ",res)
    d['res'] = res

    if d['minlat'] == -999.:
        d['minlat'] = d['midlat']-gridres_m*d['gridsize']/200000.
        if d['minlat'] < -90.:
            d['minlat'] = -90.
        print(dict2str("-> Adjust minlat to {minlat}"))

    if d['maxlat'] == -999.:
        d['maxlat'] = d['midlat']+gridres_m*d['gridsize']/200000.
        if d['maxlat'] > 90.:
            d['maxlat'] = 90.
        print(dict2str("-> Adjust maxlat to {maxlat}"))

    if d['minlon'] == -999.:
        d['minlon'] = d['midlon']-gridres_m*d['gridsize']/200000.
        if d['minlat'] == -90.:
            d['minlon'] = 0.
        if d['maxlat'] == 90.:
            d['minlon'] = 0.
        print(dict2str("-> Adjust minlon to {minlon}"))

    if d['maxlon'] == -999.:
        d['maxlon'] = d['midlon']+gridres_m*d['gridsize']/200000.
        if d['minlat'] == -90.:
            d['maxlon'] = 360.
        if d['maxlat'] == 90.:
            d['maxlon'] = 360.
        print(dict2str("-> Adjust maxlon to {maxlon}"))


def calc_dt_model():
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
    test_surf = d['dtout']
    test_high = d['dtout']
    if d['ktc_surf']>0:
        test_surf = d['ktc_surf']
    if d['ktc_high']>0:
        test_high = d['ktc_high']
    for dx in sorted(d_dxdt):
        if (d['gridres_m']>=dx) and (60*d['dtout']%d_dxdt[dx]==0) and (60*test_surf%d_dxdt[dx]==0) and (60*test_high%d_dxdt[dx]==0):
            d['dt'] = d_dxdt[dx]

    if d['gridres_m'] < 50:
        raise ValueError("Minimum grid resolution of 50m has been exceeded")

    if d['ktc']%d['dtout'] != 0:
        raise ValueError("ktc must be a multiple of dtout")

    if d['ktc_surf'] > 0:
        if d['dtout']%d['ktc_surf'] != 0:
            raise ValueError("dtout must be a multiple of ktc_surf")

    if d['ktc_high'] > 0:
        if d['dtout']%d['ktc_high'] != 0:
            raise ValueError("dtout must be a multiple of ktc_high")


def get_datetime():
    "Determine relevant dates and timesteps for running model"

    # Load year.qm with current simulation year:
    fname = dict2str('{hdir}/year.qm')
    if os.path.exists(fname):
        yyyydd = open(fname).read()
        if len(yyyydd) == 8:
            d['iyr'] = int(yyyydd[0:4])
            d['imth'] = int(yyyydd[4:6])
            d['iday'] = int(yyyydd[6:8])
        else:
            d['iyr'] = int(yyyydd[0:4])
            d['imth'] = int(yyyydd[4:6])
            d['iday'] = 1
        #print("ATTENTION:")
        #print(dict2str("Simulation start date taken from {hdir}/year.qm"))
        #print("Start date: "+str(d['iyr'])+mon_2digit(d['imth'])+mon_2digit(d['iday']))
        #print("If this is the incorrect start date, please delete year.qm")
    else:
        d['iyr'] = d['iys']
        d['imth'] = d['ims']
        d['iday'] = d['ids']

    # Abort run at finish year:
    sdate = d['iyr']*10000 + d['imth']*100 + d['iday']
    edate = d['iye']*10000 + d['ime']*100 + d['ide']

    if (sdate>edate) and (d['dmode']!="postprocess"):
        raise ValueError("CCAM simulation already completed. Delete year.qm to restart.")

    iyr = d['iyr']
    imth = d['imth']

    # Calculate previous month:
    if imth == 1:
        d['imthlst'] = 12
        d['iyrlst'] = iyr-1
    else:
        d['imthlst'] = imth-1
        d['iyrlst'] = iyr

    d['imthlst_2digit'] = mon_2digit(d['imthlst'])
    d['imth_2digit'] = mon_2digit(d['imth'])

    # radiation year
    if d['rad_year_input'] == 0:
        d['use_rad_year'] = '.false.'
        d['rad_year'] = d['iyr']
    else:
        d['use_rad_year'] = '.true.'
        d['rad_year'] = d['rad_year_input']

    if (d['preprocess_test'] is True) and (d['simulation_test'] is False):
        # Usually applied for generate_veg.  preprocessing usually only
        # requires monthly temporal resolution
        if d['leap'] == "auto":
            d['leap'] = "leap"

def check_surface_files():
    "Ensure surface datasets exist"

    testfail = False
    if not os.path.exists('custom.qm'):
        testfail = True
    else:
        filename = open('custom.qm', 'r')
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
        if dict2str('{cmip}\n') != filename.readline():
            testfail = True
        if dict2str('{rcp}\n') != filename.readline():
            testfail = True
        if dict2str('{sib}\n') != filename.readline():
            testfail = True
        filename.close()
    if testfail is True:
        print("Create surface data")
        run_cable_all()

    for fname in ['topout', 'bath', 'casa']:
        if not os.path.exists(dict2str('{hdir}/vegdata/'+fname+'{domain}')):
            print("Create surface data")
            run_cable_all()

    testfail = False
    for mon in range(1, 13):
        if (d['cmip']=="cmip5") or (d['sib']=="cable_const") or (d['sib']=='cable_modis_2020_const'):
            fname = dict2str('{hdir}/vegdata/veg{domain}.'+mon_2digit(mon))
        else:
            fname = dict2str('{hdir}/vegdata/veg{domain}.{iyr}.'+mon_2digit(mon))
        if (not os.path.exists(fname)) or (check_correct_landuse(fname) is True):
            testfail = True
    if testfail is True:
        print("Update land-surface data")
        run_cable_land()


    d['vegin'] = dict2str('{hdir}/vegdata')
    if (d['cmip']=="cmip5") or (d['sib']=="cable_const") or (d['sib']=="cable_modis2020_const"):
        # Fixed land-use
        d['vegfile'] = dict2str('veg{domain}.{imth_2digit}')
    else:
        # Use same year as LAI will not change.  Only the area fraction
        d['vegfile'] = dict2str('veg{domain}.{iyr}.{imth_2digit}')


def run_cable_all():
    "Generate topography and land-use files for CCAM"

    run_cmdline('rm -f {hdir}/vegdata/*')
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
    filename.write(dict2str('{cmip}\n'))
    filename.write(dict2str('{rcp}\n'))
    filename.write(dict2str('{sib}\n'))    
    filename.close()


def run_topo():

    print("-> Generating topography file")
    write2file('top.nml', top_template(), mode='w+')
    if d['machinetype'] == "srun":
        run_cmdline('srun -n 1 {terread} < top.nml > terread.log')
    else:
        run_cmdline('{terread} < top.nml > terread.log')
    xtest = (subprocess.getoutput('grep -o --text "terread completed successfully" terread.log')
             == "terread completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running terread. Check terread.log"))


def run_land():

    #default will disable change_landuse
    d['change_landuse'] = ""

    # CABLE land-use
    # determine if time-varying
    if (d['sib']!="cable_const") and (d['sib']!="cable_modis2020_const"):
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

    if d['change_landuse'] == "":
        print("-> Generating CABLE land-use data (varying)")
    else:
        print("-> Generating CABLE land-use data (constant)")

    # use MODIS2020 dataset
    if (d['sib']=="cable_modis2020") or (d['sib']=="cable_sli_modis2020") or (d['sib']=="cable_modis2020_const"):
        write2file('igbpveg.nml', igbpveg_template2(), mode='w+')
    else:
        write2file('igbpveg.nml', igbpveg_template(), mode='w+')
        
    # Run IGBPVEG
    if d['machinetype'] == "srun":
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" OMP_STACKSIZE=1024m srun -n 1 -c {nnode} {igbpveg} -s 5000 < igbpveg.nml > igbpveg.log')
    else:
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" OMP_STACKSIZE=1024m {igbpveg} -s 5000 < igbpveg.nml > igbpveg.log')

    # Check for errors
    xtest = (subprocess.getoutput('grep -o --text "igbpveg completed successfully" igbpveg.log') == "igbpveg completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running igbpveg.  Check igbpveg.log for details"))
    run_cmdline('mv -f topsib{domain} topout{domain}')


def run_ocean():

    print("-> Processing bathymetry data")
    write2file('ocnbath.nml', ocnbath_template(), mode='w+')
    if d['machinetype'] == "srun":
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" OMP_STACKSIZE=1024m srun -n 1 -c {nnode} {ocnbath} -s 5000 < ocnbath.nml > ocnbath.log')
    else:
        run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" OMP_STACKSIZE=1024m {ocnbath} -s 5000 < ocnbath.nml > ocnbath.log')
    xtest = (subprocess.getoutput('grep -o --text "ocnbath completed successfully" ocnbath.log')
             == "ocnbath completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running ocnbath. Check ocnbath.log"))


def run_carbon():

    print("-> Processing CASA data")
    if d['machinetype'] == "srun":
        run_cmdline('srun -n 1 {casafield} -t topout{domain} -i {insdir}/vegin/casaNP_gridinfo_1dx1d.nc -o casa{domain} > casafield.log')
    else:
        run_cmdline('{casafield} -t topout{domain} -i {insdir}/vegin/casaNP_gridinfo_1dx1d.nc -o casa{domain} > casafield.log')
    xtest = (subprocess.getoutput('grep -o --text "casafield completed successfully" casafield.log')
             == "casafield completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running casafield.  Check casafield.log for details"))


def prep_iofiles():
    "Prepare input and output files"

    # Define restart file:
    d['ifile'] = dict2str('Rest{name}.{iyrlst}{imthlst_2digit}')

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

    if d['dmode'] == "sst_only":
        d['mesonest'] = 'error'

    if d['dmode'] == "aquaplanet1":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet2":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet3":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet4":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet5":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet6":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet7":
        d['mesonest'] = 'error'
    if d['dmode'] == "aquaplanet8":
        d['mesonest'] = 'error'

    # Define restart file:
    d['restfile'] = dict2str('Rest{name}.{iyr}{imth_2digit}')

    # Check for errors
    if d['cmip'] == "cmip5":
        if d['rcp'] == "historic":
            if d['iyr'] >= 2005:
                raise ValueError(dict2str("Historical period finished at 2004.  Consider selecting a future RCP."))
    elif d['cmip'] == "cmip6":
        if d['rcp'] == "historic":
            if d['iyr'] >= 2015:
                raise ValueError(dict2str("Historical period finished at 2014.  Consider selecting a future SSP."))

    # Decade start and end:
    d['ddyear'] = int(int(d['rad_year']/10)*10)
    d['deyear'] = int(d['ddyear'] + 9)

    # Define ozone infile:
    if d['cmip'] == "cmip5":
        if (d['rcp']=="historic") or (d['iyr']<2005):
            d['ozone'] = dict2str('{stdat}/{cmip}/historic/pp.Ozone_CMIP5_ACC_SPARC_{ddyear}-{deyear}_historic_T3M_O3.nc')
        else:
            if d['iyr'] > 2099:
                d['ozone'] = dict2str('{stdat}/{cmip}/{rcp}/pp.Ozone_CMIP5_ACC_SPARC_2090-2099_{rcp}_T3M_O3.nc')
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
    d_mlev_modlolvl = {27:24, 35:32, 54:48, 72:64, 108:96, 144:128}

    d.update({'nmr': 1, 'acon': 0.00, 'bcon': 0.02, 'eigenv': d_mlev_eigenv[d['mlev']],
              'mlolvl': d_mlev_modlolvl[d['mlev']]})


def config_initconds():
    "Configure initial condition file"

    d['nrungcm'] = 0

    if d['iyr'] == d['iys']:

        if d['imth'] == d['ims']:

            if d['dmode'] in ["nudging_gcm", "nudging_ccam", "sst_6hour", "nudging_gcm_with_sst"]:
                d.update({'ifile': d['mesonest']})
            elif d['dmode'] == "sst_only":
                d.update({'ifile': d['sstinit']})
            else:
                d.update({'ifile': "error"})

            if d['bcsoil'] == "constant":
                d['nrungcm'] = -1
            if d['bcsoil'] == "climatology":
                print("Import soil from climatology")
                d['nrungcm'] = -14
                d.update({'bcsoilfile': dict2str('{insdir}/vegin/sm{imth_2digit}')})
                check_file_exists(d['bcsoilfile']+'.000000')
            elif d['bcsoil'] == "recycle":
                print("Recycle soil from input file")
                d['nrungcm'] = -4
                check_file_exists(d['bcsoilfile']+'.000000')


    # prepare ifile
    if d['dmode'] in ["nudging_gcm", "nudging_ccam", "sst_6hour", "nudging_gcm_with_sst"]:
        fpath = dict2str('{bcdir}/{mesonest}')
        if os.path.exists(fpath):
            run_cmdline('ln -s '+fpath+' .')
            cname = fpath
        elif os.path.exists(fpath+'.000000'):
            run_cmdline('ln -s '+fpath+'.?????? .')
            cname = fpath+".000000"
        elif os.path.exists(fpath+'.tar'):
            run_cmdline('tar xvf '+fpath+'.tar')
            cname = fpath
            if not os.path.exists(cname):
                cname = fpath+".000000"
        if not os.path.exists(cname):
            raise ValueError(dict2str('Cannot locate file {bcdir}/{mesonest}'))
        if d['leap'] == "auto":
            calendar_noleap = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep calendar | grep -o --text noleap') == "noleap")
            calendar_360 = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep calendar | grep -o --text 360_day') == "360_day")
            calendar_gregorian = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep calendar | grep -o --text gregorian') == "gredorian")
            if calendar_noleap is True:
                d['leap'] = "noleap"
            if calendar_360 is True:
                d['leap'] = "360"
            if calendar_gregorian is True:
                d['leap'] = "leap"
            if d['leap'] == "auto":
                raise ValueError("ERROR: Cannot assign calendar for leap=auto")
            print(dict2str('Assign calendar {leap}'))

    if (d['dmode']=="sst_only") and (d['iyr']==d['iys']) and (d['imth']==d['ims']):
        fpath = dict2str('{sstinit}')
        if os.path.exists(fpath):
            run_cmdline('ln -s '+fpath+' .')
        elif os.path.exists(fpath+'.000000'):
            run_cmdline('ln -s '+fpath+'.?????? .')
        elif os.path.exists(fpath+'.tar'):
            run_cmdline('tar xvf '+fpath+'.tar')
        else:
            raise ValueError(dict2str('ERROR: Cannot locate file {sstinit}'))

    # Check ifile
    fname = d['ifile']
    if not fname=="error":
        if not os.path.exists(fname):
            fname = d['ifile']+'.000000'
        if not os.path.exists(fname):
            raise ValueError(dict2str('ERROR: Cannot locate {ifile} or {ifile}.000000'))

    # Calculate number of days in current month:
    iyr = d['iyr']
    imth = d['imth']
    if d['leap'] == "auto":
        raise ValueError("ERROR: Unable to assign calendar with leap=auto")
    elif d['leap'] == "noleap":
        d['nleap'] = 0
        d['ndays'] = monthrange(iyr, imth)[1]
        if imth == 2:
            d['ndays'] = 28 #leap year turned off
    elif d['leap'] == "leap":
        d['nleap'] = 1
        d['ndays'] = monthrange(iyr, imth)[1]
    elif d['leap'] == "360":
        d['nleap'] = 2
        d['ndays'] = 30
    else:
        raise ValueError("ERROR: Unknown option for leap")
    
    d['eday'] = d['ndays']
    if (d['iyr']==d['iye']) and (d['imth']==d['ime']):
        if (d['ide']>d['ndays']) or (d['ide']<1):
            raise ValueError("End day ide is invalid.")
        d['eday'] = d['ide']
    if (d['iday']>d['ndays']) or (d['iday']<1):
        raise ValueError("Start day ids is invalid.")
    d['ndays'] = d['eday'] - d['iday'] + 1

    d['ihs'] = 0
    if not fname=="error":
        testtime = int(subprocess.getoutput('ncdump -c '+fname+' | grep time | grep units | head -1 | cut -d= -f2 | cut -d" " -f5 | cut -d: -f1'))
        if testtime > 12:
            testtime = 24 - testtime
        d['ihs'] = testtime


def set_nudging():
    "Set nudging strength parameters"

    if d['dmode'] == "nudging_gcm":
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})

    elif d['dmode'] == "sst_only":
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})

    elif d['dmode'] == "nudging_ccam":
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': 1, 'ktopdav': 0, 'sigramplow': 0.05})

    elif d['dmode'] == "sst_6hour":
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})

    elif d['dmode'] == "nudging_gcm_with_sst":
        d.update({'mbd_base': 20, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})
    else:
        d.update({'mbd_base': 0, 'mbd_maxgrid': 999999, 'mbd_maxscale': 3000,
                  'kbotdav': -850, 'ktopdav': -10, 'sigramplow': 0.05})

def set_downscaling():
    "Set downscaling parameters"

    if d['dmode'] == "nudging_gcm":
        d.update({'nud_p': 1, 'nud_q': 0, 'nud_t': 1,
                  'nud_uv': 1, 'mfix': 3, 'mfix_qg': 3, 'mfix_aero': 3,
                  'nbd': 0, 'mbd': d['mbd_base'], 'nud_aero': 0,
                  'mh_bs':3})
    elif d['dmode'] == "sst_only":
        d.update({'nud_p': 0, 'nud_q': 0, 'nud_t': 0,
                  'nud_uv': 0, 'mfix': 3, 'mfix_qg': 3, 'mfix_aero': 3,
                  'nbd': 0, 'mbd': 0, 'nud_aero': 0,
                  'mh_bs':3})
    elif d['dmode'] == "nudging_ccam":
        d.update({'nud_p': 1, 'nud_q': 1, 'nud_t': 1,
                  'nud_uv': 1, 'mfix': 3, 'mfix_qg': 3, 'mfix_aero': 3,
                  'nbd': 0, 'mbd': d['mbd_base'], 'nud_aero': 1,
                  'mh_bs':3})
    elif d['dmode'] == "sst_6hour":
        d.update({'nud_p': 0, 'nud_q': 0, 'nud_t': 0,
                  'nud_uv': 0, 'mfix': 3, 'mfix_qg': 3, 'mfix_aero': 3,
                  'nbd': 0, 'mbd': d['mbd_base'], 'nud_aero': 0,
                  'mh_bs':3})
    elif d['dmode'] == "nudging_gcm_with_sst":
        d.update({'nud_p': 1, 'nud_q': 0, 'nud_t': 1,
                  'nud_uv': 1, 'mfix': 3, 'mfix_qg': 3, 'mfix_aero': 3,
                  'nbd': 0, 'mbd': d['mbd_base'], 'nud_aero': 0,
                  'mh_bs':3})
    else:
        d.update({'nud_p': 0, 'nud_q': 0, 'nud_t': 0,
                  'nud_uv': 0, 'mfix': 3, 'mfix_qg': 3, 'mfix_aero': 3,
                  'nbd': 0, 'mbd': 0, 'nud_aero': 0,
                  'mh_bs':3})

def set_cloud():
    "Cloud microphysics settings"

    d['diaglevel_cloud'] = 0
    if (d['ncout']=="all") or (d['ncout']=="all_s"):
        d['diaglevel_cloud'] = 9


    if d['cloud'] == "liq_ice":
        d.update({'ncloud': 0, 'rcrit_l': 0.75, 'rcrit_s': 0.85, 'nclddia': 12})
    if d['cloud'] == "liq_ice_rain":
        d.update({'ncloud': 2, 'rcrit_l': 0.75, 'rcrit_s': 0.85, 'nclddia': 12})
    if d['cloud'] == "liq_ice_rain_snow_graupel":
        d.update({'ncloud': 3, 'rcrit_l': 0.75, 'rcrit_s': 0.85, 'nclddia': 12})
    if d['cloud'] == "lin":
        d.update({'ncloud': 100, 'rcrit_l': 0.825, 'rcrit_s': 0.825, 'nclddia': 8})

    if d['cldfrac'] == "mcgregor":
        d.update({'rcrit_l': 0.85, 'rcrit_s': 0.85, 'nclddia': 3})

def set_radiation():
    "Radiation settings"

    if d['rad'] == "SE3":
        d.update({'linecatalog_form': 'hitran_2000',
                  'continuum_form': 'ckd2.4',
                  'do_co2_10um': '.false.',
                  'liqradmethod': 0, 'iceradmethod': 1})
    if d['rad'] == "SE4":
        d.update({'linecatalog_form': 'hitran_2012',
                  'continuum_form': 'mt_ckd2.5',
                  'do_co2_10um': '.true.',
                  'liqradmethod': 0, 'iceradmethod': 5})
    if d['rad'] == "SE4lin":
        d.update({'linecatalog_form': 'hitran_2012',
                  'continuum_form': 'mt_ckd2.5',
                  'do_co2_10um': '.true.',
                  'liqradmethod': 6, 'iceradmethod': 4})


def set_ocean():
    "Ocean physics settings"

    if d['mlo'] == "prescribed":
        #Interpolated SSTs
        d.update({'nmlo': 0, 'mbd_mlo': 0, 'nud_sst': 0,
                  'nud_sss': 0, 'nud_ouv': 0, 'nud_sfh': 0,
                  'kbotmlo': -40})

    else:
        #Dynanical Ocean
        if d['dmode'] in ["nudging_gcm", "sst_only", "sst_6hour", "nudging_gcm_with_sst"]:
            # Downscaling mode - GCM or SST-only:
            d.update({'nmlo': -3, 'mbd_mlo': 60, 'nud_sst': 1,
                      'nud_sss': 0, 'nud_ouv': 0, 'nud_sfh': 0,
                      'kbotmlo': -40})
        elif d['dmode'] == "nudging_ccam":
            # Downscaling CCAM:
            d.update({'nmlo': -3, 'mbd_mlo': 60, 'nud_sst': 1,
                      'nud_sss': 1, 'nud_ouv': 1, 'nud_sfh': 1,
                      'kbotmlo': -40})
        else:
            raise ValueError(dict2str('ERROR: mlo not supported for dmode {dmode}'))
            d.update({'nmlo': -3, 'mbd_mlo': 60, 'nud_sst': 1,
                      'nud_sss': 1, 'nud_ouv': 1, 'nud_sfh': 1,
                      'kbotmlo': -40})


def set_atmos():
    "Atmospheric physics settings"

    # CABLE options
    if d['sib'] == "cable_vary":
        d.update({'nsib': 7, 'soil_struc': 0, 'fwsoil_switch': 3,
                  'cable_litter': 0, 'gs_switch': 1})
    if d['sib'] == "cable_sli":
        d.update({'nsib': 7, 'soil_struc': 1, 'fwsoil_switch': 3,
                  'cable_litter': 1, 'gs_switch': 1})
    if d['sib'] == "cable_const":
        d.update({'nsib': 7, 'soil_struc': 0, 'fwsoil_switch': 3,
                  'cable_litter': 0, 'gs_switch': 1})
    if d['sib'] == "cable_modis2020":
        d.update({'nsib': 7, 'soil_struc': 0, 'fwsoil_switch': 3,
                  'cable_litter': 0, 'gs_switch': 1})
    if d['sib'] == "cable_sli_modis2020":
        d.update({'nsib': 7, 'soil_struc': 1, 'fwsoil_switch': 3,
                  'cable_litter': 1, 'gs_switch': 1})
    if d['sib'] == "cable_modis2020_const":
        d.update({'nsib': 7, 'soil_struc': 0, 'fwsoil_switch': 3,
                  'cable_litter': 0, 'gs_switch': 1})

    # CASA options        
    if d['casa'] == "off":
        d.update({'ccycle': 0, 'proglai': 0, 'progvcmax': 0, 'cable_pop': 0})
    if d['casa'] == "casa_cnp":
        d.update({'ccycle': 3, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 0})
    if d['casa'] == "casa_cnp_pop":
        d.update({'ccycle': 2, 'proglai': 1, 'progvcmax': 1, 'cable_pop': 1})

    # Input files for vegetation
    if (d['cmip']=="cmip5") or (d['sib']=="cable_const") or (d['sib']=="cable_modis2020_const"):
        d.update({'vegin': dict2str('{hdir}/vegdata'),
                  'vegfile': dict2str('veg{domain}.{imth_2digit}')})
    else:
        # Use same year as LAI will not change.  Only the area fraction
        d.update({'vegin': dict2str('{hdir}/vegdata'),
                  'vegfile': dict2str('veg{domain}.{iyr}.{imth_2digit}')})

    if d['bmix'] == "ri":
        d.update({'nvmix': 3, 'nlocal': 6, 'amxlsq': 100., 'wg_tau': 3.,
                  'wg_prob': 0.5})
    if d['bmix'] == "tke_eps":
        if d['mlo'] == "dynamical":
            d.update({'nvmix': 9, 'nlocal': 7, 'amxlsq': 9., 'wg_tau': 3.,
                      'wg_prob': 0.5})
        else:
            d.update({'nvmix': 6, 'nlocal': 7, 'amxlsq': 9., 'wg_tau': 3.,
                      'wg_prob': 0.5})
    if d['bmix'] == "hbg":
        d.update({'nvmix': 7, 'nlocal': 6, 'amxlsq': 9., 'wg_tau': 3.,
                  'wg_prob': 0.5})

    d.update({'ngwd': -5, 'helim': 800., 'fc2': 1., 'sigbot_gwd': 0., 'alphaj': '0.000001'})

    if d['conv'] == "2015b":
        d.update({'ngwd': -20, 'helim': 1600., 'fc2': -0.5, 'sigbot_gwd': 1., 'alphaj': '0.025'})

    if d['conv'] == "2017":
        d.update({'ngwd': -20, 'helim': 1600., 'fc2': -0.5, 'sigbot_gwd': 1., 'alphaj': '0.025'})

    if d['conv'] == "2021":
        d.update({'ngwd': -20, 'helim': 1600., 'fc2': -0.5, 'sigbot_gwd': 1., 'alphaj': '0.025'})


def set_surfc():
    "Prepare surface files"

    if d['ktc_surf'] > 0:
        d.update({'tbave': int(d['ktc_surf']*60/d['dt'])})
    else:
        d.update({'tbave': 0})	

    if d['ktc_high'] > 0:
        d.update({'tbave10': int(d['ktc_high']*60/d['dt'])})
    else:
        d.update({'tbave10': 0})	


def set_aeros():
    "Prepare aerosol files"

    # Decade start and end:
    d['ddyear'] = int(int(d['rad_year']/10)*10)
    d['deyear'] = int(d['ddyear'] + 9)

    if d['aero'] == "off":
        # Aerosols turned off
        d.update({'iaero': 0, 'sulffile' : 'none', 'lin_aerosolmode' : 0})

    if d['aero'] == "prognostic":
        # Prognostic aerosols
        d.update({'iaero': 2, 'sulffile': 'aero.nc', 'lin_aerosolmode' : 1})

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
            elif d['iyr'] < 2100:
                aero = {'so2_anth': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_anthropogenic_{ddyear}*.nc'),
                        'so2_ship': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_ships_{ddyear}*.nc'),
                        'so2_biom': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_biomassburning_{ddyear}*.nc'),
                        'bc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_anthropogenic_{ddyear}*.nc'),
                        'bc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_ships_{ddyear}*.nc'),
                        'bc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_biomassburning_{ddyear}*.nc'),
                        'oc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_anthropogenic_{ddyear}*.nc'),
                        'oc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_ships_{ddyear}*.nc'),
                        'oc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_biomassburning_{ddyear}*.nc')}
            else:
                aero = {'so2_anth': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_anthropogenic_2090*.nc'),
                        'so2_ship': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_ships_2090*.nc'),
                        'so2_biom': get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_SO2_biomassburning_2090*.nc'),
                        'bc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_anthropogenic_2090*.nc'),
                        'bc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_ships_2090*.nc'),
                        'bc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_BC_biomassburning_2090*.nc'),
                        'oc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_anthropogenic_2090*.nc'),
                        'oc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_ships_2090*.nc'),
                        'oc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/IPCC_emissions_{rcp}_OC_biomassburning_2090*.nc')}
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
                elif d['iyr'] < 2100:
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
                    aero = {'so2_anth': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'so2_ship': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'so2_biom': get_fpath('{stdat}/{cmip}/{rcp}/SO2-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'bc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'bc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'bc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/BC-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'oc_anth':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'oc_ship':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-anthro_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc'),
                            'oc_biom':  get_fpath('{stdat}/{cmip}/{rcp}/OC-em-openburning-share_input4MIPs_emissions_ScenarioMIP_IAMC-{rcplabel}-{rcp}-1-1_gn_2090*.nc')}
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

    if d['aero'] != "off":
        print("Create aerosol emissions")
        write2file('aeroemiss.nml', aeroemiss_template(), mode='w+')

        # Remove any existing sulffile:
        run_cmdline('rm -rf {sulffile}')

        # Create new sulffile:
        if d['machinetype'] == "srun":
            run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" OMP_STACKSIZE=1024m srun -n 1 -c {nnode} {aeroemiss} -o {sulffile} < aeroemiss.nml > aero.log')
        else:
            run_cmdline('env OMP_NUM_THREADS={nnode} OMP_WAIT_POLICY="PASSIVE" OMP_STACKSIZE=1024m {aeroemiss} -o {sulffile} < aeroemiss.nml > aero.log')

        xtest = (subprocess.getoutput('grep -o --text "aeroemiss completed successfully" aero.log')
                 == "aeroemiss completed successfully")
        if xtest is False:
            raise ValueError(dict2str("An error occured while running aeroemiss.  Check aero.log for details"))


def locate_tracer_emissions():
    "Locate tracer emissions"

    d['mfix_tr'] = 0
    if d['tracer'] != "off":
        d['mfix_tr'] = 1
        filename = dict2str('{tracer}/tracer.txt')
        if not os.path.exists(filename):
            raise ValueError(dict2str("Cannot locate tracer.txt in {tracer}"))

        run_cmdline('ln -s {tracer}/* .')


def set_aquaplanet():
    "Define aquaplanet settings"

   # set-up aquaplanet
    d['nhstest'] = 0
    if d['dmode'] == "aquaplanet1":
        d['nhstest'] = -1
    if d['dmode'] == "aquaplanet2":
        d['nhstest'] = -2
    if d['dmode'] == "aquaplanet3":
        d['nhstest'] = -3
    if d['dmode'] == "aquaplanet4":
        d['nhstest'] = -4
    if d['dmode'] == "aquaplanet5":
        d['nhstest'] = -5
    if d['dmode'] == "aquaplanet6":
        d['nhstest'] = -6
    if d['dmode'] == "aquaplanet7":
        d['nhstest'] = -7
    if d['dmode'] == "aquaplanet8":
        d['nhstest'] = -8

    d['io_in'] = 1
    if not (d['nhstest']==0):
        if (d['iyr']==d['iys']) and (d['imth']==d['ims']):
            d['io_in'] = 10


def create_input_file():
    "Write arguments to the CCAM 'input' namelist file"

    # check start time
    d['ihour'] = 0
    if (d['iyr']==d['iys']) and (d['imth']==d['ims']):
        d['ihour'] = d['ihs']
        if (d['ihs']<0) or (d['ihs']>23):
            raise ValueError("Start hour ihs is invalid.")

    # Number of steps between output:
    d['nwt'] = int(d['dtout']*60/d['dt'])

    # Number of steps in run:
    d['ntau'] = int(((d['ndays']-1)*86400+(24-d['ihour'])*3600)/d['dt'])

    # Start date string:
    d['kdates'] = str(d['iyr']*10000 + d['imth']*100 + d['iday'])
    d['ktimes'] = str(d['ihour']*100)

    write2file('input', input_template_1(), mode='w+')

    if d['conv'] == "2014":
        write2file('input', input_template_c2014())
    if d['conv'] == "2015a":
        write2file('input', input_template_c2015a())
    if d['conv'] == "2015b":
        write2file('input', input_template_c2015b())
    if d['conv'] == "2017":
        write2file('input', input_template_c2017())
    if d['conv'] == "Mod2015a":
        write2file('input', input_template_c2015m())
    if d['conv'] == "2021":
        write2file('input', input_template_c2021())

    if d['tracer'] != "off":
        write2file('input', input_template_3())

    write2file('input', input_template_4())


def prepare_ccam_infiles():
    "Prepare and check CCAM input data"

    if not d['ifile']=="error":
        if not os.path.exists(d['ifile']) and not os.path.exists(d['ifile']+'.000000'):
            raise ValueError(dict2str('Cannot locate {ifile} or {ifile}.000000. ')+
                             'If this is the start of a new run, please check that year.qm has been deleted')

    if d['dmode'] in ["nudging_gcm", "nudging_ccam", "sst_6hour", "nudging_gcm_with_sst"]:
        if not os.path.exists(d['mesonest']) and not os.path.exists(d['mesonest']+'.000000'):
            raise ValueError(dict2str('Cannot locate {mesonest} or {mesonest}.000000'))

    for file in ['topout{domain}', '{vegfile}']:
        check_file_exists(dict2str('{vegin}/'+file))

    if d['nmlo'] != "prescribed" and not os.path.exists(dict2str('{vegin}/bath{domain}')):
        raise ValueError(dict2str('Cannot locate {vegin}/bath{domain}'))

    if d['aero']!="off" and not os.path.exists(d['sulffile']):
        raise ValueError('Cannot locate '+d['sulffile'])

    d['namip'] = 0
    if d['dmode'] in ['sst_only', 'nudging_gcm_with_sst']:
        fname = dict2str('{sstdir}/{sstfile}')
        if not os.path.exists(fname):
            raise ValueError('Cannot locate '+fname)
        testrealheader = (subprocess.getoutput('ncdump -c '+fname+' | grep -o --text real_header') == "real_header")
        if testrealheader is False:
            raise ValueError('Invalid sstfile '+fname+'.  Must use a cubic grid.')
        # check if sea-ice is present in sstfile
        sictest = (subprocess.getoutput('ncdump -c '+fname+' | grep -o --text sic') == "sic")
        if sictest is True:
            d['nmaip'] = 14
        else:
            d['namip'] = 11


def check_correct_host():
    "Check if host is CCAM"

    if d['dmode'] in ["nudging_gcm", "nudging_ccam", "nudging_gcm_with_sst"]:
        for fname in [d['mesonest'], d['mesonest']+'.000000']:
            if os.path.exists(fname):
                ccam_host = (subprocess.getoutput('ncdump -c '+fname+' | grep -o --text :version') == ":version")
                break
        if ccam_host is True and (d['dmode']=="nudging_gcm"):
            raise ValueError('CCAM is the host model. Use dmode=nudging_ccam')
        if ccam_host is False and (d['dmode']=="nudging_ccam"):
            raise ValueError('CCAM is not the host model. Use dmode=nudging_gcm')
        if ccam_host is True and (d['dmode']=="nudging_gcm_with_sst"):
            raise ValueError('CCAM is the host model. Use dmode=nudging_ccam')

#    if d['dmode'] == "nudging_gcm":
#        if d['inv_schmidt'] < 0.2:
#            raise ValueError('CCAM grid stretching is too high for dmode=nudging_gcm.  Try reducing grid resolution or increasing grid size')

    if d['dmode'] in ["sst_only", "aquaplanet1", "aquaplanet2", "aquaplanet3",
                      "aquaplanet4", "aquaplanet5", "aquaplanet6",
                      "aquaplanet7", "aquaplanet8"]:
        if d['inv_schmidt'] < 0.2:
            print(dict2str("inv_schmidt = {inv_schmidt}"))
            raise ValueError('CCAM grid stretching is too high for dmode=sst_only.  Try reducing grid resolution or increasing grid size')

    if (d['dmode'] == "nudging_ccam") or (d['dmode'] == "nudging_gcm"):
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

    cable_data = (subprocess.getoutput('ncdump -c '+fname+' | grep -o --text cableversion') == "cableversion")
    if cable_data is False:
        testfail = True

    return testfail


def run_model():
    "Execute the CCAM model"

    if d['machinetype'] == "srun":
        run_cmdline('srun -n {nproc} {model} > prnew.{kdates}.{name} 2> err.{iyr}')
    else:
        run_cmdline('mpirun -np {nproc} {model} > prnew.{kdates}.{name} 2> err.{iyr}')

    prfile = dict2str('prnew.{kdates}.{name}')
    xtest = (subprocess.getoutput('grep -o --text "globpea completed successfully" '+prfile)
             == "globpea completed successfully")
    if xtest is False:
        raise ValueError(dict2str("An error occured while running CCAM.  Check prnew.{kdates}.{name} for details"))

    fname = dict2str('{mesonest}.000000')
    if os.path.exists(fname):
        run_cmdline('rm {mesonest}.??????')
    fname = dict2str('{mesonest}')
    if os.path.exists(fname):
        run_cmdline('rm {mesonest}')

    if d['dmode'] != "postprocess":
        fname = dict2str('{hdir}/daily/pr_{ofile}.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/daily/*_{ofile}.nc')
        fname = dict2str('{hdir}/daily/{ofile}.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/daily/{ofile}.nc')
        fname = dict2str('{hdir}/daily/ccam_{iyr}{imth_2digit}01.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/daily/ccam_{iyr}{imth_2digit}??.nc')
        fname = dict2str('{hdir}/daily_h/pr_{ofile}.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/daily_h/*_{ofile}.nc')
        fname = dict2str('{hdir}/daily_h/{ofile}.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/daily_h/{ofile}.nc')
        fname = dict2str('{hdir}/cordex/pr_surf.{ofile}.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/cordex/*_surf.{ofile}.nc')
        fname = dict2str('{hdir}/highfreq/pr_freq.{ofile}.nc')
        if os.path.exists(fname):
            run_cmdline('rm {hdir}/highfreq/*_freq.{ofile}.nc')

    if d['ihour'] > 0:
        print("Incomplete month detected - Removing spin-up output")
        run_cmdline('rm {ofile}.??????')
        fname = dict2str('surf.{ofile}.000000')
        if os.path.exists(fname):
            run_cmdline('rm surf.{ofile}.??????')
        fname = dict2str('freq.{ofile}.000000')
        if os.path.exists(fname):
            run_cmdline('rm freq.{ofile}.??????')

def post_process_output():
    "Post-process the CCAM model output"
    
    hy = d['iys']
    hm = 1
    ftest = True
    newoutput = False
    newoutput_h = False
    newcordex = False
    newhighfreq = False
    d['drs_host_scenario'] = "error"
    d['drs_host_ensemble'] = "error"
    d['drs_host_name'] = "error"
    while ftest:
        d['histmonth'] = mon_2digit(hm)
        d['histyear'] = hy
        d['histfile'] = dict2str('{name}.{histyear}{histmonth}')
	    
        # standard output
        outlist = [""]
        if d['outlevmode']=="pressure":
            outlist = ["pressure"]
        if d['outlevmode']=="height":
            outlist = ["height"]
        if d['outlevmode']=="pressure_height":
            outlist = ["pressure", "height"]
        
        for outindex in range(len(outlist)):
            d['vertout'] = outlist[outindex]

            if d['vertout']=="pressure":
                d['use_plevs'] = 'T'
                d['use_meters'] = 'F'
                d['dailydir'] = 'daily'
            elif d['vertout']=="height":
                d['use_plevs'] = 'F'
                d['use_meters'] = 'T'
                d['dailydir'] = 'daily_h'
            else:
                raise ValueError('Unknown option for vertical levels')


            if d['ncout'] == "all":
                fname = dict2str('{hdir}/{dailydir}/pr_{histfile}.nc')
                if not os.path.exists(fname):
                    tarflag = False
                    cname = dict2str('{histfile}.000000')
                    if not os.path.exists(cname):
                        tname = dict2str('{histfile}.tar')
                        if os.path.exists(tname):
                            tarflag = True
                            run_cmdline('tar xvf '+tname)    
                    if os.path.exists(cname):
                        calc_drs_host(cname)
                        print("Process ",dict2str('{vertout}')," (daily) output for ",dict2str('{histyear}{histmonth}'))
                        write2file('cc.nml', cc_template_1(), mode='w+')
                        if d['machinetype'] == "srun":
                            run_cmdline('srun -n {nproc} {pcc2hist} --cordex --multioutput > pcc2hist.log')
                        else:
                            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex --multioutput > pcc2hist.log')
                        xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" pcc2hist.log')
                                 == "pcc2hist completed successfully")
                        if xtest is False:
                            raise ValueError(dict2str("An error occured while running pcc2hist.  Check pcc2hist.log for details"))
                        run_cmdline('mv *_{histfile}.nc {hdir}/{dailydir}')
                        if tarflag is True:
                            run_cmdline('rm {histfile}.??????')
                        ftest = False
                        if d['vertout'] == "pressure":
                            newoutput = True
                        if d['vertout'] == "height":
                            newoutput_h = True

            if d['ncout'] == "ctm":
                if not (d['vertout']=="pressure"):
                    raise ValueError("CTM output requires pressure levels")
                fname = dict2str("{hdir}/daily/ccam_{histyear}{histmonth}01.nc")
                if not os.path.exists(fname):
                    tarflag = False
                    cname = dict2str('{histfile}.000000')
                    if not os.path.exists(cname):
                        tname = dict2str('{histfile}.tar')
                        if os.path.exists(tname):
                            tarflag = True
                            run_cmdline('tar xvf '+tname)    
                    if os.path.exists(cname):
                        calc_drs_host(cname)
                        print("Process CTM output for ",dict2str('{histyear}{histmonth}'))
                        calendar_noleap = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep calendar | grep -o --text noleap') == "noleap")
                        calendar_360 = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep calendar | grep -o --text 360_day') == "360_day")
                        calendar_test = "leap"
                        if calendar_noleap is True:
                            calendar_test = "noleap"
                        if calendar_360 is True:
                            calendar_test = "360"
                        print("Calendar found "+calendar_test)
                        idaystart = 1
                        if (hy == d['iys']) and (hm == d['ims']):
                            idaystart = d['ids']
                        if calendar_test == "noleap":
                            idayend = monthrange(hy, hm)[1]
                            if hm == 2:
                                idayend=28
                        if calendar_test == "leap":
                            idayend = monthrange(hy, hm)[1]
                        if calendar_test == "360":
                            idayend = 30
                        if (hy == d['iye']) and (hm == d['ime']):
                            idayend = d['ide']
                        for iday in range(idaystart, idayend+1):
                            d['cday'] = mon_2digit(iday)
                            d['iend'] = (iday-idaystart+1)*1440
                            d['istart'] = (iday-idaystart)*1440
                            d['outctmfile'] = dict2str("ccam_{histyear}{histmonth}{cday}.nc")
                            write2file('cc.nml', cc_template_2(), mode='w+')
                            if d['machinetype'] == "srun":
                                run_cmdline('srun -n {nproc} {pcc2hist} > pcc2hist_ctm.log')
                            else:
                                run_cmdline('mpirun -np {nproc} {pcc2hist} > pcc2hist_ctm.log')
                            xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" pcc2hist_ctm.log')
                                     == "pcc2hist completed successfully")
                            if xtest is False:
                                raise ValueError(dict2str("An error occured while running pcc2hist.  Check pcc2hist_ctm.log for details"))
                        run_cmdline('mv ccam_{histyear}{histmonth}??.nc {hdir}/daily')
                        if tarflag is True:
                            run_cmdline('rm {histfile}.??????')
                        ftest = False
                        # No DRS output for CTM formatting
                        newoutput = False

            if d['ncout'] == "basic":
                fname = dict2str('{hdir}/{dailydir}/pr_{histfile}.nc')
                if not os.path.exists(fname):
                    tarflag = False
                    cname = dict2str('{histfile}.000000')
                    if not os.path.exists(cname):
                        tname = dict2str('{histfile}.tar')
                        if os.path.exists(tname):
                            tarflag = True
                            run_cmdline('tar xvf '+tname)    
                    if os.path.exists(cname):
                        calc_drs_host(cname)
                        print("Process ",dict2str('{vertout}')," (daily) output for ",dict2str('{histyear}{histmonth}'))
                        write2file('cc.nml', cc_template_6(), mode='w+')
                        if d['machinetype'] == "srun":
                            run_cmdline('srun -n {nproc} {pcc2hist} --cordex --multioutput > pcc2hist.log')
                        else:
                            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex --multioutput > pcc2hist.log')
                        xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" pcc2hist.log')
                                 == "pcc2hist completed successfully")
                        if xtest is False:
                            raise ValueError(dict2str("An error occured running pcc2hist. Check pcc2hist.log"))
                        run_cmdline('mv *{histfile}.nc {hdir}/{dailydir}')
                        if tarflag is True:
                            run_cmdline('rm {histfile}.??????')
                        ftest = False
                        if d['vertout'] == "pressure":
                            newoutput = True
                        if d['vertout'] == "height":
                            newoutput_h = True

            if d['ncout'] == "tracer":
                fname = dict2str('{hdir}/{dailydir}/trav0001_{histfile}.nc')
                if not os.path.exists(fname):
                    tarflag = False
                    cname = dict2str('{histfile}.000000')
                    if not os.path.exists(cname):
                        tname = dict2str('{histfile}.tar')
                        if os.path.exists(tname):
                            tarflag = True
                            run_cmdline('tar xvf '+tname)
                    if os.path.exists(cname):
                        calc_drs_host(cname)
                        print("Process ",dict2str('{vertout}')," (daily) output for ",dict2str('{histyear}{histmonth}'))
                        write2file('cc.nml', cc_template_7(), mode='w+')
                        if d['machinetype'] == "srun":
                            run_cmdline('srun -n {nproc} {pcc2hist} --cordex --multioutput > pcc2hist.log')
                        else:
                            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex --multioutput > pcc2hist.log')
                        xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" pcc2hist.log')
                                 == "pcc2hist completed successfully")
                        if xtest is False:
                            raise ValueError(dict2str("An error occured running pcc2hist. Check pcc2hist.log"))
                        run_cmdline('mv *{histfile}.nc {hdir}/{dailydir}')
                        if tarflag is True:
                            run_cmdline('rm {histfile}.??????')
                        ftest = False
                        if d['vertout'] == "pressure":
                            newoutput = True
                        if d['vertout'] == "height":
                            newoutput_h = True

            if d['ncout'] == "all_s":
                fname = dict2str('{hdir}/{dailydir}/{histfile}.nc')
                if not os.path.exists(fname):
                    tarflag = False
                    cname = dict2str('{histfile}.000000')
                    if not os.path.exists(cname):
                        tname = dict2str('{histfile}.tar')
                        if os.path.exists(tname):
                            tarflag = True
                            run_cmdline('tar xvf '+tname)
                    if os.path.exists(cname):
                        calc_drs_host(cname)
                        print("Process ",dict2str('{vertout}')," (daily) output for ",dict2str('{histyear}{histmonth}'))
                        write2file('cc.nml', cc_template_1(), mode='w+')
                        if d['machinetype'] == "srun":
                            run_cmdline('srun -n {nproc} {pcc2hist} --cordex > pcc2hist.log')
                        else:
                            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > pcc2hist.log')
                        xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" pcc2hist.log')
                                 == "pcc2hist completed successfully")
                        if xtest is False:
                            raise ValueError(dict2str("An error occured while running pcc2hist.  Check pcc2hist.log for details."))
                        run_cmdline('mv *_{histfile}.nc {hdir}/{dailydir}')
                        if tarflag is True:
                            run_cmdline('rm {histfile}.??????')
                        ftest = False
                        if d['vertout'] == "pressure":
                            newoutput = True
                        if d['vertout'] == "height":
                            newoutput_h = True

            if d['ncout'] == "basic_s":
                fname = dict2str('{hdir}/{dailydir}/{histfile}.nc')
                if not os.path.exists(fname):
                    tarflag = False
                    cname = dict2str('{histfile}.000000')
                    if not os.path.exists(cname):
                        tname = dict2str('{histfile}.tar')
                        if os.path.exists(tname):
                            tarflag = True
                            run_cmdline('tar xvf '+tname)
                    if os.path.exists(cname):
                        calc_drs_host(cname)
                        print("Process ",dict2str('{vertout}')," (daily) output for ",dict2str('{histyear}{histmonth}'))
                        write2file('cc.nml', cc_template_6(), mode='w+')
                        if d['machinetype'] == "srun":
                            run_cmdline('srun -n {nproc} {pcc2hist} --cordex > pcc2hist.log')
                        else:
                            run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > pcc2hist.log')
                        xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" pcc2hist.log')
                                 == "pcc2hist completed successfully")
                        if xtest is False:
                            raise ValueError(dict2str("An error occured running pcc2hist. Check pcc2hist.log"))
                        run_cmdline('mv *{histfile}.nc {hdir}/{dailydir}')
                        if tarflag is True:
                            run_cmdline('rm {histfile}.??????')
                        ftest = False
                        if d['vertout'] == "pressure":
                            newoutput = True
                        if d['vertout'] == "height":
                            newoutput_h = True
                    
        # store output
        if (d['nctar']=="off") and (d['dmode']!="postprocess"):
            cname = dict2str('{histfile}.000000')
            if os.path.exists(cname):
                run_cmdline('mv {histfile}.?????? {hdir}/OUTPUT')
                ftest = False

        if d['nctar'] == "tar":
            cname = dict2str('{histfile}.000000')
            if os.path.exists(cname):
                run_cmdline('tar cvf {hdir}/OUTPUT/{histfile}.tar {histfile}.??????')
                run_cmdline('rm {histfile}.??????')
                ftest = False

        if d['nctar'] == "delete":
            cname = dict2str('{histfile}.000000')
            if os.path.exists(cname):
                run_cmdline('rm {histfile}.??????')
                ftest = False                    

        # surface files
        if d['ncsurf'] == "cordex":
            fname = dict2str('{hdir}/cordex/pr_surf.{histfile}.nc')
            if not os.path.exists(fname):
                tarflag = False
                cname = dict2str('surf.{histfile}.000000')
                if not os.path.exists(cname):
                    tname = dict2str('surf.{histfile}.tar')
                    if os.path.exists(tname):
                        tarflag = True
                        run_cmdline('tar xvf '+tname)    
                if os.path.exists(cname):
                    calc_drs_host(cname)
                    print("Process CORDEX output for ",dict2str('{histyear}{histmonth}'))
                    d['ktc_units'] = d['ktc_surf']
                    cname = dict2str('surf.{histfile}.000000')
                    seconds_check = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep units | grep -o --text seconds') == "seconds")
                    if seconds_check is True:
                        d['ktc_units'] = d['ktc_units']*60
                    write2file('cc.nml', cc_template_5(), mode='w+')
                    if d['machinetype'] == "srun":
                        run_cmdline('srun -n {nproc} {pcc2hist} --cordex --multioutput > surf.pcc2hist.log')
                    else:
                        run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex --multioutput > surf.pcc2hist.log')
                    xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" surf.pcc2hist.log')
                             == "pcc2hist completed successfully")
                    if xtest is False:
                        raise ValueError(dict2str("An error occured running pcc2hist. Check surf.pcc2hist.log"))
                    run_cmdline('mv *_surf.{histfile}.nc {hdir}/cordex')
                    if tarflag is True:
                        run_cmdline('rm {histfile}.??????')
                    ftest = False
                    newcordex = True

        if d['ncsurf'] == "cordex_s":
            fname = dict2str('{hdir}/cordex/surf.{histfile}.nc')
            if not os.path.exists(fname):
                tarflag = False
                cname = dict2str('surf.{histfile}.000000')
                if not os.path.exists(cname):
                    tname = dict2str('surf.{histfile}.tar')
                    if os.path.exists(tname):
                        tarflag = True
                        run_cmdline('tar xvf '+tname)
                if os.path.exists(cname):
                    calc_drs_host(cname)
                    print("Process CORDEX output for ",dict2str('{histyear}{histmonth}'))
                    d['ktc_units'] = d['ktc_surf']
                    cname = dict2str('surf.{histfile}.000000')
                    seconds_check = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep units | grep -o --text seconds') == "seconds")
                    if seconds_check is True:
                        d['ktc_units'] = d['ktc_units']*60
                    write2file('cc.nml', cc_template_5(), mode='w+')
                    if d['machinetype'] == "srun":
                        run_cmdline('srun -n {nproc} {pcc2hist} --cordex > surf.pcc2hist.log')
                    else:
                        run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > surf.pcc2hist.log')
                    xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" surf.pcc2hist.log')
                             == "pcc2hist completed successfully")
                    if xtest is False:
                        raise ValueError(dict2str("An error occured running pcc2hist. Check surf.pcc2hist.log"))
                    run_cmdline('mv *_surf.{histfile}.nc {hdir}/cordex')
                    if tarflag is True:
                        run_cmdline('rm {histfile}.??????')
                    ftest = False
                    newcordex = True

        # store output
        if d['ktc_surf'] > 0:
            if (d['nctar']=="off") and (d['dmode']!="postprocess"):
                cname = dict2str('surf.{histfile}.000000')
                if os.path.exists(cname):
                    run_cmdline('mv surf.{histfile}.?????? {hdir}/OUTPUT')
                    ftest = False

            if d['nctar'] == "tar":
                cname = dict2str('surf.{histfile}.000000')
                if os.path.exists(cname):
                    run_cmdline('tar cvf {hdir}/OUTPUT/surf.{histfile}.tar surf.{histfile}.??????')
                    run_cmdline('rm surf.{histfile}.??????')
                    ftest = False

            if d['nctar'] == "delete":
                cname = dict2str('surf.{histfile}.000000')
                if os.path.exists(cname):
                    run_cmdline('rm surf.{histfile}.??????')
                    ftest = False

        # high-frequency files
        if d['nchigh'] == "latlon":
            fname = dict2str('{hdir}/highfreq/rnd_freq.{histfile}.nc')
            if not os.path.exists(fname):
                tarflag = False
                cname = dict2str('freq.{histfile}.000000')
                if not os.path.exists(cname):
                    tname = dict2str('freq.{histfile}.tar')
                    if os.path.exists(tname):
                        tarflag = True
                        run_cmdline('tar xvf '+tname)    
                if os.path.exists(cname):
                    calc_drs_host(cname)
                    print("Process high-frequency output for ",dict2str('{histyear}{histmonth}'))
                    d['ktc_units'] = d['ktc_high']
                    cname = dict2str('freq.{histfile}.000000')
                    seconds_check = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep units | grep -o --text seconds') == "seconds")
                    if seconds_check is True:
                        d['ktc_units'] = d['ktc_units']*60
                    write2file('cc.nml', cc_template_3(), mode='w+')
                    if d['machinetype'] == "srun":
                        run_cmdline('srun -n {nproc} {pcc2hist} --cordex --multioutput > freq.pcc2hist.log')
                    else:
                        run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex --multioutput > freq.pcc2hist.log')
                    xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" freq.pcc2hist.log')
                             == "pcc2hist completed successfully")
                    if xtest is False:
                        raise ValueError(dict2str("An error occured running pcc2hist. Check freq.pcc2hist.log"))
                    run_cmdline('mv *_freq.{histfile}.nc {hdir}/highfreq')
                    if tarflag is True:
                        run_cmdline('rm {histfile}.??????')
                    ftest = False
                    newhighfreq = True

        if d['nchigh'] == "latlon_s":
            fname = dict2str('{hdir}/highfreq/freq.{histfile}.nc')
            if not os.path.exists(fname):
                tarflag = False
                cname = dict2str('freq.{histfile}.000000')
                if not os.path.exists(cname):
                    tname = dict2str('freq.{histfile}.tar')
                    if os.path.exists(tname):
                        tarflag = True
                        run_cmdline('tar xvf '+tname)
                if os.path.exists(cname):
                    calc_drs_host(cname)
                    print("Process high-frequency output for ",dict2str('{histyear}{histmonth}'))
                    d['ktc_units'] = d['ktc_high']
                    cname = dict2str('freq.{histfile}.000000')
                    seconds_check = (subprocess.getoutput('ncdump -c '+cname+' | grep time | grep units | grep -o --text seconds') == "seconds")
                    if seconds_check is True:
                        d['ktc_units'] = d['ktc_units']*60
                    write2file('cc.nml', cc_template_3(), mode='w+')
                    if d['machinetype'] == "srun":
                        run_cmdline('srun -n {nproc} {pcc2hist} --cordex > freq.pcc2hist.log')
                    else:
                        run_cmdline('mpirun -np {nproc} {pcc2hist} --cordex > freq.pcc2hist.log')
                    xtest = (subprocess.getoutput('grep -o --text "pcc2hist completed successfully" freq.pcc2hist.log')
                             == "pcc2hist completed successfully")
                    if xtest is False:
                        raise ValueError(dict2str("An error occured running pcc2hist. Check freq.pcc2hist.log"))
                    run_cmdline('mv *_freq.{histfile}.nc {hdir}/highfreq')
                    if tarflag is True:
                        run_cmdline('rm {histfile}.??????')
                    ftest = False
                    newhighfreq = True


        # store output
        if d['ktc_high'] > 0:
            if (d['nctar']=="off") and (d['dmode']!="postprocess"):
                cname = dict2str('freq.{histfile}.000000')
                if os.path.exists(cname):
                    run_cmdline('mv freq.{histfile}.?????? {hdir}/OUTPUT')
                    ftest = False

            if d['nctar'] == "tar":
                cname = dict2str('freq.{histfile}.000000')
                if os.path.exists(cname):
                    run_cmdline('tar cvf {hdir}/OUTPUT/freq.{histfile}.tar freq.{histfile}.??????')
                    run_cmdline('rm freq.{histfile}.??????')
                    ftest = False

            if d['nctar'] == "delete":
                cname = dict2str('freq.{histfile}.000000')
                if os.path.exists(cname):
                    run_cmdline('rm freq.{histfile}.??????')
                    ftest = False

        hm = hm + 1
        if hm > 12:
            # create JSON file for DRS if new cordex formatted output was created
            if d['drsmode'] == "on":
                create_drs(newoutput, newoutput_h, newcordex, newhighfreq) 
            # Advace year
            hm = 1
            hy = hy + 1
        if (hy>d['iye']) and (ftest==True):
            ftest = False
            if d['dmode'] == "postprocess":
                print("CCAM post-processing is complete")
                write2file(d['hdir']+'/restart5.qm', "Complete", mode='w+')
                sys.exit(0)


def calc_drs_host(fname):

    d['drs_host_scenario'] = "error"
    d['drs_host_ensemble'] = "error"
    d['drs_host_name'] = "error"
    d['drs_host_institution'] = "error"

    driving_model_id_test = subprocess.getoutput('ncdump -c '+fname+' | grep driving_model_id | cut -d\" -f2')
    if driving_model_id_test != "":
        d['drs_host_name'] = driving_model_id_test

    driving_model_ensemble_number_test = subprocess.getoutput('ncdump -c '+fname+' | grep driving_model_ensemble_number | cut -d\" -f2')
    if driving_model_ensemble_number_test != "":
        d['drs_host_ensemble'] = driving_model_ensemble_number_test

    driving_experiment_name_test = subprocess.getoutput('ncdump -c '+fname+' | grep driving_experiment_name | cut -d\" -f2')
    if driving_experiment_name_test != "":
        d['drs_host_scenario'] = driving_experiment_name_test

    driving_institution_id_test = subprocess.getoutput('ncdump -c '+fname+' | grep driving_institution_id | cut -d\" -f2')
    if driving_institution_id_test != "":
        d['drs_host_institution'] = driving_institution_id_test


def create_drs(newoutput, newoutput_h, newcordex, newhighfreq):

    for dirname in ['daily', 'daily_h', 'cordex', 'highfreq']:
        d['drsdirname'] = dirname

        # check if new file has been created
        newtest = False
        if dirname == "daily":
            newtest = newoutput
        elif dirname == "daily_h":
            newtest = newoutput_h
        elif dirname == "cordex":
            newtest = newcordex
        elif dirname == "highfreq":
            newtest = newhighfreq
        if newtest is True:         
            # check if all files are present    

            ctest = True
            tm = 1

            while (tm<=12) and (ctest is True):    
                d['histmonth'] = mon_2digit(tm)
                tm = tm + 1

                fname = "error"
                if (dirname == "daily") and (d['outlevmode'] in ["pressure", "pressure_height"]):
                    fname = dict2str('{hdir}/{drsdirname}/pr_{name}.{histyear}{histmonth}.nc')
                elif (dirname == "daily_h") and (d['outlevmode'] in ["height", "pressure_height"]):
                    fname = dict2str('{hdir}/{drsdirname}/pr_{name}.{histyear}{histmonth}.nc')
                elif (dirname == "cordex") and (d['ncsurf']!="off"):
                    fname = dict2str('{hdir}/{drsdirname}/pr_surf.{name}.{histyear}{histmonth}.nc')
                elif (dirname == "highfreq") and (d['nchigh']!="off"):
                    fname = dict2str('{hdir}/{drsdirname}/pr_freq.{name}.{histyear}{histmonth}.nc')
                if not os.path.exists(fname):
                    ctest = False

            # all files exist (ctest) and a new file was created (newtest)
            if ctest is True:
                hres = d['gridres']
                project = d['drsproject']
                drsinstitution = "unknown"
                if d['drs_host_name'] != "error":
                    d['drshost'] = d['drs_host_name']
                
                # Patch for old CORDEX format
                patch_dict = { ECMWF:ERA5, CSIRO:ACCESS-ESM1-5,
                               CSIRO-ARCCSS:ACCESS-CM2, CMCC-CMCC:ESM2,
                               CNRM-CERFACS:CNRM-ESM2-1,
                               EC-Earth-Consortium:EC-Earth3, NCAR:CESM2,
                               NCC:NorESM2-MM }
                for test_institution in patch_dict:
                    test_model = patch_dict[test_institution]
                    test_name = test_institution+'-'+test_model
                    if d['drshost'] == test_name:
                        d['drshost'] = test_model
                        drsinstitution = test_institution
                    print("Replace metadata with ",d['drshost']," and ",drsinstitution)

                # default
                if d['cmip'] == "cmip5":
                    if d['histyear'] <= 2005:
                        cmip_scenario = "historical"
                    else:
                        cmip_scenario = dict2str('{rcp}')
                elif d['cmip'] == 'cmip6':
                    if d['histyear'] <= 2014:
                        cmip_scenario = "historical"
                    else:
                        cmip_scenario = dict2str('{rcp}')
                if (d['drshost']=='ECMWF-ERA5') or (d['drshost']=='ERA5'):
                        cmip_scenario="evaluation"

                # Use file metadata if avaliable
                if d['drs_host_ensemble'] != "error":
                    d['drsensemble'] = d['drs_host_ensemble']
                if d['drs_host_scenario'] != "error":
                    cmip_scenario = d['drs_host_scenario']
                if d['drs_host_institution'] != "error":
                    drsinstitution = d['drs_host_institution']

                # Recombine host insitution and model name for compatibility
                # depreciate this line below when driving_institution_id is
                # avaliable with AXIOM
                d['drshost'] = d['drshost']+'-'+drsinstitution

                payload = dict(
                    input_files=dict2str('{hdir}/{drsdirname}/*nc'),
                    output_directory=dict2str('{hdir}/drs_{drsdirname}/'),
                    start_year=dict2str('{histyear}'), end_year=dict2str('{histyear}'),
                    output_frequency='1M',
                    project=project,
                    model=dict2str('{drshost}'),
                    ensemble=dict2str('{drsensemble}'),
                    variables=[],
                    domain=dict2str('{drsdomain}'),
                    cordex=True,
                    input_resolution=hres,
                    model_id=dict2str('{model_id}'),
                    driving_experiment_name=cmip_scenario,
                    contact=dict2str('{contact}'),
                    rcm_version_id=dict2str('{rcm_version_id}'),
                    preprocessor="ccam",
                    postprocessor="ccam"
                )

                f = open(dict2str('{hdir}/{drsdirname}/payload.json.{histyear}'), 'w', encoding='utf-8')
                json.dump(payload,f,ensure_ascii=False,indent=4)
                f.close()


def update_monthyear():
    # update counter for next simulation month and remove old files
    iyr = d['iyr']
    imth = d['imth']

    d['iday'] = d['eday'] + 1
    if d['leap'] == "auto":
        raise ValueError("ERROR: Unable to assign calendar with leap=auto")
    elif d['leap'] == "noleap":
        month_length = monthrange(iyr, imth)[1]
        if imth == 2:
            month_length = 28 #leap year turned off
    elif d['leap'] == "leap":
        month_length = monthrange(iyr, imth)[1]
    elif d['leap'] == "360":
        month_length = 30
    else:
        raise ValueError("ERROR: Unknown option for leap")

    if d['iday'] > month_length:
        d['iday'] = 1
        d['imth'] = d['imth'] + 1

    if d['imth'] < 12:
        fname = dict2str('Rest{name}.{iyrlst}12.000000')
        if os.path.exists(fname):
            run_cmdline('rm Rest{name}.{iyrlst}12.??????')

    if d['imth'] > 12:
        run_cmdline('tar cvf {hdir}/RESTART/Rest{name}.{iyr}12.tar Rest{name}.{iyr}12.??????')
        run_cmdline('rm Rest{name}.{iyr}0?.?????? Rest{name}.{iyr}10.?????? Rest{name}.{iyr}11.??????')
        run_cmdline('rm {name}*{iyr}??')
        run_cmdline('rm {name}*{iyr}??.nc')
        d['imth'] = 1
        d['iyr'] = d['iyr'] + 1


def update_yearqm():
    "Update the year.qm file"

    yyyymmdd = d['iyr'] * 10000 + d['imth'] * 100 + d['iday']
    d['yyyymmdd'] = yyyymmdd
    write2file(d['hdir']+'/year.qm', "{yyyymmdd}", mode='w+')


def restart_flag():
    "Create restart.qm containing flag for restart. This flag signifies that CCAM completed previous month"

    if d['dmode'] == "postprocess":
        write2file(d['hdir']+'/restart5.qm', "True", mode='w+')
    else:	
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

    cmth = int(imth)

    if cmth < 10:
        return '0'+str(cmth)

    return str(cmth)

def top_template():
    "Template for writing top.nml namelist file"

    return """\
    &topnml
     il={gridsize}
     debug=t idia=29 jdia=48 id=2 jd=4
     fileout="topout{domain}" luout=50
     rlong0={midlon} rlat0={midlat} schmidt={inv_schmidt}
     dosrtm=f do1km=t do250=t netout=t topfilt=t    
     filepath10km="{insdir}/vegin"
     filepath1km="{insdir}/vegin"
     filepath250m="{insdir}/vegin"
     filepathsrtm="{insdir}/vegin"
    &end
    """

def igbpveg_template2():
    "Template for writing igbpveg.nml namelist file"

    return """\
    &vegnml
     month=0
     year={iyr}
     topofile="topout{domain}"
     newtopofile="topsib{domain}"
     landtypeout="veg{domain}"
     veg2input="{insdir}/vegin/landcover_2020.nc"
     soilinput="{insdir}/vegin/usda4.img"
     laiinput="{insdir}/vegin"
     albvisinput="{insdir}/vegin/salbvis_landcover2020.nc"
     albnirinput="{insdir}/vegin/salbnir_landcover2020.nc"
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
     natural_maxtile=4
     alb3939=.false.
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
     natural_maxtile=4
     alb3939=.false.
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
     kdate_s={kdates} ktime_s={ktimes} leap={nleap}
     dt={dt} nwt={nwt} ntau={ntau}
     nmaxpr=999999 newtop=1 nrungcm={nrungcm}
     namip={namip} rescrn=1 zo_clearing=1.
     nhstest={nhstest}

     COMMENT='dynamical core'
     epsp=0.1 epsu=0.1 epsh=1.
     precon=-10000 restol=2.e-7 nh=5 knh=9 maxcolour=3
     nstagu=1 khor=0 nhorps=-1 nhorjlm=0 nhor=-151
     mh_bs={mh_bs} ntvd=3

     COMMENT='mass fixer'
     mfix_qg={mfix_qg} mfix={mfix} mfix_aero={mfix_aero}
     mfix_tr={mfix_tr}

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
     synchist=.false. compression=1 io_in={io_in}
     tbave={tbave} tbave10={tbave10} procmode=16 fnproc_bcast_max=24
    &end
    &skyin
     mins_rad=-1 qgmin=2.E-7
     ch_dust=3.E-10 aerosol_u10=1 aero_split=1
     siglow=0.76 sigmid=0.44
     linecatalog_form='{linecatalog_form}'
     continuum_form='{continuum_form}' 
     do_co2_10um={do_co2_10um}
     do_quench=.false.
     remain_rayleigh_bug=.false.     
     use_rad_year={use_rad_year}
     rad_year={rad_year}
     liqradmethod={liqradmethod}
     iceradmethod={iceradmethod}
    &end
    &datafile
     ifile=      '{ifile}'
     mesonest=   '{mesonest}'
     topofile=   '{vegin}/topout{domain}'
     vegfile=    '{vegin}/{vegfile}'
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
     surf_cordex=11 surf_windfarm=1
     diaglevel_cloud={diaglevel_cloud}
     """

    template2 = """
     surfile=    'surf.{ofile}'
     """

    template3 = """
     freqfile=   'freq.{ofile}'
     """

    template4 = """
    &end
    """

    template = template1
    if d['ktc_surf'] > 0:
        template = template + template2
    if d['ktc_high'] > 0:
        template = template + template3
    template = template + template4

    return template

def input_template_c2014():
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
     nclddia={nclddia} nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l={rcrit_l} rcrit_s={rcrit_s}
     lin_aerosolmode={lin_aerosolmode}
    &end
    """

def input_template_c2015a():
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
     nclddia={nclddia} nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l={rcrit_l} rcrit_s={rcrit_s}
     lin_aerosolmode={lin_aerosolmode}
    &end
    """

def input_template_c2015m():
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
     nclddia={nclddia} nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l={rcrit_l} rcrit_s={rcrit_s}
     lin_aerosolmode={lin_aerosolmode}
    &end
    """

def input_template_c2015b():
    "Fourth part of template for 'input' namelist file"

    return """
    &kuonml
     nkuo=23 sig_ct=1. rhcv=0.1 rhmois=0. convfact=1.05 convtime=-2030.60
     alflnd=1.2 alfsea=1.10 fldown=-0.3 iterconv=3 ncvcloud=0 nevapcc=0
     nuvconv=-3
     mbase=4 mdelay=0 methprec=5 nbase=-10 detrain=0.1 entrain=-0.5
     methdetr=-1 detrainx=0. dsig2=0.1 dsig4=1.
     ksc=0 kscsea=0 sigkscb=0.95 sigksct=0.8 tied_con=0. tied_over=2626.
     ldr=1 nstab_cld=0 nrhcrit=10 sigcll=0.95
     nclddia={nclddia} nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l={rcrit_l} rcrit_s={rcrit_s}
     lin_aerosolmode={lin_aerosolmode}
    &end
    """

def input_template_c2017():
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
     nclddia={nclddia} nmr={nmr}
     nevapls=0 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l={rcrit_l} rcrit_s={rcrit_s}
     lin_aerosolmode={lin_aerosolmode}
    &end
    """

def input_template_c2021():
    "Second part of template for 'input' namelist file"

    return """
    &kuonml
     nkuo=21
     alfsea=1.10 alflnd=1.10
     convfact=1.05 convtime=-3030.60
     tied_con=0.85 mdelay=0
     fldown=-0.3
     iterconv=3
     ksc=0 kscsea=0 kscmom=1 dsig2=0.1
     mbase=3 nbase=3
     methprec=5 detrain=0.05 methdetr=-5
     ncvcloud=0
     nevapcc=0 entrain=-0.5
     nuvconv=-3
     rhcv=0. rhmois=0. tied_over=1026.
     nmr={nmr} nclddia={nclddia}
     nevapls=-4 ncloud={ncloud} acon={acon} bcon={bcon}
     rcrit_l={rcrit_l} rcrit_s={rcrit_s}
     lin_aerosolmode={lin_aerosolmode}
    &end
    """

def input_template_3():
    "Tracer emissions part of templat for 'input' namelist file"

    return """
    &trfiles
      tracerlist='tracer.txt'
    &end
    """


def input_template_4():
    "Sixth part of template for 'input' namelist file"

    return """
    &turbnml
     buoymeth=1 tkemeth=1
     mintke=1.5e-4 mineps=1.e-6 minl=5. maxl=500.
     qcmf=1.e-4 ezmin=10.
     ent0=0.5 ent1=0. ent_min=0.001
     be=1. b1=2. b2=0.3333 m0=0.1
     tke_timeave_length={tke_timeave_length}
     wg_tau={wg_tau} wg_prob={wg_prob}
     dvmodmin=0.01 amxlsq={amxlsq}
     ngwd={ngwd} helim={helim} fc2={fc2}
     sigbot_gwd={sigbot_gwd} alphaj={alphaj}
    &end
    &landnml
     proglai={proglai} progvcmax={progvcmax} ccycle={ccycle}
     soil_struc={soil_struc} fwsoil_switch={fwsoil_switch}
     cable_pop={cable_pop} gs_switch={gs_switch} cable_potev=0
     cable_litter={cable_litter}
     ateb_intairtmeth=1 ateb_intmassmeth=2
     ateb_zoroof=0.05 ateb_zocanyon=0.05
    &end
    &mlonml
     mlodiff=11 otaumode=1 mlojacobi=7 mlomfix=1
     usetide=0 mlosigma=6 nodrift=1 oclosure=1
     ocnsmag=0. ocnlap=0.01 zomode=0 ocneps=0.1 ocnepr=1. omaxl=1000.
     mlodiff_numits=6 mlo_adjeta=0 mstagf=0 mlodps=0
     mlo_bs=3 minwater=2. mlo_step=1
     alphavis_seaice=0.95 alphanir_seaice=0.7
     alphavis_seasnw=0.95 alphanir_seasnw=0.7
     rivermd=1
    &end
    &tin &end
    &soilin &end
    """


def cc_template_1():
    "First part of template for 'cc.nml' namelist file"

    template = """\
    &input
     ifile = "{histfile}"
     ofile = "{histfile}.nc"
     hres  = {res}
     kta={ktc}   ktb=999999  ktc=-1
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
     ifile = "{histfile}"
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

    fname = dict2str('{histfile}.000000')
    rsmin_test = (subprocess.getoutput('ncdump -c '+fname+' | grep -o --text rsmin') != "")
    if rsmin_test is True:
        template = template1 + template2
    else:
        template = template1 + template3

    return template


def cc_template_3():
    "Third part of template for 'cc.nml' namelist file"

    template = """\
    &input
     ifile = "freq.{histfile}"
     ofile = "freq.{histfile}.nc"
     hres  = {res}
     kta={ktc_units}   ktb=2999999  ktc=-1
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
    &end
    &histnl
     htype="inst"
     hnames= "uas","vas","tas","hurs","ps","pr"
     hfreq = 1
    &end
    """

    return template

def cc_template_5():
    "Fifth part of template for 'cc.nml' namelist file"

    template = """\
    &input
     ifile = "surf.{histfile}"
     ofile = "surf.{histfile}.nc"
     hres  = {res}
     kta={ktc_units}   ktb=2999999  ktc=-1
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
    &end
    &histnl
     htype="inst"
     hnames= "tas","tasmax","tasmin","pr","ps","psl","huss","hurs","sfcWind","sfcWindmax","clt","sund","rsds","rsdsdir","rlds","hfls","hfss","rsus","rlus","evspsbl","evspsblpot","mrfso","mrros","mrro","mrso","snw","snm","prhmax","prc","rlut","rsdt","rsut","uas","vas","tauu","tauv","ts","zmla","prw","clwvi","clivi","ua1000","va1000","ta1000","zg1000","hus1000","wa1000","ua925","va925","ta925","zg925","hus925","wa925","ua850","va850","ta850","zg850","hus850","wa850","ua700","va700","ta700","zg700","hus700","wa700","ua600","va600","ta600","zg600","hus600","wa600","ua500","va500","ta500","zg500","hus500","wa500","ua400","va400","ta400","zg400","hus400","wa400","ua300","va300","ta300","zg300","hus300","wa300","ua250","va250","ta250","zg250","hus250","wa250","ua200","va200","ta200","zg200","hus200","wa200","clh","clm","cll","snc","snd","siconca","prsn","orog","sftlf","ua50m","va50m","ta50m","hus50m","ua100m","va100m","ua150m","va150m","ua200m","va200m","ua250m","va250m","ua300m","va300m","sftlaf","sfturf","z0","wsgsmax","tsl","mrsol","mrfsol","CAPE","CIN","mrfsos","mrsos","od550aer","tsroof","tsgree","tspav","mrsofc","anthroheat"
     hfreq = 1
    &end
    """

    return template

def cc_template_6():
    "Sixth part of template for 'cc.nml' namelist file"

    template1 = """\
    &input
     ifile="{histfile}"
     ofile="{histfile}.nc"
     hres={res}
     kta={ktc}  ktb=999999  ktc=-1
     minlat={minlat}  maxlat={maxlat}  minlon={minlon}  maxlon={maxlon}
     use_plevs={use_plevs}
     use_meters={use_meters}     
     use_depth={use_depth}
     plevs={plevs}
     mlevs={mlevs}
     dlevs={dlevs}
    &end
    &histnl
     htype="inst"
    """
    template2 = """\
    hnames="pr","ta","ts","ua","va","psl","tas","uas","vas","hurs","orog",\
"tasmax","tasmin","sfcWind","zg","hus","qlg","qfg","wa","theta","omega", \
"cfrac","prw","clwvi","clivi","zmla","ustar", \
"clt","clh","clm","cll","rsds","rlds","rsus","rlus","prgr","prsn","sund", \
"rsut","rlut","rsdt","hfls","hfss","CAPE","CIN","prc", \
"evspsbl","mrro","mrros","snm","hurs","huss","ps","tauu","tauv","snw", \
"snc","snd","siconca","z0","evspsblpot","tdew","tsl","mrsol","mrfsol","orog", \
"alb","sftlf","grid","sdischarge"
     hfreq = 1
    &end
    """
    
    template3 = """\
    hnames="pr","ta","ts","ua","va","psl","tas","uas","vas","hurs","orog",\
"tasmax","tasmin","sfcWind","zg","hus","qlg","qfg","wa","theta","omega", \
"cfrac","prw","clwvi","clivi","zmla","ustar", \
"clt","clh","clm","cll","rsds","rlds","rsus","rlus","prgr","prsn", "sund", \
"rsut","rlut","rsdt","hfls","hfss","CAPE","CIN","prc", \
"evspsbl","mrro","mrros","snm","hurs","huss","ps","tauu","tauv","snw", \
"snc","snd","siconca","z0","evspsblpot","tdew","tsl","mrsol","mrfsol","orog" \
"alb","sftlf","grid","sdischarge","tos","sos","uos","vos","ssh","ocndepth"
     hfreq = 1
    &end
    """

    fname = d['histfile']
    mlo_test = (subprocess.getoutput('ncdump -c '+fname+'.000000 | grep -o --text thetao | head -1') == "thetao")
    print("fname ",fname)
    print("mlo_test ",mlo_test)
    if mlo_test is True:
        template = template1 + template3
    else:
        template = template1 + template2

    return template


def cc_template_7():
    "Tracer part of template for 'cc.nml' namelist file"

    template = """\
    &input
     ifile = "{histfile}"
     ofile = "{histfile}.nc"
     hres  = {res}
     kta={ktc}   ktb=999999  ktc=-1
     minlat = {minlat}, maxlat = {maxlat}, minlon = {minlon},  maxlon = {maxlon}
     use_plevs = F
     use_meters = F
     use_depth = F
    &end
    &histnl
     htype="inst"
     hnames= "tracer"  hfreq = 1
    &end
    """

    return template


if __name__ == '__main__':

    extra_info = """
    Usage:
        python run_ccam.py [-h]

    Author:
        Mitchell Black
    Modifications:
        Marcus Thatcher, marcus.thatcher@csiro.au
        Sonny Truong, sonny.truong@csiro.au	
    """
    description = 'Run the CCAM model'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info,
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--name", type=str, help=" run name")
    parser.add_argument("--nproc", type=int, help=" number of processors")
    parser.add_argument("--nnode", type=int, help=" number of processors per node")
    parser.add_argument("--machinetype", type=str, help=" Machine type (mpirun, srun)")

    parser.add_argument("--midlon", type=float, help=" central longitude of domain")
    parser.add_argument("--midlat", type=float, help=" central latitude of domain")
    parser.add_argument("--gridres", type=float, help=" required resolution (km) of domain")
    parser.add_argument("--gridsize", type=int, help=" cubic grid size")
    parser.add_argument("--mlev", type=int, choices=[27, 35, 54, 72, 108, 144], help=" number of model levels (27, 35, 54, 72, 108 or 144)")

    parser.add_argument("--iys", type=int, help=" start year [YYYY]")
    parser.add_argument("--ims", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], help=" start month [MM]")
    parser.add_argument("--ids", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31], help=" start day [DD]")    
    parser.add_argument("--iye", type=int, help=" end year [YYYY]")
    parser.add_argument("--ime", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], help=" end month [MM]")
    parser.add_argument("--ide", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31], help=" end day [DD]")    
    parser.add_argument("--leap", type=str, help=" Define calendar (noleap, leap, 360, auto)")
    parser.add_argument("--ncountmax", type=int, help=" Number of months before resubmit")

    parser.add_argument("--cmip", type=str, choices=['cmip5', 'cmip6'], help=" CMIP scenario")
    parser.add_argument("--rcp", type=str, choices=['historic', 'RCP26', 'RCP45', 'RCP85', 'ssp126', 'ssp245', 'ssp370', 'ssp460', 'ssp585'], help=" RCP/SSP scenario")

    parser.add_argument("--minlat", type=float, help=" output min latitude (degrees)")
    parser.add_argument("--maxlat", type=float, help=" output max latitude (degrees)")
    parser.add_argument("--minlon", type=float, help=" output min longitude (degrees)")
    parser.add_argument("--maxlon", type=float, help=" output max longitude (degrees)")
    parser.add_argument("--reqres", type=float, help=" required output resolution (degrees) (-1.=automatic)")
    parser.add_argument("--outlevmode", type=str, help=" Output level mode (pressure, height, pressure_height)")
    parser.add_argument("--plevs", type=str, help=" output pressure levels (hPa)")
    parser.add_argument("--mlevs", type=str, help=" output height levels (m)")
    parser.add_argument("--dlevs", type=str, help=" output ocean depth (m)")

    parser.add_argument("--dmode", type=str, help=" downscaling (nudging_gcm, sst_only, nuding_ccam, sst_6hr, generate_veg, postprocess, nudging_gcm_with_sst, squaplanet1, .., aquaplanent8)")
    parser.add_argument("--sib", type=str, help=" land surface (cable_vary, cable_sli, cable_const, cable_modis2020, cable_sli_modis2020, cable_modis2020_const)")
    parser.add_argument("--aero", type=str, help=" aerosols (off, prognostic)")
    parser.add_argument("--conv", type=str, help=" convection (2014, 2015a, 2015b, 2017, Mod2015a, 2021)")
    parser.add_argument("--cldfrac", type=str, help=" cloud fraction (smith, mcgregor")
    parser.add_argument("--cloud", type=str, help=" cloud microphysics (liq_ice, liq_ice_rain, liq_ice_rain_snow_graupel)")
    parser.add_argument("--rad", type=str, help=" radiation (SE3, SE4)")
    parser.add_argument("--rad_year", type=int, help=" radiation year (0=off)")
    parser.add_argument("--bmix", type=str, help=" boundary layer (ri, tke_eps, hbg)")
    parser.add_argument("--tke_timeave_length", type=float, help=" Averaging time period for TKE")
    parser.add_argument("--mlo", type=str, help=" ocean (prescribed, dynamical)")
    parser.add_argument("--casa", type=str, help=" CASA-CNP carbon cycle with prognostic LAI (off, casa_cnp, casa_cnp_pop)")
    parser.add_argument("--tracer", type=str, help=" Tracer emission directory (off=disabled)")

    parser.add_argument("--ncout", type=str, help=" standard output format (off, all, ctm, basic, all_s, basic_s)")
    parser.add_argument("--ncsurf", type=str, help=" CORDEX output (off, cordex), cordex_s")
    parser.add_argument("--nchigh", type=str, help=" High-freq output (off, latlon, latlon_s)")
    parser.add_argument("--nctar", type=str, help=" TAR output files in OUTPUT directory (off, tar, delete)")
    parser.add_argument("--ktc", type=int, help=" standard output period (mins)")
    parser.add_argument("--ktc_surf", type=int, help=" CORDEX file output period (mins) (0=off)")
    parser.add_argument("--ktc_high", type=int, help=" High-freq file output period (mins) (0=off)")
    
    parser.add_argument("--uclemparm", type=str, help=" User defined UCLEMS parameter file (default for standard values)")
    parser.add_argument("--cableparm", type=str, help=" User defined CABLE vegetation parameter file (default for standard values)")
    parser.add_argument("--soilparm", type=str, help=" User defined soil parameter file (default for standard values)")
    parser.add_argument("--vegindex", type=str, help=" User defined vegetation indices for user vegetation (default for standard values)")
    parser.add_argument("--uservegfile", type=str, help=" User defined vegetation map (none for no file)")
    parser.add_argument("--userlaifile", type=str, help=" User defined LAI map (none for no file)")

    parser.add_argument("--drsmode", type=str, help=" DRS output (off, on)")
    parser.add_argument("--drshost", type=str, help=" Host GCM for DRS output")
    parser.add_argument("--drsensemble", type=str, help=" Host GCM ensemble number for DRS output")
    parser.add_argument("--drsdomain", type=str, help=" DRS domain")
    parser.add_argument("--drsproject", type=str, help=" DRS project name")
    parser.add_argument("--model_id", type=str, help=" CCAM version name")
    parser.add_argument("--contact", type=str, help=" CCAM contact email")
    parser.add_argument("--rcm_version_id", type=str, help=" CCAM version number")

    # special options for testing
    
    ###############################################################
    # Specify directories, datasets and executables

    parser.add_argument("--bcdom", type=str, help=" host file prefix for dmode=nudging_gcm, nudging_ccam, sst_6hour or nudging_gcm_with_sst")
    parser.add_argument("--bcdir", type=str, help=" host atmospheric data (for dmode=nudging_gcm, nudging_ccam, sst_6hour or nudging_gcm_with_sst)")
    parser.add_argument("--sstfile", type=str, help=" sst file for dmode=sst_only or nudging_gcm_with_sst")
    parser.add_argument("--sstinit", type=str, help=" initial conditions file for dmode=sst_only")
    parser.add_argument("--sstdir", type=str, help=" SST data (for dmode=sst_only or nudging_gcm_with_sst)")
    parser.add_argument("--bcsoil", type=str, help=" Initial soil moisture (constant, climatology, recycle)")
    parser.add_argument("--bcsoilfile", type=str, help=" Input file for soil recycle")

    parser.add_argument("--insdir", type=str, help=" install directory")
    parser.add_argument("--hdir", type=str, help=" script directory")
    parser.add_argument("--wdir", type=str, help=" working directory")
    parser.add_argument("--stdat", type=str, help=" eigen and radiation datafiles")

    parser.add_argument("--terread", type=str, help=" path of terread executable")
    parser.add_argument("--igbpveg", type=str, help=" path of igbpveg executable")
    parser.add_argument("--sibveg", type=str, help="depreciated")
    parser.add_argument("--ocnbath", type=str, help=" path of ocnbath executable")
    parser.add_argument("--casafield", type=str, help=" path of casafield executable")
    parser.add_argument("--aeroemiss", type=str, help=" path of aeroemiss executable")
    parser.add_argument("--model", type=str, help=" path of globpea executable")
    parser.add_argument("--pcc2hist", type=str, help=" path of pcc2hist executable")

    args = parser.parse_args()

    main(args)
