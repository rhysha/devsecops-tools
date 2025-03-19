from flask import Flask, request, jsonify
import subprocess
import os
import shutil
from datetime import datetime
import json
import urllib.parse  # Import URL decoding module

app = Flask(__name__)

# Function to clone repo
def clone_repo(git_url, branch):
    git_url = urllib.parse.unquote(urllib.parse.unquote(git_url))  # Decode URL twice
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    repo_name = git_url.split("/")[-1].replace(".git", "")
    repo_dir = os.path.join("repo", f"{repo_name}_{timestamp}")
    
    clone_cmd = ["git", "clone", "--branch", branch, "--depth", "1", git_url, repo_dir]
    result = subprocess.run(clone_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr
    return repo_dir, None

# Pull Docker image and run SCA scan with Grype
def run_sca_scan(image_name):
    pull_cmd = ["docker", "pull", image_name]
    pull_result = subprocess.run(pull_cmd, capture_output=True, text=True)
    
    if pull_result.returncode != 0:
        return {"error": "Failed to pull Docker image", "details": pull_result.stderr}
    
    scan_cmd = ["grype", image_name]
    scan_result = subprocess.run(scan_cmd, capture_output=True, text=True)
    
    return scan_result.stdout if scan_result.returncode == 0 else scan_result.stderr

@app.route("/scan/run_sca_scan", methods=["GET"])
def run_sca_scan_endpoint():
    image_name = request.args.get("image_name")
    
    if not image_name:
        return jsonify({"error": "Missing image_name"}), 400
    
    result = run_sca_scan(image_name)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)