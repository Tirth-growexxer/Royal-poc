"""
secret_manager.py

This module provides functionality to retrieve secrets such as usernames and passwords
from Oracle Cloud Infrastructure (OCI) Vault. It reads secret OCIDs from a configuration file
and securely fetches their values using OCI's Instance Principals authentication.

Classes:
    SecretManager: Manages the retrieval of API and database credentials from OCI Vault.

Dependencies:
    - oci (Oracle Cloud Infrastructure Python SDK)
    - configparser
    - logger_config (custom logger module)

Configuration:
    The module expects a `config.ini` file with the following sections and keys:

    [AUTH]
    login_username_ocid=<OCID for API login username>
    login_password_ocid=<OCID for API login password>

    [ADW]
    adw_user_oci=<OCID for ADW username>
    adw_password_oci=<OCID for ADW password>
"""
import oci
from configparser import ConfigParser
import json



class SecretManager(object):
    """
    Handles retrieval of secrets (usernames and passwords) from OCI Vault using OCIDs
    provided in a configuration file.
    """
    def __init__(self):
        """
        Initializes the SecretManager by reading secret OCIDs from a local config file (./config.ini).
        The config file must have sections 'AUTH' and 'ADW' with corresponding keys.
        """
        try:
            config = ConfigParser()
            with open('config.json') as config_file:
                config = json.load(config_file)

            self.EMAIL_USERNAME_SECRET_OCID = config['smtp_username']
            self.EMAIL_PASSWORD_SECRET_OCID = config['smtp_password']
            print(self.EMAIL_USERNAME_SECRET_OCID)
            print(self.EMAIL_PASSWORD_SECRET_OCID)
        except Exception as e:
            raise Exception(f"Failed to read config file or missing keys: {e}")


    @staticmethod
    def get_secret_from_oci(secret_ocid: str) -> str:
        """
        Retrieves a secret value from OCI Vault using its OCID.

        Args:
            secret_ocid (str): The OCID of the secret to retrieve.

        Returns:
            str: The decoded secret string (base64-decoded if needed).
        """
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        secrets_client = oci.secrets.SecretsClient({}, signer=signer)

        response = secrets_client.get_secret_bundle(secret_ocid)
        if not response.data.secret_bundle_content.content_type=="BASE64":
            content = response.data.secret_bundle_content.content
            return content
        else:
            content = response.data.secret_bundle_content.content
            import base64
            return base64.b64decode(content).decode()

    def get_secret(self, default=None):
        """
        Fetches all configured secrets (email and DB credentials) from OCI Vault.

        Args:
            default (Any, optional): Value to return if an error occurs. Defaults to None.

        Returns:
            dict or Any: A dictionary with keys:
                - email_username
                - email_password
            or the fallback `default` if retrieval fails.
        """
        try:
            email_username = self.get_secret_from_oci(self.EMAIL_USERNAME_SECRET_OCID)
            email_password = self.get_secret_from_oci(self.EMAIL_PASSWORD_SECRET_OCID)
            return {
                "email_username":email_username,
                "email_password":email_password
            }
        except Exception as e:
            print(f"Failed to retrieve secret: usernames and passwords -> {e}")
            return default

