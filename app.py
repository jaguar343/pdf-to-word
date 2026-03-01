import os
import uuid
import tempfile
import io
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pdf2docx import Converter
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are accepted.'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        uid = uuid.uuid4().hex[:8]
        safe_name = secure_filename(file.filename) or f'upload_{uid}.pdf'
        pdf_path = os.path.join(tmpdir, f'{uid}_{safe_name}')
        docx_name = safe_name.rsplit('.', 1)[0] + '.docx'
        docx_path = os.path.join(tmpdir, f'{uid}_{docx_name}')

        file.save(pdf_path)

        try:
            cv = Converter(pdf_path)
            cv.convert(docx_path, start=0, end=None)
            cv.close()
        except Exception as e:
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

        if not os.path.exists(docx_path):
            return jsonify({'error': 'Conversion produced no output.'}), 500

        # Read file into memory BEFORE temp directory is deleted
        # Fixes Windows WinError 32 file locking issue
        with open(docx_path, 'rb') as f:
            file_bytes = io.BytesIO(f.read())

    # Temp directory now cleaned up - send from memory
    file_bytes.seek(0)
    return send_file(
        file_bytes,
        as_attachment=True,
        download_name=docx_name,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
