from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def index():
    html_path = '/Users/jdyun/Desktop/minimal_index.html'  # Replace with the actual path you got
    with open(html_path, 'r') as f:
        return f.read()

@app.route('/slice', methods=['POST'])
def slice_only():
    stl_file = request.files['stlFile']
    layer_height = request.form['layerHeight']
    infill = request.form['infill']

    TEMP_STL_PATH = os.path.abspath("temp_minimal.stl")
    OUTPUT_GCODE_PATH = os.path.abspath("doesthiswork.gcode")
    config_file_path = "/Users/jdyun/Desktop/neov2_config.ini"

    try:
        stl_file.save(TEMP_STL_PATH)
        prusaslicer_executable = '/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/prusaslicer'
        prusaslicer_command = [
            prusaslicer_executable,
            "--slice",
            TEMP_STL_PATH,
            "--output", OUTPUT_GCODE_PATH,
            "--layer-height", layer_height,
            "--fill-density", infill + "%",
            "--load", config_file_path
        ]
        result = subprocess.run(prusaslicer_command, check=True, capture_output=True, text=True, env=os.environ, cwd='.')

        if result.returncode != 0:
            os.remove(TEMP_STL_PATH)
            return jsonify({"error": f"PrusaSlicer failed: {result.stderr}"}), 500

        os.remove(TEMP_STL_PATH)
        return jsonify({"gcode_path": OUTPUT_GCODE_PATH}), 200

    except Exception as e:
        if os.path.exists(TEMP_STL_PATH):
            os.remove(TEMP_STL_PATH)
        return jsonify({"error": f"Error: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)