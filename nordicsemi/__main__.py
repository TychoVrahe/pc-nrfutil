#
# Copyright (c) 2016 Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
#   3. Neither the name of Nordic Semiconductor ASA nor the names of other
#   contributors to this software may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
#   4. This software must only be used in or with a processor manufactured by Nordic
#   Semiconductor ASA, or in or with a processor manufactured by a third party that
#   is used in combination with a processor manufactured by Nordic Semiconductor.
#
#   5. Any software provided in binary or object form under this license must not be
#   reverse engineered, decompiled, modified and/or disassembled.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""nrfutil command line tool."""
import os
import sys
import click
import logging
sys.path.append(os.getcwd())

from dfu.bl_dfu_sett import BLDFUSettings
from dfu.package import Package
import version as nrfutil_version
from dfu.signing import Signing

logger = logging.getLogger(__name__)


def display_sec_warning():
    default_key_warning = """
|===============================================================|
|##      ##    ###    ########  ##    ## #### ##    ##  ######  |
|##  ##  ##   ## ##   ##     ## ###   ##  ##  ###   ## ##    ## |
|##  ##  ##  ##   ##  ##     ## ####  ##  ##  ####  ## ##       |
|##  ##  ## ##     ## ########  ## ## ##  ##  ## ## ## ##   ####|
|##  ##  ## ######### ##   ##   ##  ####  ##  ##  #### ##    ## |
|##  ##  ## ##     ## ##    ##  ##   ###  ##  ##   ### ##    ## |
| ###  ###  ##     ## ##     ## ##    ## #### ##    ##  ######  |
|===============================================================|
|The security key you provided is insecure, as it part of a     |
|known set of keys that have been widely distributed. Do NOT use|
|it in your final product or your DFU procedure may be          |
|compromised and at risk of malicious attacks.                  |
|===============================================================|
"""
    click.echo("{}".format(default_key_warning))

def display_nokey_warning():
    default_nokey_warning = """
|===============================================================|
|##      ##    ###    ########  ##    ## #### ##    ##  ######  |
|##  ##  ##   ## ##   ##     ## ###   ##  ##  ###   ## ##    ## |
|##  ##  ##  ##   ##  ##     ## ####  ##  ##  ####  ## ##       |
|##  ##  ## ##     ## ########  ## ## ##  ##  ## ## ## ##   ####|
|##  ##  ## ######### ##   ##   ##  ####  ##  ##  #### ##    ## |
|##  ##  ## ##     ## ##    ##  ##   ###  ##  ##   ### ##    ## |
| ###  ###  ##     ## ##     ## ##    ## #### ##    ##  ######  |
|===============================================================|
|You are not providing a signature key, which means the DFU     |
|files will not be signed, and are vulnerable to tampering.     |
|This is only compatible with a signature-less bootloader and is|
|not suitable for production environments.                      |
|===============================================================|
"""
    click.echo("{}".format(default_nokey_warning))

def display_debug_warning():
    debug_warning = """
|===============================================================|
|##      ##    ###    ########  ##    ## #### ##    ##  ######  |
|##  ##  ##   ## ##   ##     ## ###   ##  ##  ###   ## ##    ## |
|##  ##  ##  ##   ##  ##     ## ####  ##  ##  ####  ## ##       |
|##  ##  ## ##     ## ########  ## ## ##  ##  ## ## ## ##   ####|
|##  ##  ## ######### ##   ##   ##  ####  ##  ##  #### ##    ## |
|##  ##  ## ##     ## ##    ##  ##   ###  ##  ##   ### ##    ## |
| ###  ###  ##     ## ##     ## ##    ## #### ##    ##  ######  |
|===============================================================|
|You are generating a package with the debug bit enabled in the |
|init packet. This is only compatible with a debug bootloader   |
|and is not suitable for production.                            |
|===============================================================|
"""
    click.echo("{}".format(debug_warning))

def display_settings_backup_warning():
    debug_warning = """
Note: Generating a DFU settings page with backup page included.
This is only required for bootloaders from nRF5 SDK 15.1 and newer.
If you want to skip backup page generation, use --no-backup option."""
    click.echo("{}".format(debug_warning))

