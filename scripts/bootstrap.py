# Version: 2.0 (578d03a6632b46c13c46f36390507eba57abbf44)
import argparse
import datetime
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from argparse import RawTextHelpFormatter
from contextlib import contextmanager
import shutil

HTTP_PROXY = None

EXIT_CODES = {
    "100": "Failed to install Package 'amazon-ssm-agent'",
    "101": "Failed to uninstall Package 'amazon-ssm-agent'",
    "102": "Unable to start 'amazon-ssm-agent' service",
    "103": "Unable to stop 'amazon-ssm-agent' service",
    "104": "Service 'amazon-ssm-agent' has not reached a 'running' status after multiple attempts.",
    "105": "GET request to activation job url failed.",
    "106": "SSM agent activation job was not successful",
    "107": "Agent activation job did not complete after multiple attempts.",
    "108": "POST request to activation url failed.",
    "109": "POST request to activation url did not return a Location header.",
    "110": "Failed to execute agent registration command.",
    "111": "Failed to execute agent diagnostics command.",
    "112": "Management agent was not registered successfully.",
    "113": "'ssm-cli' command does not exist",
    "114": "Failed to execute clear agent registration command",
    "115": "HTTP request failed while installing Amazon SSM Agent",
    "116": "Package 'amazon-ssm-agent' Agent is not currently installed",
    "117": "HTTP request failed while uninstalling Amazon SSM Agent",
    "118": "Could not retrieve token after multiple attempts.  Rackspace vmware provisioning is responsible for setting the 'guestinfo.machine.id' custom property.",
    "119": "Vmware get token command failed.",
    "120": "GET request to metadata instance url failed.",
    "121": "GET request to metadata attest url failed.",
    "122": "Token file not found. Rackspace dedicated server provisioning is responsible for populating this file.",
    "123": "Token file is empty. Rackspace dedicated server provisioning is responsible for populating this file.",
    "124": "GET request to instance identity url failed",
    "125": "GET request to instance metadata identity url failed",
    "126": "Downloading agent package installer from package installer url failed",
    "127": "Command 'amazon-ssm-agent' not found",
    "128": "SSM package is not installed, cannot reregister agent",
    "129": "'ssm-cli' command does not exist",
    "130": "Neither systemctl or service commands found in $PATH, bootstrap install cannot continue.",
    "131": "Could not determine guest operating system Linux distribution.",
    "132": "Operating system is not unsupported.",
    "137": "Installation cannot continue because 'vmtoolsd' is not installed, please install 'vmtoolsd' before continuing",
    "138": "Failed to get token from OpenStack vendordata. The underlying API might have an outage.",
}
SORTED_EXIT_CODES = sorted(EXIT_CODES.items(), key=lambda exit_code: exit_code[0])

EXIT_CODES_FOR_EPILOG = "\n".join([": ".join(exit_code) for exit_code in SORTED_EXIT_CODES])


def is_python2():
    return sys.version_info[0] == 2


def get_timestamp():
    current_time = datetime.datetime.utcnow()
    formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    return formatted_time


def as_text(message, level="DEBUG"):
    current_timestamp = get_timestamp()
    return "[%s] %s - %s" % (current_timestamp, level, message)


def as_json(message, details, level="DEBUG"):
    return {"timestamp": get_timestamp(), "level": "%s" % (level), "message": "%s" % (message), "details": "%s" % (details)}


def setup_logger():
    logging.addLevelName(logging.WARNING, "WARN")
    logging.addLevelName(logging.CRITICAL, "CRIT")

    formatter = logging.Formatter(
        fmt="[%(asctime)s.%(msecs)03d] %(levelname)-5s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = time.gmtime

    logs_fh = logging.FileHandler("agent_bootstrap.log")
    logs_fh.setLevel(logging.DEBUG)
    logs_fh.setFormatter(formatter)
    logs_fh.set_name("agent_bootstrap_logs")

    logs_sh = logging.StreamHandler(stream=sys.stdout)
    logs_sh.setLevel(logging.DEBUG)
    logs_sh.setFormatter(formatter)
    logs_sh.set_name("agent_bootstrap_stream_logs")

    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(logs_fh)
    _logger.addHandler(logs_sh)
    return _logger


class Enum(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, value):
        return value in self.__dict__.values()

    def __iter__(self):
        return iter(self.__dict__.values())

    def __repr__(self):
        return repr(list(self.__dict__.values()))


if is_python2():
    from urlparse import urlparse
    from httplib import (  # noqa: F401
        HTTPSConnection,
        HTTPConnection,
        HTTPException,
        HTTPResponse,
    )
else:
    from urllib.parse import urlparse
    from http.client import (  # noqa: F401
        HTTPSConnection,
        HTTPConnection,
        HTTPException,
        HTTPResponse,
    )

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
DISTROS = Enum(UBUNTU="ubuntu", RHEL="rhel", CENTOS="centos", SUSE="sles", DEBIAN="debian")
IGNORE_TAG_KEY = "rackspace-addon-ignore"
PLATFORMS = Enum(GCP="gcp", AZURE="azure", VMWARE="vmware", DEDICATED="dedicated", OPENSTACK_FLEX="openstack_flex", OPENSTACK="openstack")
PLATFORM_SERVICES_BASE_URL = "https://add-ons.api.manage.rackspace.com"
SSM_SERVICE = "amazon-ssm-agent"
REGISTRATION_WAIT = 10
logger = setup_logger()
result_format = "text"
result_delimiter = "".join(["-" * 25, "%s", "-" * 25])


def set_log_level(log_level):
    for handler in logger.handlers:
        if handler.name == "stderr":
            handler.setLevel(log_level)


def command_exists(prog):
    if is_python2():
        from distutils.spawn import find_executable

        return find_executable(prog)
    else:
        from shutil import which

        return which(prog)


def file_exists(path):
    return os.path.exists(path)


def file_read(path):
    f = open(path, "r")
    return f.read()


def file_write(content, path, mode="w"):
    f = open(path, mode)
    f.write(content)
    f.close()
    return path


def file_find(path, matcher):
    f = open(path, "r")
    for line in f.readlines():
        if matcher(line):
            return line
    return None


def is_truthy(value):
    return isinstance(value, str) and value.lower() in ("t", "true", "y", "yes", "1")


def run_command(cmd):
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)


