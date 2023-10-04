import os
import requests
import zipfile
import json
import tempfile

class NugetLoader:
    def __init__(self, package_name):
        self.package_name = package_name
        self.temp_dir = tempfile.TemporaryDirectory()

    def _get_latest_version(self):
        nuget_api_url = f"https://api.nuget.org/v3/registration5-semver1/{self.package_name}/index.json"
        response = requests.get(nuget_api_url)
        response.raise_for_status()
        data = response.json()
        return data['items'][-1]['items'][-1]['catalogEntry']['version']

    def _download_package(self, version):
        nuget_url = f"https://www.nuget.org/api/v2/package/{self.package_name}/{version}"
        response = requests.get(nuget_url, stream=True)
        response.raise_for_status()
        file_path = os.path.join(self.temp_dir.name, f"{self.package_name}.{version}.nupkg")
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return file_path

    def _extract_package(self, file_path):
        extract_folder = os.path.join(self.temp_dir.name, os.path.basename(file_path).replace('.nupkg', ''))
        os.makedirs(extract_folder, exist_ok=True)
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        return extract_folder

    def _read_content(self, package_dir, content_file=""):
        content_files = [os.path.join(package_dir, "content", f) for f in os.listdir(f"{package_dir}/content")]
        if not content_files:
            raise Exception("No content file exists")

        if len(content_files) > 1:
            raise Exception(f"Please specify content file: {content_files}")

        try:
            with open(content_files[0], 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            existing_files = "\n".join(os.listdir(f"{package_dir}/content"))
            raise FileNotFoundError(f"{content_files[0]} not found in the nupkg file.\nExisting files:\n{existing_files}")
    
        return data

    def load(self, content_filename, version=None, cleanup=True):
        try:
            if version == None:
                version = self._get_latest_version()
            nuget_file = self._download_package(version)
            nuget_dir = self._extract_package(nuget_file)
            content = self._read_content(nuget_dir, content_filename)
        finally:
            if cleanup:
                self.temp_dir.cleanup()
        return content