def int_as_text_to_int(value):
    try:
        if value[:2].lower() == '0x':
            return int(value[2:], 16)
        elif value[:1] == '0':
            return int(value, 8)
        return int(value, 10)
    except ValueError:
        raise NordicSemiException('%s is not a valid integer' % value)

# TODO: Create query function that maps query-result strings with functions
def query_func(question, default=False):
    """
    Ask a string question
    No input defaults to "no" which results in False
    """
    valid = {"yes": True, "y": True, "no": False, "n": False}
    if default is True:
        prompt = " [Y/n]"
    else:
        prompt = " [y/N]"

    while True:
        print("%s %s" % (question, prompt))
        choice = input().lower()
        if choice == '':
            return default
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with y/n")

def pause():
    while True:
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            break

class BasedIntOrNoneParamType(click.ParamType):
    name = 'Integer'

    def convert(self, value, param, ctx):
        try:
            if value.lower() == 'none':
                return 'none'
            return int_as_text_to_int(value)
        except NordicSemiException:
            self.fail('%s is not a valid integer' % value, param, ctx)

BASED_INT_OR_NONE = BasedIntOrNoneParamType()

class BasedIntParamType(BasedIntOrNoneParamType):
    name = 'Integer'

BASED_INT = BasedIntParamType()

class TextOrNoneParamType(click.ParamType):
    name = 'Text'

    def convert(self, value, param, ctx):
        return value

TEXT_OR_NONE = TextOrNoneParamType()

BOOT_VALIDATION_ARGS = [
    'NO_VALIDATION',
    'VALIDATE_GENERATED_CRC',
    'VALIDATE_GENERATED_SHA256',
    'VALIDATE_ECDSA_P256_SHA256',
]
DEFAULT_BOOT_VALIDATION = 'VALIDATE_GENERATED_CRC'

KEY_CHOICE = ['pk', 'sk']
KEY_FORMAT = [
    'hex',
    'code',
    'pem',
    'dbgcode',
]


class OptionRequiredIf(click.Option):

    def full_process_value(self, ctx, value):
        value = super().full_process_value(ctx, value)
        if ('serial_number' not in ctx.params or not ctx.params['serial_number']) and value is None:
            msg = 'Required if "-snr" / "--serial-number" is not defined.'
            raise click.MissingParameter(ctx=ctx, param=self, message=msg)
        return value

@click.group()
@click.option('-v', '--verbose',
              help='Increase verbosity of output. Can be specified more than once (up to -v -v -v -v).',
              count=True)
@click.option('-o', '--output',
              help='Log output to file',
              metavar='<filename>')
def cli(verbose, output):
    #click.echo('verbosity: %s' % verbose)
    if verbose == 0:
        log_level = logging.ERROR
    elif verbose == 1:
        log_level = logging.WARNING
    elif verbose == 2:
        log_level = logging.INFO
    elif verbose == 3:
        log_level = logging.DEBUG
    else:
        log_level = logging.ERROR

    logging.basicConfig(format='%(asctime)s %(message)s', level=log_level)

    if (output):
        root = logging.getLogger('')
        fh = logging.FileHandler(output)
        fh.setLevel(log_level)
        fh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        root.addHandler(fh)

@cli.command()
def version():
    """Display nrfutil version."""
    click.echo("nrfutil version {}".format(nrfutil_version.NRFUTIL_VERSION))
    logger.info("PyPi URL: https://pypi.python.org/pypi/nrfutil")
    logger.debug("GitHub URL: https://github.com/NordicSemiconductor/pc-nrfutil")

@cli.group(short_help='Generate and display Bootloader DFU settings.')
def settings():
    """
    This set of commands supports creating and displaying bootloader settings.
    """
    pass

@settings.command(short_help='Generate a .hex file with Bootloader DFU settings.')
@click.argument('hex_file', required=True, type=click.Path())
@click.option('--family',
              help='nRF IC family: NRF51 or NRF52 or NRF52QFAB or NRF52810 or NRF52840',
              type=click.Choice(['NRF51', 'NRF52', 'NRF52QFAB', 'NRF52810', 'NRF52840']),
              required=True)
@click.option('--application',
              help='The application firmware file. This can be omitted if'
                    'the target IC does not contain an application in flash.'
                    'Requires --application-version or --application-version-string.',
              type=click.STRING)
@click.option('--application-version',
              help='The application version.',
              type=BASED_INT_OR_NONE)