def format_command_error(cmd, err):
    return "\n".join(
        [
            "Failed command: %s" % cmd,
            "ExitCode: %d" % err.returncode,
            "Output: %s" % err.output,
        ]
    )


class Error:
    def __init__(self, message, details={}):
        self.message = message
        self.details = details


@contextmanager
def proxy_context():
    """
    Context manager to set and unset HTTP/HTTPS proxy settings in the environment.
    """
    global HTTP_PROXY
    try:
        if HTTP_PROXY:
            set_proxy()
        yield
    finally:
        if HTTP_PROXY:
            unset_proxy()


def set_proxy():
    """
    Set HTTP/HTTPS proxy settings in the environment.
    """
    global HTTP_PROXY
    os.environ["http_proxy"] = HTTP_PROXY
    os.environ["https_proxy"] = HTTP_PROXY


def unset_proxy():
    """
    Un-Set HTTP/HTTPS proxy settings in the environment.
    """
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)


class Platform(object):
    @staticmethod
    def get(name):
        if name == PLATFORMS.GCP:
            platform = Platform.Gcp
        elif name == PLATFORMS.AZURE:
            platform = Platform.Azure
        elif name == PLATFORMS.VMWARE:
            platform = Platform.Vmware
        elif name == PLATFORMS.DEDICATED:
            platform = Platform.Dedicated
        elif name == PLATFORMS.OPENSTACK:
            platform = Platform.OpenStack
        elif name == PLATFORMS.OPENSTACK_FLEX:
            logger.warning("openstack_flex platform has been deprecated, please use openstack instead.")
            platform = Platform.OpenStack
        else:
            raise Exception("Unknown platform: %s" % name)

        return platform

    class Gcp(object):
        instance_metadata_base_url = "http://metadata.google.internal/computeMetadata/v1/instance"
        name = "gcp"

        @classmethod
        def get_activation_url(cls):
            return "%s/v1.0/instance/gcp/activate" % PLATFORM_SERVICES_BASE_URL

        @classmethod
        def get_token(cls):
            instance_identity_url = "%s/service-accounts/default/identity?audience=platform.manage.rackspace.com&format=full" % cls.instance_metadata_base_url
            response = HttpClient.get(instance_identity_url, headers={"Metadata-Flavor": "Google"})
            if not response.ok:
                die("GET request to instance identity url %s failed: %s\n%s" % (instance_identity_url, response.full_status, response.dump()), exitcode=124)
            return response.text

        @staticmethod
        def is_agent_disabled():
            logger.debug("Checking GCP metadata for '%s' tag", IGNORE_TAG_KEY)
            value = Platform.Gcp.get_metadata_attribute(IGNORE_TAG_KEY)
            return value and is_truthy(value)

        @classmethod
        def get_metadata_attribute(cls, key):
            url = "%s/attributes/%s" % (cls.instance_metadata_base_url, key)
            response = HttpClient.get(url, headers={"Metadata-Flavor": "Google"})
            if response.ok:
                return response.text
            elif response.status == 404:
                return None
            die("GET request to metadata url %s failed: %s\n%s" % (url, response.full_status, response.dump()), exitcode=125)

    class Azure(object):
        attest_url = "http://169.254.169.254/metadata/attested/document?api-version=2021-01-01"
        instance_metadata_url = "http://169.254.169.254/metadata/instance/compute?api-version=2021-01-01&format=json"
        name = "azure"

        @classmethod
        def get_activation_url(cls):
            return "%s/v1.0/instance/azure/activate" % PLATFORM_SERVICES_BASE_URL

        @classmethod
        def get_token(cls):
            instance_metadata = cls.get_metadata()
            attest_doc = cls.get_attest_document()
            return json.dumps(
                {
                    "instance": {
                        "location": instance_metadata["location"],
                        "name": instance_metadata["name"],
                        "subscriptionId": instance_metadata["subscriptionId"],
                        "vmId": instance_metadata["vmId"],
                        "vmScaleSetName": instance_metadata["vmScaleSetName"],
                    },
                    "signature": attest_doc["signature"],
                    "encoding": attest_doc["encoding"],
                }
            )

        @classmethod
        def get_attest_document(cls):
            response = HttpClient.get_json(cls.attest_url, headers={"Metadata": "true"})
            if not response.ok:
                die("GET request to metadata attest url %s failed: %s\n%s" % (cls.attest_url, response.full_status, response.dump()), exitcode=121)
            return response.json()

        @staticmethod
        def is_agent_disabled():
            logger.debug("Checking Azure metadata for '%s' tag", IGNORE_TAG_KEY)
            tags = Platform.Azure.get_instance_tags()
            return is_truthy(tags.get(IGNORE_TAG_KEY))

        @classmethod
        def get_instance_tags(cls):
            return dict([(tag["name"], tag["value"]) for tag in cls.get_metadata_key("tagsList")])

        @classmethod
        def get_metadata_key(cls, key):
            metadata = cls.get_metadata()
            return metadata.get(key, None)

        @classmethod
        def get_metadata(cls):
            response = HttpClient.get_json(cls.instance_metadata_url, headers={"Metadata": "true"})
            if not response.ok:
                die("GET request to metadata instance url %s failed: %s\n%s" % (cls.instance_metadata_url, response.full_status, response.dump()), exitcode=120)
            return response.json()

    class Vmware(object):
        vmtoolsd_cmd = 'vmtoolsd --cmd "info-get guestinfo.machine.id"'
        name = "vmware"
        get_token_attempts = 20
        get_token_delay = 60

        @classmethod
        def get_activation_url(cls):
            return "%s/v1.0/instance/activate" % PLATFORM_SERVICES_BASE_URL

        @classmethod
        def get_token(cls):
            if not command_exists("vmtoolsd"):
                die("Installation cannot continue because 'vmtoolsd' is not installed, please install 'vmtoolsd' before continuing", exitcode=137)
            for attempt in range(1, cls.get_token_attempts):
                logger.debug("Running vmware get token command (attempt: %d): %s" % (attempt, cls.vmtoolsd_cmd))
                try:
                    token = run_command(cls.vmtoolsd_cmd).strip()
                except subprocess.CalledProcessError as e:
                    if e.returncode == 1:
                        logger.debug("Vmware get token command returned no token, checking again in one minute")
                        token = None
                    else:
                        die("Vmware get token command failed\n%s" % format_command_error(cls.vmtoolsd_cmd, e), exitcode=119)
                if token:
                    logger.debug("Found vmware auth token: %s", token)
                    return token
                time.sleep(cls.get_token_delay)
            die(
                "Could not retrieve token after %d attempts.  Rackspace vmware provisioning is responsible for setting the 'guestinfo.machine.id' custom property."
                % cls.get_token_attempts,
                exitcode=118,
            )

        @classmethod
        def is_agent_disabled(cls):
            logger.debug("Platform '%s' does not support bypassing agent bootstrap using tags" % cls.name)
            return False

    class Dedicated(Vmware):
        token_file = "/var/lib/rackspace/rackspace_agent/token"
        name = "dedicated"

        @classmethod
        def get_token(cls):
            if not file_exists(cls.token_file):
                die("Token file not found: %s.  Rackspace dedicated server provisioning is responsible for populating this file.", exitcode=122)
            token = file_read(cls.token_file).strip()
            if not token:
                die("Token file is empty: %s.  Rackspace dedicated server provisioning is responsible for populating this file.", exitcode=123)
            return token

        @classmethod
        def is_agent_disabled(cls):
            logger.debug(
                "Platform '%s' does not support bypassing agent bootstrap using tags",
                cls.name,
            )
            return False

    class OpenStack(object):
        name = "openstack"
        get_token_attempts = 20
        get_token_delay = 60
        vendordata_api_url = "http://169.254.169.254/openstack/latest/vendor_data2.json"

        @classmethod
        def get_activation_url(cls):
            return "%s/v2/instance/activate" % PLATFORM_SERVICES_BASE_URL

        @classmethod
        def get_token(cls):
            for attempt in range(1, cls.get_token_attempts + 1):
                logger.debug("Getting OpenStack vendordata (attempt: %d): %s" % (attempt, cls.vendordata_api_url))
                response = HttpClient.get_json(cls.vendordata_api_url)
                if not response.ok:
                    die("GET request to vendordata url %s failed: %s\n%s" % (cls.vendordata_api_url, response.full_status, response.dump()), exitcode=138)
                parsed_response = response.json()
                token = parsed_response.get("platform_services", {}).get("token")
                error_message = parsed_response.get("platform_services", {}).get("error", {}).get("message")
                if not token:
                    if error_message:
                        logger.debug("Got error message from vendordata API: %s" % error_message)
                        die("Failed to get token from OpenStack vendordata. Reason: %s" % error_message, exitcode=138)
                    logger.debug("No token found in vendordata, checking again in one minute")
                    time.sleep(cls.get_token_delay)
                    continue
                return token

            die(
                "Could not retrieve token after %d attempts. This is likely caused by an outage in the Platform Services API. Please try again later."
                % cls.get_token_attempts,
                exitcode=138,
            )

        @classmethod
        def is_agent_disabled(cls):
            # We will likely be able to support this in the future based on information we can get
            # from the metadata service.
            logger.debug("Platform '%s' does not support bypassing agent bootstrap using tags", cls.name)
            return False


