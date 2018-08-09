import subprocess
import pathlib
from argparse import ArgumentParser
import shutil

from releaseapi import get_release_asset
from gdrive_download import download_file_from_google_drive


def run_tests(
    config: str,
    compiler: str,
    domain_dir: str,
    candidate_dir: str,
    reference_dir: str,
    output_dir: str,
    scheduler: bool=False,
    ncores: int=216,
    nnodes: int=6,
    account: str='NRAL0017',
    walltime: str='02:00:00',
    queue='regular',
    html_report='wrfhydro_testout.html'
):

    """Function to run wrf_hydro_nwm pytests
        Args:
            config: The config(s) to run, must be listed in hydro_namelist.json keys.
            E.g. nwm_ana gridded
            compiler: The compiler to use, options are 'ifort' or 'gfort'
            domain_dir: The domain directory to use
            candidate_dir: The wrf-hydro code candidate directory to use, e.g. wrf_hydro_nwm_public
            reference_dir: The wrf-hydro code directory to use, e.g. wrf_hydro_nwm_public
            output_dir: The directory to hold test outputs
            nproc: Optional. The number of cores to use if running on cheyenne
            nnodes: Optional. The number of nodes to use if running on cheyenne
            account: Options. The account number to use if running on cheyenne
    """

    # Pytest wants the actual source code directory, not the top level repo directory
    candidate_source_dir = candidate_dir + '/trunk/NDHMS'
    reference_source_dir = reference_dir + '/trunk/NDHMS'

    # For interactive debug add: --pdb
    pytest_cmd = "pytest -v --ignore=local"

    # Ignore section: for cleaner tests with less skipps!
    # NWM
    # If it is not NWM, ignore channel-only. (This is probably not the right way to do this.)
    if config.lower().find('nwm') < 0:
        pytest_cmd += " --ignore=tests/test_supp_1_channel_only.py "

    pytest_cmd += " --html=" + str(html_report)
    pytest_cmd += " --config " + config.lower()
    pytest_cmd += " --compiler " + compiler.lower()
    pytest_cmd += " --domain_dir " + domain_dir
    pytest_cmd += " --candidate_dir " + candidate_source_dir
    pytest_cmd += " --reference_dir " + reference_source_dir
    pytest_cmd += " --output_dir " + output_dir
    pytest_cmd += " --ncores " + str(ncores)

    if scheduler:
        pytest_cmd += " --scheduler "
        pytest_cmd += " --nnodes " + str(nnodes)
        pytest_cmd += " --account " + account
        pytest_cmd += " --walltime " + walltime
        pytest_cmd += " --queue " + queue

    print(pytest_cmd)
    tests = subprocess.run(pytest_cmd, shell=True, cwd=candidate_dir)

    return tests