@click.option('--application-version-string',
              help='The application version string, e.g. "2.7.31". Will be converted to an integer, e.g. 20731.',
              type=click.STRING)
@click.option('--bootloader-version',
              help='The bootloader version.',
              type=BASED_INT_OR_NONE,
              required=True)
@click.option('--start-address',
              help='Custom start address for the settings page. If not specified, '
                   'then the last page of the flash is used.',
              type=BASED_INT_OR_NONE)
@click.option('--no-backup',
              help='Do not overwrite DFU settings backup page. If not specified, '
                   'than the resulting .hex file will contain a copy of DFU settings, '
                   'that will overwrite contents of DFU settings backup page.',
              type=click.BOOL,
              is_flag=True,
              required=False)
@click.option('--backup-address',
              help='Address of the DFU settings backup page inside flash. '
                   'By default, the backup page address is placed one page below DFU settings. '
                   'The value is precalculated based on configured settings address '
                   '(<DFU_settings_address> - 0x1000).',
              type=BASED_INT_OR_NONE)
@click.option('--softdevice',
              help='The SoftDevice firmware file. Must be given if SD Boot Validation is used.',
              required=False,
              type=click.Path(exists=True, resolve_path=True, file_okay=True, dir_okay=False))
@click.option('--key-file',
              help='The private (signing) key in PEM format. Needed for ECDSA Boot Validation.',
              required=False,
              type=click.Path(exists=True, resolve_path=True, file_okay=True, dir_okay=False))
def generate(hex_file,
             family,
             application,
             application_version,
             application_version_string,
             bootloader_version,
             start_address,
             no_backup,
             backup_address,
             softdevice,
             key_file):

    # The user can specify the application version with two different
    # formats. As an integer, e.g. 102130, or as a string
    # "10.21.30". Internally we convert to integer.
    if application_version_string:
        application_version_internal = convert_version_string_to_int(application_version_string)
        if application_version:
            click.echo('Warning: When both application-version-string and application-version are provided, only the string will be used.')
    else:
        application_version_internal = application_version

    if application is not None:
        if not os.path.isfile(application):
            raise click.FileError(application, hint="Application file not found")
        if application_version_internal is None:
            raise click.UsageError('--application-version or --application-version-string'
                                   ' required with application image.')

    if (no_backup is not None) and (backup_address is not None):
        raise click.BadParameter("Bootloader DFU settings backup page cannot be specified if backup is disabled.", param_hint='backup_address')

    if no_backup is None:
        no_backup = False

    if no_backup is False:
        display_settings_backup_warning()

    if (start_address is not None) and (backup_address is None):
        click.echo("WARNING: Using default offset in order to calculate bootloader settings backup page")

    # load signing key (if needed) only once
    if not os.path.isfile(key_file):
        raise click.UsageError("Key file must be given")
    signer = Signing()
    default_key = signer.load_key(key_file)
    if default_key:
        display_sec_warning()


    if not application:
        raise click.UsageError("--application hex file must be set")


    sett = BLDFUSettings()
    sett.generate(arch=family, app_file=application, app_ver=application_version_internal, bl_ver=bootloader_version,
                  custom_bl_sett_addr=start_address, no_backup=no_backup,
                  backup_address=backup_address, sd_file=softdevice, signer=signer)
    sett.tohexfile(hex_file)

    click.echo("\nGenerated Bootloader DFU settings .hex file and stored it in: {}".format(hex_file))

    click.echo("{0}".format(str(sett)))

@settings.command(short_help='Display the contents of a .hex file with Bootloader DFU settings.')
@click.argument('hex_file', required=True, type=click.Path())

def display(hex_file):

    sett = BLDFUSettings()
    try:
        sett.fromhexfile(hex_file)
    except NordicSemiException as err:
        raise click.UsageError(err)

    click.echo("{0}".format(str(sett)))


@cli.group(short_help='Generate and display private and public keys.')
def keys():
    """
    This set of commands supports creating and displaying a private (signing) key
    as well as displaying the public (verification) key derived from a private key.
    Private keys are stored in PEM format.
    """
    pass

@keys.command(short_help='Generate a private key and store it in a file in PEM format.')
@click.argument('key_file', required=True, type=click.Path())