class GuestOs(object):
    class AgentDiagnostics:
        def __init__(self, from_cmd):
            self.from_cmd = from_cmd

        def filter_checks(self, status):
            return [check for check in self.from_cmd if check["Status"] == status]

        def failed_checks(self):
            return self.filter_checks("Failed")

        def successful_checks(self):
            return self.filter_checks("Success")

        def skipped_checks(self):
            return self.filter_checks("Skipped")

        def checks(self):
            return self.from_cmd

    @staticmethod
    def is_agent_disabled(platform):
        return platform.is_agent_disabled()

    @staticmethod
    def clear_agent_registration():
        cmd = "amazon-ssm-agent -register -clear"
        if not command_exists("amazon-ssm-agent"):
            die("Command: amazon-ssm-agent not found in $PATH", exitcode=127)
        try:
            logger.debug("Running agent registration clear command: %s" % cmd)
            result = run_command(cmd)
            return result.strip()
        except subprocess.CalledProcessError as e:
            die("Agent registration clear command failed\n%s" % format_command_error(cmd, e), exitcode=114)

    @staticmethod
    def get_agent_information():
        cmd = "ssm-cli get-instance-information"
        if not command_exists("ssm-cli"):
            die("Command: ssm-cli not found in $PATH", exitcode=113)
        try:
            logger.debug("Running agent instance information command: %s" % cmd)
            result = run_command(cmd)
            return json.loads(result)
        except subprocess.CalledProcessError as e:
            error_line = [line for line in e.output.split("\n") if "error:" in line]
            logger.warning("Agent is not registered (exitcode: %d): %s" % (e.returncode, error_line))
            return False

    @classmethod
    def check_ssm_activation(cls):
        ssm_diagnostics = cls.get_ssm_diagnostics()
        failed_checks = ssm_diagnostics.failed_checks()
        agent_info = cls.get_agent_information()
        if failed_checks:
            logger.warning("Some management agent diagnostic checks failed, please review:\n%s" % json.dumps(failed_checks, indent=2))
        if agent_info:
            success("Management agent was registered successfully.", details=json.dumps(agent_info))
        else:
            die("Management agent was not registered successfully, view /var/log/amazon/ssm/errors.log for details", exitcode=112)

    @staticmethod
    def is_ssm_package_installed():
        distro_config = Distro.get_config(GuestOs.get_distro())
        check_installed_cmd = distro_config.check_installed_cmd
        logger.debug("Checking if amazon-ssm-agent package is already installed: %s" % check_installed_cmd)
        try:
            run_command(check_installed_cmd)
            return True
        except subprocess.CalledProcessError as e:
            logger.debug("Package amazon-ssm-agent is not currently installed\n%s" % format_command_error(check_installed_cmd, e))
            return False

    @staticmethod
    def uninstall_ssm_package():
        distro_config = Distro.get_config(GuestOs.get_distro())
        cmd = distro_config.uninstall_cmd
        logger.debug("Running ssm package uninstall command: %s" % cmd)
        try:
            result = run_command(cmd)
            logger.debug("Uninstalled ssm package\n%s" % result)
        except subprocess.CalledProcessError as e:
            die("Package uninstall command failed\n%s" % format_command_error(cmd, e), exitcode=101)

    @staticmethod
    def install_ssm_package(package_installer_path):
        distro_config = Distro.get_config(GuestOs.get_distro())
        cmd = distro_config.install_cmd % package_installer_path
        logger.debug("Running ssm package install command: %s" % cmd)
        try:
            result = run_command(cmd)
            logger.debug("Installed ssm package\n%s" % result)
        except subprocess.CalledProcessError as e:
            die("Package install command failed\n%s" % format_command_error(cmd, e), exitcode=100)

    @classmethod
    def stop_ssm_service(cls):
        cmd = None
        if command_exists("systemctl"):
            cmd = "systemctl stop %s" % SSM_SERVICE
        elif command_exists("service"):
            cmd = "service %s stop" % SSM_SERVICE
        if not cmd:
            die("Neither systemctl or service commands found in $PATH, bootstrap install cannot continue.", exitcode=130)

        logger.debug("Running stop agent service command: %s" % cmd)
        try:
            result = run_command(cmd)
            logger.debug("Stop agent service command succeeded\n%s" % result)
        except subprocess.CalledProcessError as e:
            die("Stop agent service command failed\n%s" % format_command_error(cmd, e), exitcode=103)

    @classmethod
    def get_ssm_diagnostics(cls):
        cmd = "ssm-cli get-diagnostics"
        if not command_exists("ssm-cli"):
            die("Command: ssm-cli not found in $PATH", exitcode=129)
        try:
            logger.debug("Running agent diagnostics command: %s" % cmd)
            result = run_command(cmd)
            return GuestOs.AgentDiagnostics(json.loads(result)["DiagnosticsOutput"])
        except subprocess.CalledProcessError as e:
            die("Agent diagnostics command failed\n%s" % format_command_error(cmd, e), exitcode=111)

    @classmethod
    def start_ssm_service(cls):
        start_cmd, status_cmd = None, None
        if command_exists("systemctl"):
            start_cmd = "systemctl start %s" % SSM_SERVICE
            status_cmd = "systemctl is-active %s" % SSM_SERVICE
        elif command_exists("service"):
            start_cmd = "service %s start" % SSM_SERVICE
            status_cmd = "service %s status" % SSM_SERVICE
        if not start_cmd:
            die("Neither systemctl or service commands found in $PATH, bootstrap install cannot continue.", exitcode=130)

        logger.debug("Running start agent service command: %s" % start_cmd)
        try:
            start_result = run_command(start_cmd)
            logger.debug("Start agent service command succeeded\n%s" % start_result)
        except subprocess.CalledProcessError as e:
            die("Start agent service command failed\n%s" % format_command_error(start_cmd, e), exitcode=102)

        last_err = None
        for attempt in range(1, 10):
            logger.debug("Checking if agent service is running (attempt: %d): %s" % (attempt, status_cmd))
            try:
                status_result = run_command(status_cmd)
                logger.debug("Agent service is now running: %s" % status_result)
                return True
            except subprocess.CalledProcessError as e:
                last_err = e
                logger.debug("Agent service is not running yet, checking again in one second (exitcode: %d)" % e.returncode)
        die("Agent service failed to reach a running state\n%s" % format_command_error(status_cmd, last_err), exitcode=104)

    @classmethod
    def register_ssm(cls, activation):
        cmd = 'amazon-ssm-agent -y -register -code "%s" -id "%s" -region "%s"' % (
            activation["code"],
            activation["id"],
            activation["region"],
        )
        try:
            logger.debug("Running agent registration command: %s" % cmd)
            with proxy_context():
                run_command(cmd)
            logger.debug("Agent registration succeeded")
        except subprocess.CalledProcessError as e:
            die("Agent registration command failed\n%s" % format_command_error(cmd, e), exitcode=110)

    @classmethod
    def activate_ssm(cls, activation):
        cls.stop_ssm_service()
        cls.register_ssm(activation)
        cls.start_ssm_service()

    @staticmethod
    def get_distro():
        def get_id_line(line):
            if line.startswith("ID="):
                return True
            return False

        def get_id(path):
            return file_find(path, get_id_line).split("=")[1].strip()

        centos_release = "/etc/centos-release"
        redhat_release = "/etc/redhat-release"
        os_release = "/etc/os-release"

        log_msg = "Found %s file, assuming that distro is %s"
        if file_exists(centos_release):
            logger.debug(log_msg % (centos_release, DISTROS.CENTOS))
            return DISTROS.CENTOS
        elif file_exists(redhat_release):
            logger.debug(log_msg % (redhat_release, DISTROS.RHEL))
            return DISTROS.RHEL
        elif file_exists(os_release):
            distro_id = get_id(os_release)
            if distro_id:
                logger.debug(log_msg % (os_release, distro_id))
                return distro_id
        die("Could not determine guest operating system Linux distribution.", exitcode=131)


