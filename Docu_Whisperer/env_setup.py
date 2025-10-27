# env_setup.py
import os
import sys
import subprocess

def setup_environment():
    ca_bundle_path = os.path.expanduser("~/ca_bundle.pem")

    if sys.platform == "darwin":
        subprocess.run([
            "security", "find-certificate", "-a", "-p",
            "/Library/Keychains/System.keychain",
            "/System/Library/Keychains/SystemRootCertificates.keychain",
            os.path.expanduser("~/Library/Keychains/login.keychain-db")
        ], stdout=open(ca_bundle_path, "w"))
    elif sys.platform == "win32":
        subprocess.run([
            "powershell", "-Command",
            "Get-ChildItem Cert:\\LocalMachine\\Root, Cert:\\LocalMachine\\CA, Cert:\\CurrentUser\\Root | "
            "Where-Object { ! $_.PsIsContainer } | "
            "ForEach-Object { $_.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert) } | "
            f"Set-Content -Encoding ascii -Path {ca_bundle_path}"
        ])

    os.environ["OPENAI_BASE_URL"] = "https://api.studio.genai.cba"
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + (",.cba" if os.environ.get("NO_PROXY") else ".cba")

    if os.path.exists(ca_bundle_path):
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle_path
        os.environ["SSL_CERT_FILE"] = ca_bundle_path

def get_api_key():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable when running the Docker container.")
    return api_key