def generate(key_file):
    signer = Signing()

    if os.path.exists(key_file):
        if not query_func("File found at %s. Do you want to overwrite the file?" % key_file):
            click.echo('Key generation aborted.')
            return

    signer.gen_key(key_file)
    click.echo("Generated private key and stored it in: %s" % key_file)

@keys.command(short_help='Display the private key that is stored in a file in PEM format or a public key derived from it.')
@click.argument('key_file', required=True, type=click.Path())
@click.option('--key',
              help='(pk|sk) Display the public key (pk) or the private key (sk).',
              type=click.Choice(KEY_CHOICE),
              required=True)
@click.option('--format',
              help='(hex|code|pem) Display the key in hexadecimal format (hex), C code (code), or PEM (pem) format.',
              type=click.Choice(KEY_FORMAT),
              required=True)
@click.option('--out_file',
              help='If provided, save the output in file out_file.',
              type=click.STRING)

def display(key_file, key, format, out_file):
    signer = Signing()

    if not os.path.isfile(key_file):
        raise NordicSemiException("File not found: %s" % key_file)

    default_key = signer.load_key(key_file)
    if default_key:
        display_sec_warning()

    if format == "dbgcode":
        format = "code"
        dbg = True
    else:
        dbg = False

    if format == "code" and key == "sk":
        raise click.UsageError("Displaying the private key as code is not available.")

    if key == "pk":
        kstr = signer.get_vk(format, dbg)
    elif key == "sk":
        kstr = "\nWARNING: Security risk! Do not share the private key.\n\n"
        kstr = kstr + signer.get_sk(format, dbg)

    if not out_file:
        click.echo(kstr)
    else:
        with open(out_file, "w") as kfile:
            kfile.write(kstr)


@cli.group(short_help='Display or generate a DFU package (zip file).')
def pkg():
    """
    This set of commands supports Nordic DFU package generation.
    """
    pass


@pkg.command(short_help='Generate a zip file for performing DFU.')
@click.argument('zipfile',
                required=True,
                type=click.Path())
@click.option('--debug-mode',
              help='Debug mode switch, enables version check skipping.',
              type=click.BOOL,
              default=False,
              is_flag=True)
@click.option('--application',
              help='The application firmware file.',
              type=click.STRING)
@click.option('--application-version',
              help='The application version.',
              type=BASED_INT_OR_NONE)
@click.option('--application-version-string',
              help='The application version string, e.g. "2.7.31". Will be converted to an integer, e.g. 20731.',
              type=click.STRING)
@click.option('--bootloader',
              help='The bootloader firmware file.',
              type=click.STRING)
@click.option('--bootloader-version',
              help='The bootloader version.',
              type=BASED_INT_OR_NONE)
@click.option('--hw-version',
              help='The hardware version.',
              required=False,
              type=BASED_INT)