class DistroConfig:
    def __init__(self, default_package_installer_url, regional_package_installer_url, install_cmd, uninstall_cmd, check_installed_cmd):
        self.default_package_installer_url = default_package_installer_url
        self.regional_package_installer_url = regional_package_installer_url
        self.region = None
        self.install_cmd = install_cmd
        self.uninstall_cmd = uninstall_cmd
        self.check_installed_cmd = check_installed_cmd

    @property
    def package_installer_url(self):
        if self.region is None:
            return self.default_package_installer_url

        return self.regional_package_installer_url.format(region=self.region)


class Distro(object):
    UbuntuConfig = DistroConfig(
        default_package_installer_url="https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb",
        regional_package_installer_url="https://amazon-ssm-{region}.s3.{region}.amazonaws.com/latest/debian_amd64/amazon-ssm-agent.deb",
        install_cmd="dpkg -i %s",
        uninstall_cmd="dpkg -r %s" % SSM_SERVICE,
        check_installed_cmd="dpkg -l %s" % SSM_SERVICE,
    )
    DebianConfig = DistroConfig(
        default_package_installer_url="https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb",
        regional_package_installer_url="https://amazon-ssm-{region}.s3.{region}.amazonaws.com/latest/debian_amd64/amazon-ssm-agent.deb",
        install_cmd="dpkg -i %s",
        uninstall_cmd="dpkg -r %s" % SSM_SERVICE,
        check_installed_cmd="dpkg -l %s" % SSM_SERVICE,
    )
    RhelConfig = DistroConfig(
        default_package_installer_url="https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm",
        regional_package_installer_url="https://amazon-ssm-{region}.s3.{region}.amazonaws.com/latest/linux_amd64/amazon-ssm-agent.rpm",
        install_cmd="yum install -y %s",
        uninstall_cmd="yum remove -y %s" % SSM_SERVICE,
        check_installed_cmd="yum list installed %s" % SSM_SERVICE,
    )
    SuseConfig = DistroConfig(
        default_package_installer_url="https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm",
        regional_package_installer_url="https://amazon-ssm-{region}.s3.{region}.amazonaws.com/latest/linux_amd64/amazon-ssm-agent.rpm",
        install_cmd="rpm --install %s",
        uninstall_cmd="rpm -e %s" % SSM_SERVICE,
        check_installed_cmd="rpm -q %s" % SSM_SERVICE,
    )
    CentosConfig = RhelConfig

    @classmethod
    def get_config(cls, distro, region=None):
        if distro == DISTROS.RHEL:
            distro_config = cls.RhelConfig
        elif distro == DISTROS.CENTOS:
            distro_config = cls.CentosConfig
        elif distro == DISTROS.UBUNTU:
            distro_config = cls.UbuntuConfig
        elif distro == DISTROS.DEBIAN:
            distro_config = cls.DebianConfig
        elif distro == DISTROS.SUSE:
            distro_config = cls.SuseConfig
        else:
            die("Operating system '%s' is not unsupported." % distro, exitcode=132)

        distro_config.region = region
        return distro_config