def main():
    parser = ArgumentParser()

    parser.add_argument("--config",
                        required=True,
                        nargs='+',
                        help="<Required> The configuration(s) to test, "
                             "must be one listed in trunk/NDHMS/hydro_namelist.json keys.")

    parser.add_argument('--compiler',
                        required=True,
                        help='<Required> compiler, options are intel or gfort')

    parser.add_argument('--output_dir',
                        required=True,
                        help='<Required> test output directory')

    parser.add_argument('--candidate_dir',
                        required=True,
                        help='<Required> candidate model directory')

    parser.add_argument('--reference_dir',
                        required=True,
                        help='<Required> reference model directory')

    parser.add_argument('--domain_dir',
                        required=False,
                        help='optional domain directory')

    parser.add_argument("--domain_tag",
                        required=False,
                        help="The release tag of the domain to retrieve, e.g. v5.0.1. or dev. If "
                             "specified, a small test domain will be retrieved and placed in the "
                             "specified output_dir and used for the testing domain")

    parser.add_argument('--ncores',
                        default='2',
                        required=False,
                        help='Number of cores to use for testing')

    parser.add_argument('--scheduler',
                        required=False,
                        action='store_true',
                        help='Scheduler to use for testing, options are PBSCheyenne or do not '
                             'specify for no scheduler')

    parser.add_argument('--nnodes',
                        default='6',
                        required=False,
                        help='Number of nodes to use for testing if running on scheduler')

    parser.add_argument('--account',
                        default='NRAL0017',
                        required=False,
                        action='store',
                        help='Account number to use if using a scheduler.')

    parser.add_argument('--walltime',
                        default='02:00:00',
                        required=False,
                        action='store',
                        help='Account number to use if using a scheduler.')

    parser.add_argument('--queue',
                        default='regular',
                        required=False,
                        action='store',
                        help='Queue to use if running on NCAR Cheyenne, options are regular, '
                             'premium, or shared')

    parser.add_argument('--html_report',
                        default='wrfhydro_testout.html',
                        required=False,
                        action='store',
                        help='Create an HTML report from testing with the specified name')

    args = parser.parse_args()

    # Make all directories pathlib objects
    output_dir = pathlib.Path(args.output_dir)
    candidate_dir = pathlib.Path(args.candidate_dir)
    reference_dir = pathlib.Path(args.reference_dir)
    domain_dir = args.domain_dir

    if domain_dir is not None:
        domain_dir = pathlib.Path(domain_dir)

    # Get other args
    config_list = args.config

    compiler = args.compiler
    domain_tag = args.domain_tag
    ncores = args.ncores
    nnodes = args.nnodes
    scheduler = args.scheduler
    account = args.account
    walltime = args.walltime
    queue = args.queue

    # Build path to html report
    html_report = args.html_report
    html_report = str(output_dir.joinpath(html_report))

    # Make output dir if does not exist
    if output_dir.is_dir():
        raise(IsADirectoryError('Output directory ' + str(output_dir) + ' already exists'))
    else:
        output_dir.mkdir(parents=True)

    # Get the domain if asked for
    if domain_tag is not None:
        # Reset domain dir to be the downlaoded domain in the output dir
        domain_dir = output_dir.joinpath('example_case')

        if domain_tag == 'dev':
            file_id = '1EHgWeM8k2-Y3jNMLri6C0u_fIUQIonO_'
            download_file_from_google_drive(file_id, str(output_dir.joinpath(
                'gdrive_testcase.tar.gz')))

            # untar the test case
            untar_cmd = 'tar -xf *testcase*.tar.gz'
            subprocess.run(untar_cmd,
                           shell=True,
                           cwd=str(output_dir))
        else:
            get_release_asset(download_dir=str(output_dir),
                              repo_name='NCAR/wrf_hydro_nwm_public',
                              tag=domain_tag,
                              asset_name='testcase')
            # untar the test case
            untar_cmd = 'tar -xf *testcase*.tar.gz'
            subprocess.run(untar_cmd,
                           shell=True,
                           cwd=str(output_dir))

    # Make copy paths
    candidate_copy = output_dir.joinpath(candidate_dir.name + '_can_pytest')
    reference_copy = output_dir.joinpath(reference_dir.name + '_ref_pytest')

    # Remove if exist and make if not
    if candidate_copy.is_dir():
        shutil.rmtree(str(candidate_copy))
    if reference_copy.is_dir():
        shutil.rmtree(str(reference_copy))

    # copy directories to avoid polluting user source code directories
    shutil.copytree(str(candidate_dir), str(candidate_copy), symlinks=True)
    shutil.copytree(str(reference_dir), str(reference_copy), symlinks=True)

    # run pytest for each supplied config
    has_failure = False
    for config in config_list:

        extra_spaces = 29
        total_len = len(config) + extra_spaces
        print('\n\n' + ('#' * total_len))
        print('### TESTING:  ---  ' + config + '  ---  ###')
        print(('#' * total_len) + '\n', flush=True)

        test_result = run_tests(
            config=config,
            compiler=compiler,
            domain_dir=str(domain_dir),
            candidate_dir=str(candidate_copy),
            reference_dir=str(reference_copy),
            output_dir=str(output_dir),
            scheduler=scheduler,
            ncores=ncores,
            nnodes=nnodes,
            account=account,
            walltime=walltime,
            queue=queue,
            html_report=html_report
        )
        if test_result.returncode != 0:
            has_failure = True

    # Exit with 1 if failure
    if has_failure:
        print('\n\n'
              '##################################')
        print('###  ---  TESTING FAILED  ---  ###')
        print('##################################\n\n', flush=True)
        exit(1)
    else:
        print('\n\n'
              '##################################')
        print('###  ---  TESTING PASSED  ---  ###')
        print('##################################\n\n', flush=True)
        exit(0)


if __name__ == '__main__':
    main()