@click.option('--sd-req',
              help='The SoftDevice requirements. A comma-separated list of SoftDevice firmware IDs '
                   '(1 or more) of which one must be present on the target device. Each item on the '
                   'list must be a two- or four-digit hex number prefixed with \"0x\" (e.g. \"0x12\", '
                   '\"0x1234\").\n'
                   'A non-exhaustive list of well-known values to use with this option follows:'
                   '\n|s112_nrf52_6.0.0|0xA7|'
                   '\n|s112_nrf52_6.1.0|0xB0|'
                   '\n|s112_nrf52_6.1.1|0xB8|'
                   '\n|s112_nrf52_7.0.0|0xC4|'
                   '\n|s112_nrf52_7.0.1|0xCD|'
                   '\n|s112_nrf52_7.2.0|0x103|'
                   '\n|s112_nrf52_7.3.0|0x126|'
                   '\n|s113_nrf52_7.0.0|0xC3|'
                   '\n|s113_nrf52_7.0.1|0xCC|'
                   '\n|s113_nrf52_7.2.0|0x102|'
                   '\n|s113_nrf52_7.3.0|0x125|'
                   '\n|s122_nrf52_8.0.0|0xEA|'
                   '\n|s122_nrf52_8.1.1|0x112|'
                   '\n|s130_nrf51_1.0.0|0x67|'
                   '\n|s130_nrf51_2.0.0|0x80|'
                   '\n|s130_nrf51_2.0.1|0x87|'
                   '\n|s132_nrf52_2.0.0|0x81|'
                   '\n|s132_nrf52_2.0.1|0x88|'
                   '\n|s132_nrf52_3.0.0|0x8C|'
                   '\n|s132_nrf52_3.1.0|0x91|'
                   '\n|s132_nrf52_4.0.0|0x95|'
                   '\n|s132_nrf52_4.0.2|0x98|'
                   '\n|s132_nrf52_4.0.3|0x99|'
                   '\n|s132_nrf52_4.0.4|0x9E|'
                   '\n|s132_nrf52_4.0.5|0x9F|'
                   '\n|s132_nrf52_5.0.0|0x9D|'
                   '\n|s132_nrf52_5.1.0|0xA5|'
                   '\n|s132_nrf52_6.0.0|0xA8|'
                   '\n|s132_nrf52_6.1.0|0xAF|'
                   '\n|s132_nrf52_6.1.1|0xB7|'
                   '\n|s132_nrf52_7.0.0|0xC2|'
                   '\n|s132_nrf52_7.0.1|0xCB|'
                   '\n|s132_nrf52_7.2.0|0x101|'
                   '\n|s132_nrf52_7.3.0|0x124|'
                   '\n|s140_nrf52_6.0.0|0xA9|'
                   '\n|s140_nrf52_6.1.0|0xAE|'
                   '\n|s140_nrf52_6.1.1|0xB6|'
                   '\n|s140_nrf52_7.0.0|0xC1|'
                   '\n|s140_nrf52_7.0.1|0xCA|'
                   '\n|s140_nrf52_7.2.0|0x100|'
                   '\n|s140_nrf52_7.3.0|0x123|'
                   '\n|s212_nrf52_6.1.1|0xBC|'
                   '\n|s332_nrf52_6.1.1|0xBA|'
                   '\n|s340_nrf52_6.1.1|0xB9|',
              type=click.STRING,
              required=False,
              multiple=True)
@click.option('--sd-id',
              help='The new SoftDevice ID to be used as --sd-req for the Application update in case the ZIP '
                   'contains a SoftDevice and an Application.',
              type=click.STRING,
              multiple=True)
@click.option('--softdevice',
              help='The SoftDevice firmware file.',
              type=click.STRING)
@click.option('--key-file',
              help='The private (signing) key in PEM format.',
              required=False,
              type=click.Path(exists=True, resolve_path=True, file_okay=True, dir_okay=False))