class HttpClient(object):
    request_exceptions = (HTTPException, IOError)

    class Response(object):
        def __init__(self, raw_response):
            self.raw_response = raw_response
            self._content = raw_response.read()

        @property
        def ok(self):
            return self.raw_response.status <= 202

        @property
        def content(self):
            return self._content

        @property
        def text(self):
            return self.content.decode("utf-8")

        def json(self):
            if "application/json" in self.headers["content-type"]:
                return json.loads(self.text)

        @property
        def headers(self):
            return dict((key.lower(), val) for (key, val) in self.raw_response.getheaders())

        @property
        def status(self):
            return self.raw_response.status

        @property
        def reason(self):
            return self.raw_response.reason

        def dump(self):
            return "HTTP Response:\n%s\n%s" % (self.headers, self.text)

        @property
        def full_status(self):
            return " ".join([str(self.status), self.reason])

    class RequestException(IOError):
        def __init__(self, message, **kwargs):
            self.response = kwargs.pop("response", None)
            super(HttpClient.RequestException, self).__init__(message)

    @classmethod
    def get_connection(cls, url, **kwargs):
        global HTTP_PROXY
        if HTTP_PROXY:
            logger.info("Using proxy for connection: %s" % HTTP_PROXY.geturl())
            if url.scheme == "https":
                conn = HTTPSConnection(HTTP_PROXY.hostname, HTTP_PROXY.port, **kwargs)
            elif url.scheme == "http":
                conn = HTTPConnection(HTTP_PROXY.hostname, HTTP_PROXY.port, **kwargs)
            else:
                raise Exception("Invalid scheme for url %s", url.geturl())
            conn.set_tunnel(url.hostname, url.port)
            return conn
        else:
            if url.scheme == "https":
                return HTTPSConnection(url.hostname, **kwargs)
            elif url.scheme == "http":
                return HTTPConnection(url.hostname, **kwargs)
            raise Exception("Invalid scheme for url %s", url.geturl())

    @classmethod
    def download(cls, url, file_path, headers=None):
        headers = headers or {}
        logger.debug("Attempting to download file from: %s" % url)
        u = urlparse(url)
        try:
            c = cls.get_connection(u, timeout=60)
            if u.query:
                path = "?".join([u.path, u.query])
            else:
                path = u.path
            c.request("GET", path, headers=headers)
            response = HttpClient.Response(c.getresponse())
            if not response.ok:
                return response, None
            file_name = u.path.split("/")[-1]
            output_file = os.path.join(file_path, file_name)
            file_write(response.content, output_file, "wb")
            c.close()
            return response, output_file
        except cls.request_exceptions as err:
            raise HttpClient.RequestException("Download request to %s failed: %s" % (url, err))

    @classmethod
    def post_json(cls, url, data=None, headers=None):
        data = data or {}
        headers = headers or {}
        logger.debug("Attempting POST request to: %s" % url)
        headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        u = urlparse(url)
        try:
            c = cls.get_connection(u, timeout=15)
            if u.query:
                path = "?".join([u.path, u.query])
            else:
                path = u.path
            c.request("POST", path, headers=headers, body=json.dumps(data))
            return HttpClient.Response(c.getresponse())
        except cls.request_exceptions as err:
            raise HttpClient.RequestException("POST request to %s failed: %s" % (url, err))

    @classmethod
    def get_json(cls, url, headers=None):
        headers = headers or {}
        headers.update({"Accept": "application/json"})
        return cls.get(url, headers)

    @classmethod
    def get(cls, url, headers=None):
        headers = headers or {}
        logger.debug("Attempting GET request to: %s with headers: %s" % (url, headers))
        u = urlparse(url)
        try:
            c = cls.get_connection(u, timeout=10)
            if u.query:
                path = "?".join([u.path, u.query])
            else:
                path = u.path
            c.request("GET", path, headers=headers)
            return HttpClient.Response(c.getresponse())
        except cls.request_exceptions as err:
            raise HttpClient.RequestException("GET request to %s failed: %s" % (url, err))


