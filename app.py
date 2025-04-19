from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os
import requests

app = Flask(__name__)

OCTOPRINT_URL = "http://ender3neo.local"  # Replace with your OctoPrint URL
OCTOPRINT_API_KEY = "7OAokKDCOlLmcsvXKswEW7niqNiL7JaT7lIGBBOXHlw"  # Replace with your OctoPrint API key

# Define absolute paths for temp files
TEMP_STL_PATH = os.path.abspath("temp.stl") # Should save in the same directory as app.py
OUTPUT_GCODE_PATH = os.path.abspath("output.gcode")

def upload_and_print(gcode_path):
    headers = {"X-Api-Key": OCTOPRINT_API_KEY}
    files = {"file": open(gcode_path, "rb")}
    try:
        r = requests.post(f"{OCTOPRINT_URL}/api/files/local", headers=headers, files=files)
        r.raise_for_status()  # Raise an exception for bad status codes
        filename = os.path.basename(gcode_path)
        payload = {"command": "select", "print": True}
        r = requests.post(f"{OCTOPRINT_URL}/api/files/local/{filename}", headers=headers, json=payload)
        r.raise_for_status()
        return True, "Print started"
    except requests.exceptions.RequestException as e:
        return False, f"OctoPrint communication error: {e}"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html') #serve index.html

@app.route('/slice_and_print', methods=['POST'])
def slice_and_print():
    stl_file = request.files['stlFile']
    layer_height = request.form['layerHeight']
    infill = request.form['infill']

    try:
        stl_file.save(TEMP_STL_PATH)
        print(f"STL file saved to: {TEMP_STL_PATH}")
        prusaslicer_executable = '/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/prusaslicer'
        config_file_path = "/Users/jdyun/Desktop/webapp/neov2_config.ini"
        prusaslicer_command = [
            prusaslicer_executable,
            "--slice",
            TEMP_STL_PATH,
            "--output", OUTPUT_GCODE_PATH,
            "--layer-height", layer_height,
            "--fill-density", infill + "%",
            "--load", config_file_path
        ]
        print(f"PrusaSlicer Command: {prusaslicer_command}")
        print(f"TEMP_STL_PATH: {TEMP_STL_PATH}")
        print(f"OUTPUT_GCODE_PATH: {OUTPUT_GCODE_PATH}")
        result = subprocess.run(
            prusaslicer_command,
            capture_output=True,
            text=True,
            env=os.environ,
            cwd='.'
        )

        print(f"PrusaSlicer Return Code: {result.returncode}")  # Print the return code
        print(f"PrusaSlicer Stdout:\n{result.stdout}")
        print(f"PrusaSlicer Stderr:\n{result.stderr}")

        if result.returncode != 0:
            os.remove(TEMP_STL_PATH)
            error_message = f"PrusaSlicer failed with exit code {result.returncode}:\nStdout: {result.stdout}\nStderr: {result.stderr}"
            print(error_message)
            return jsonify({"error": error_message}), 500

    except Exception as e:
        os.remove(TEMP_STL_PATH)
        print(f"Python Error during slicing: {e}")
        return jsonify({"error": f"Error: {e}"}), 500

    # success, message = upload_and_print(OUTPUT_GCODE_PATH)
    # os.remove(TEMP_STL_PATH)
    # os.remove(OUTPUT_GCODE_PATH)
    return jsonify({"message": "G-code generated successfully (OctoPrint integration skipped)"}), 200

    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 500

if __name__ == '__main__':
    app.run(debug=True)