def generate(zipfile,
           debug_mode,
           application,
           application_version,
           application_version_string,
           bootloader,
           bootloader_version,
           hw_version,
           sd_req,
           sd_id,
           softdevice,
           key_file,):
    """
    Generate a zip package for distribution to apps that support Nordic DFU OTA.
    The application, bootloader, and SoftDevice files are converted to .bin if supplied as .hex files.
    For more information on the generated package, see:
    http://developer.nordicsemi.com/nRF5_SDK/doc/

    The following combinations are supported by this command:

    * BL only: Supported.

    * SD only: Supported (SD of same Major Version).

    * APP only: Supported (external or internal).

    * BL + SD: Supported.

    * BL + APP: Not supported (use two packages instead).

    * BL + SD + APP: Supported.

    * SD + APP: Supported (SD of same Major Version).
    """
    zipfile_path = zipfile

    # Check combinations
    if bootloader is not None and application is not None and softdevice is None:
        raise click.UsageError("Invalid combination: use two .zip packages instead.")

    if debug_mode is None:
        debug_mode = False

    # The user can specify the application version with two different
    # formats. As an integer, e.g. 102130, or as a string
    # "10.21.30". Internally we convert to integer.
    if application_version_string:
        application_version_internal = convert_version_string_to_int(application_version_string)
        if application_version:
            click.echo('Warning: When both application-version-string and application-version are provided, only the string will be used.')
    else:
        application_version_internal = application_version

    if application_version_internal == 'none':
        application_version_internal = None

    if bootloader_version == 'none':
        bootloader_version = None

    if hw_version == 'none':
        hw_version = None

    # Convert multiple value into a single instance
    if len(sd_req) > 1:
        raise click.BadParameter("Please specify SoftDevice requirements as a comma-separated list: --sd-req 0xXXXX,0xYYYY,...", param_hint='sd_req')
    elif len(sd_req) == 0:
        sd_req = None
    else:
        sd_req = sd_req[0]
        if sd_req == 'none':
            sd_req = None

    if len(sd_id) > 1:
        raise click.BadParameter("Please specify SoftDevice requirements as a comma-separated list: --sd-id 0xXXXX,0xYYYY,...", param_hint='sd_req')
    elif len(sd_id) == 0:
        sd_id = None
    else:
        sd_id = sd_id[0]
        if sd_id == 'none':
            sd_id = None

    # Initial consistency checks
    if application_version_internal is not None and application is None:
        raise click.UsageError("Application version with no image.")

    if bootloader_version is not None and bootloader is None:
        raise click.UsageError("Bootloader version with no image.")

    if debug_mode:
        display_debug_warning()
        # Default to no version checking
        if application_version_internal is None:
            application_version_internal=Package.DEFAULT_APP_VERSION
        if bootloader_version is None:
            bootloader_version=Package.DEFAULT_BL_VERSION
        if hw_version is None:
            hw_version=Package.DEFAULT_HW_VERSION
        if sd_req is None:
            # Use string as this will be mapped into an int below
            sd_req=str(Package.DEFAULT_SD_REQ[0])

    # Version checks
    if hw_version is None:
        raise click.UsageError("--hw-version required.")

    if sd_req is None:
        raise click.UsageError("--sd-req required.")

    if application is not None and application_version_internal is None:
        raise click.UsageError('--application-version or --application-version-string'
                   ' required with application image.')

    if bootloader is not None and bootloader_version is None:
        raise click.UsageError("--bootloader-version required with bootloader image.")

    if application is not None and softdevice is not None and sd_id is None:
        raise click.UsageError("--sd-id required with softdevice and application images.")

    sd_req_list = []
    if sd_req is not None:
        try:
            # This will parse any string starting with 0x as base 16.
            sd_req_list = sd_req.split(',')
            sd_req_list = list(map(int_as_text_to_int, sd_req_list))
        except ValueError:
            raise NordicSemiException("Could not parse value for --sd-req. "
                                      "Hex values should be prefixed with 0x.")

    sd_id_list = []
    if sd_id is not None:
        try:
            # This will parse any string starting with 0x as base 16.
            sd_id_list = sd_id.split(',')
            sd_id_list = list(map(int_as_text_to_int, sd_id_list))

            # Copy all IDs from sd_id_list to sd_req_list, without duplicates.
            # This ensures that the softdevice update can be repeated in case
            # SD+(BL)+App update terminates during application update after the
            # softdevice was already updated (with new ID). Such update would
            # have to be repeated and the softdevice would have to be sent again,
            # this time updating itself.
            sd_req_list += set(sd_id_list) - set(sd_req_list)
        except ValueError:
            raise NordicSemiException("Could not parse value for --sd-id. "
                                      "Hex values should be prefixed with 0x.")
    else:
        sd_id_list = sd_req_list

    if key_file is None:
        display_nokey_warning()
        signer = None
    else:
        signer = Signing()
        default_key = signer.load_key(key_file)
        if default_key:
            display_sec_warning()

    # Generate a DFU package. If --zigbee is set this is the inner DFU package
    # which will be used as a binary input to the outer DFU package
    package = Package(debug_mode,
                      hw_version,
                      application_version_internal,
                      bootloader_version,
                      sd_req_list,
                      sd_id_list,
                      application,
                      bootloader,
                      softdevice,
                      signer,)

    package.generate_package(zipfile_path)

    log_message = "Zip created at {0}".format(zipfile_path)
    click.echo(log_message)

@pkg.command(short_help='Display the contents of a .zip package file.')
@click.argument('zip_file', required=True, type=click.Path())

def display(zip_file):

    package = Package()
    package.parse_package(zip_file, preserve_work_dir=True)

    click.echo("{0}".format(str(package)))


def convert_version_string_to_int(s):
    """Convert from semver string "1.2.3", to integer 10203"""
    numbers = s.split(".")
    if len(numbers) != 3:
        raise click.BadParameter("Must be on the format x.y.z", param_hint='application-version-string')
    js = [10000, 100, 1]
    return sum([js[i] * int(numbers[i]) for i in range(3)])

if __name__ == '__main__':
    cli()