def reset_formatter(formatter_name="agent_bootstrap_stream_logs"):
    handler = list(filter(lambda handler: handler._name == formatter_name, logger.handlers))[0]
    handler.formatter = None


def die(msg, details="", exitcode=1):
    if result_format == "json":
        reset_formatter()
        logger.warning(result_delimiter % "Failed")
        logger.warning(as_json(level="WARN", message=msg, details=details))
    else:
        if details:
            detailed_msg = "%s: %s" % (msg, details)
        else:
            detailed_msg = msg
        logger.warning(as_text(level="WARN", message=detailed_msg))
    exit(exitcode)


def success(msg, details="", exitcode=0):
    if result_format == "json":
        reset_formatter()
        logger.debug(result_delimiter % "Success")
        logger.debug(as_json(level="DEBUG", message=msg, details=details))
    else:
        if details:
            detailed_msg = "%s: %s" % (msg, details)
        else:
            detailed_msg = msg
        logger.debug(as_text(level="DEBUG", message=detailed_msg))
    exit(exitcode)


class PlatformServices(object):
    get_job_attempts = 10
    get_job_delay = 10

    @classmethod
    def get_activation(cls, platform):
        activation_url = platform.get_activation_url()
        logger.debug("Getting auth token for agent activation on platform: %s" % platform.name)
        token = platform.get_token()
        logger.debug("Requesting agent activation: %s" % activation_url)
        response = HttpClient.post_json(activation_url, headers={"X-Auth-Token": token, "User-Agent": "Rackspace-SSM-Bootstrap/2.0"})
        if not response.ok:
            die("POST request to activation url %s failed: %s\n%s" % (activation_url, response.full_status, response.dump()), exitcode=108)
        if not response.headers.get("location"):
            die("POST request to activation url %s did not return a Location header\n%s" % (activation_url, response.dump()), exitcode=109)
        job_url = response.headers["location"]
        logger.debug("Agent activation request responded with job: %s", job_url)
        job = cls.get_job(job_url, token)
        return {
            "code": job["message"]["activation_code"],
            "id": job["message"]["activation_id"],
            "region": job["message"]["region"],
            "system_account": job["message"]["system_account"],
        }

    @staticmethod
    def format_job(job):
        return "Job Details:\n%s" % json.dumps(job)

    @classmethod
    def get_job(cls, job_url, token):
        job_data = None
        for attempt in range(1, cls.get_job_attempts):
            logger.debug("Requesting agent activation job (attempt: %d): %s" % (attempt, job_url))
            response = HttpClient.get_json(job_url, headers={"X-Auth-Token": token})
            if not response.ok:
                die("GET request to job url %s failed: %s\nResponse:\n%s" % (job_url, response.full_status, response.dump()), exitcode=105)
            job_data = response.json()["data"]
            logger.debug("Job data: %s" % job_data)
            job = job_data["items"][0]
            if job["status"] == "RUNNING":
                logger.debug("Agent activation job %s still running, checking again in %d seconds" % (job_url, cls.get_job_delay))
                time.sleep(cls.get_job_delay)
            elif job["status"] != "SUCCEEDED":
                die(
                    "Agent activation job %s completed unsuccessfully (status: %s).\n%s" % (job_url, job["status"], PlatformServices.format_job(job)),
                    exitcode=106,
                )
            elif job["status"] == "SUCCEEDED":
                logger.debug("Agent activation job %s completed successfully.\n%s" % (job_url, PlatformServices.format_job(job)))
                return job
        die(
            "Agent activation job %s did not complete after %d attempts.\nLast %s" % (job_url, cls.get_job_attempts, PlatformServices.format_job(job)),
            exitcode=107,
        )


