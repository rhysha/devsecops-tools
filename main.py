from flask import Flask, request, jsonify
import subprocess
import os
import shutil
from datetime import datetime
import json
import urllib.parse 

app = Flask(__name__)

# Ensure repo directory exists
if not os.path.exists("repo"):
    os.makedirs("repo")

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

# Build Docker image and run SCA scan with Grype
def run_sca_scan(directory, dockerfile):
    dockerfile_path = os.path.join(directory, dockerfile)
    if not os.path.exists(dockerfile_path):
        return {"error": "Dockerfile not found"}
    
    image_tag = f"sca_scan_image_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    build_cmd = ["docker", "build", "-t", image_tag, "-f", dockerfile_path, directory]
    build_result = subprocess.run(build_cmd, capture_output=True, text=True)
    
    if build_result.returncode != 0:
        return {"error": "Failed to build Docker image", "details": build_result.stderr}
    
    scan_cmd = ["grype", image_tag, "-o", "json"]
    scan_result = subprocess.run(scan_cmd, capture_output=True, text=True)
    
    try:
        output = json.loads(scan_result.stdout)
    except json.JSONDecodeError:
        output = scan_result.stdout
    
    return {"output": output if scan_result.returncode == 0 else scan_result.stderr}

# Run SAST scan with Bearer
def run_sast_scan(directory):
    result = subprocess.run(["bearer", "scan", directory, "--format", "json"], capture_output=True, text=True)
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = result.stdout
    return {"output": output if result.returncode == 0 else result.stderr}

@app.route("/scan/run_sca_scan", methods=["GET"])
def run_sca_scan_endpoint():
    git_url = request.args.get("git_url")
    branch = request.args.get("branch", "main")
    dockerfile = request.args.get("dockerfile", "Dockerfile")
    
    repo_path, error = clone_repo(git_url, branch)
    if error:
        return jsonify({"error": "Failed to clone repo", "details": error}), 400
    
    result = run_sca_scan(repo_path, dockerfile)
    return jsonify(result)

@app.route("/scan/run_sast_scan", methods=["GET"])
def run_sast_scan_endpoint():
    git_url = request.args.get("git_url")
    branch = request.args.get("branch", "main")
    
    repo_path, error = clone_repo(git_url, branch)
    if error:
        return jsonify({"error": "Failed to clone repo", "details": error}), 400
    
    result = run_sast_scan(repo_path)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
