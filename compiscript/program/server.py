from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
import os

app = Flask(__name__)
CORS(app)

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    code = data.get('code', '')

    # Guardar el código en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.cps') as tmp:
        tmp.write(code.encode('utf-8'))
        tmp_path = tmp.name

    # Ejecutar el compilador
    try:
        result = subprocess.run(
            ['python3', 'Driver.py', tmp_path],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        output = result.stdout.decode('utf-8')
        errors = result.stderr.decode('utf-8')
    except Exception as e:
        output = ''
        errors = str(e)

    # Eliminar el archivo temporal
    os.unlink(tmp_path)

    return jsonify({'output': output, 'errors': errors})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)