class Package(object):
    @staticmethod
    def download_installer(region=None):
        distro = GuestOs.get_distro()
        distro_config = Distro.get_config(distro, region)
        try:
            target_dir = tempfile.mkdtemp()
            logger.debug("Downloading SSM package installer from %s to %s" % (distro_config.package_installer_url, target_dir))
            response, output_path = HttpClient.download(distro_config.package_installer_url, target_dir)
            if not response.ok:
                die("Downloading SSM package installer from %s failed:\n%s" % (distro_config.package_installer_url, response.dump()), exitcode=126)
            logger.debug("Download complete, SSM installer path: %s" % output_path)
            return output_path
        except HTTPException:
            logger.exception("Failed to download SSM package installer from %s" % distro_config.package_installer_url)
            exit(1)


def configure_ssm_profile():
    config_dir = "/etc/amazon/ssm"
    template_file = os.path.join(config_dir, "amazon-ssm-agent.json.template")
    config_file = os.path.join(config_dir, "amazon-ssm-agent.json")
    is_profile_updated = False

    try:
        # If config file doesn't exist, create it from template
        if not os.path.exists(config_file):
            if os.path.exists(template_file):
                logger.debug("Creating SSM agent configuration file from template")
                shutil.copy(template_file, config_file)
            else:
                logger.debug("SSM agent template configuration file not found: %s", template_file)
                return False

        # Read and update the configuration file
        with open(config_file, "r") as f:
            config = json.load(f)

        # Ensure Profile section exists
        if "Profile" not in config:
            config["Profile"] = {}

        # Update only the ShareProfile setting if it's different
        if config["Profile"].get("ShareProfile") != "rackspace":
            config["Profile"]["ShareProfile"] = "rackspace"
            is_profile_updated = True

        # Write the updated configuration only if changes were made
        if is_profile_updated:
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            logger.info("Updated SSM agent configuration to use 'rackspace' profile")
        else:
            logger.debug("SSM agent configuration already has 'rackspace' profile")

    except Exception:
        logger.exception("Failed to update SSM agent configuration")

    return is_profile_updated


def configure_proxy(proxy_uri):
    config_directory = "/etc/systemd/system/amazon-ssm-agent.service.d"
    if not os.path.exists(config_directory):
        os.mkdir(config_directory)
    if command_exists("systemctl"):
        file = open(os.path.join(config_directory, "override.conf"), "w")
        override = """[Service]
Environment=\"http_proxy=%s\"
Environment=\"https_proxy=%s"
Environment=\"no_proxy=169.254.169.254\"
""".strip()
        file.write(override % (proxy_uri, proxy_uri))
        file.close()
        # reloading the modified unit files
        run_command("systemctl daemon-reload")
    else:
        die("systemctl command not found in $PATH, bootstrap install cannot continue.", exitcode=130)


def install(options):
    platform = Platform.get(options.platform)
    logger.debug("Executing install command on platform %s" % platform.name)
    try:
        if GuestOs.is_agent_disabled(platform):
            success("Found a truthy value for '%s' in %s metadata, skipping agent installation" % (IGNORE_TAG_KEY, options.platform))
        else:
            logger.debug("Agent install is enabled, '%s' not found in metadata" % IGNORE_TAG_KEY)

        if not GuestOs.is_ssm_package_installed():
            package_installer_path = Package.download_installer(region=options.installer_download_region)
            GuestOs.install_ssm_package(package_installer_path)

        # Always configure the SSM profile
        is_profile_updated = configure_ssm_profile()

        registration = GuestOs.get_agent_information()
        if registration:
            logger.debug("Agent is already registered: %s" % registration)
            if is_profile_updated:
                GuestOs.stop_ssm_service()

            GuestOs.start_ssm_service()
            GuestOs.check_ssm_activation()
            exit(0)

        activation = PlatformServices.get_activation(platform)
        if options.http_proxy:
            configure_proxy(options.http_proxy)
        GuestOs.activate_ssm(activation)
        logger.debug("Waiting %d seconds before checking agent activation status" % REGISTRATION_WAIT)
        time.sleep(REGISTRATION_WAIT)
        GuestOs.check_ssm_activation()
    except HttpClient.RequestException as err:
        die(str(err), exitcode=115)


def uninstall(options):
    logger.debug("Executing uninstall command")
    if not GuestOs.is_ssm_package_installed():
        die("Package amazon-ssm-agent is not currently installed", exitcode=116)
    GuestOs.clear_agent_registration()
    GuestOs.uninstall_ssm_package()
    success("Agent was successfully uninstalled")


def reregister(options):
    platform = Platform.get(options.platform)
    logger.debug("Executing reregister command on platform %s" % platform.name)
    try:
        if GuestOs.is_agent_disabled(platform):
            success("Found a truthy value for '%s' in %s metadata, skipping agent reregistration" % (IGNORE_TAG_KEY, options.platform))
        else:
            logger.debug("Agent install is enabled, '%s' not found in metadata" % IGNORE_TAG_KEY)

        if not GuestOs.is_ssm_package_installed():
            die("SSM package is not installed, cannot reregister agent", exitcode=128)

        GuestOs.clear_agent_registration()
        activation = PlatformServices.get_activation(platform)
        GuestOs.activate_ssm(activation)
        logger.debug("Waiting %d seconds before checking agent activation status" % REGISTRATION_WAIT)
        time.sleep(REGISTRATION_WAIT)
        GuestOs.check_ssm_activation()
        success("Agent was successfully reregistered")
    except HttpClient.RequestException as err:
        die(str(err), exitcode=117)


def main(args):
    global logger
    global result_format
    global HTTP_PROXY
    global PLATFORM_SERVICES_BASE_URL

    scriptname = os.path.basename(__file__)

    parser = argparse.ArgumentParser(
        prog=scriptname,
        description="Rackspace management agent bootstrap script.",
        formatter_class=RawTextHelpFormatter,
        epilog="Exit Codes the script returns:\nExitcode: Description\n%s" % EXIT_CODES_FOR_EPILOG,
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=logging.DEBUG,
        choices=("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"),
    )

    parser.add_argument(
        "--result-format",
        dest="result_format",
        default="text",
        choices=("text", "json"),
    )

    parser.add_argument(
        "--http-proxy",
        dest="http_proxy",
        help="HTTP proxy to use for agent installation (example: http://proxy.example.com:8080)",
        required=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands:")
    subparsers.required = True

    install_cmd = subparsers.add_parser("install", help="Bootstrap agent")
    install_cmd.add_argument(
        "-p",
        "--platform",
        help="Supported managed platform",
        choices=PLATFORMS,
        required=True,
    )
    install_cmd.add_argument(
        "--installer-download-region",
        metavar="region",
        help="AWS region to download SSM Agent installer from",
        required=False,
    )
    install_cmd.add_argument(
        "--platform-services-base-url",
        metavar="url",
        help="Platform Services API endpoint (default: {})".format(PLATFORM_SERVICES_BASE_URL),
        required=False,
        default=PLATFORM_SERVICES_BASE_URL,
    )

    uninstall_cmd = subparsers.add_parser("uninstall", help="Uninstall agent")
    uninstall_cmd.add_argument(
        "--platform-services-base-url",
        metavar="url",
        help="Platform Services API endpoint (default: {})".format(PLATFORM_SERVICES_BASE_URL),
        required=False,
        default=PLATFORM_SERVICES_BASE_URL,
    )

    reregister_cmd = subparsers.add_parser("reregister", help="Reregister agent")
    reregister_cmd.add_argument(
        "-p",
        "--platform",
        help="Supported managed platform",
        choices=PLATFORMS,
        required=True,
    )
    reregister_cmd.add_argument(
        "--platform-services-base-url",
        metavar="url",
        help="Platform Services API endpoint (default: {})".format(PLATFORM_SERVICES_BASE_URL),
        required=False,
        default=PLATFORM_SERVICES_BASE_URL,
    )

    options = parser.parse_args(args)

    result_format = options.result_format
    PLATFORM_SERVICES_BASE_URL = options.platform_services_base_url

    if os.geteuid() != 0:
        print("You need to have root privileges to run this script. Please try again, this time using 'sudo'")
        exit(1)

    if options.http_proxy:
        HTTP_PROXY = urlparse(options.http_proxy)
        logger.info("Using http proxy: %s" % HTTP_PROXY.geturl())
    if options.command == "install":
        install(options)
    elif options.command == "uninstall":
        uninstall(options)
    elif options.command == "reregister":
        reregister(options)
    else:
        logger.error("Unknown command: %s, exiting..." % options.command)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])