from flask import Flask, request, jsonify, render_template
import os
import time
from werkzeug.utils import secure_filename
import openai
import pdfplumber


app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = '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'

# Dosya yükleme ayarları
UPLOAD_FOLDER = 'uploads'  # Yüklenecek dosyaların saklanacağı klasör
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'zip'}  # İzin verilen dosya türleri

# Klasör kontrolü
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Dosyanın uzantısını kontrol eder."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-request', methods=['POST'])
def process_request():
    """Hem mesaj hem de dosya işlemlerini OpenAI API ile yapar."""
    message = request.form.get('message')  # Gelen mesaj
    file = request.files.get('file')      # Gelen dosya

    file_content = ""

    # Dosya işleme (varsa)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            if filename.endswith(".pdf"):
                from pdfplumber import open
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        file_content += page.extract_text()
            elif filename.endswith(".txt"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            elif filename.endswith(".docx"):
                from docx import Document
                doc = Document(file_path)
                for para in doc.paragraphs:
                    file_content += para.text + "\n"
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    # OpenAI API çağrısı
    try:
        prompt = (
            "Your task is to assist users in crafting professional resumes and cover letters "
            "tailored to specific job positions or industries. Provide concise, clear, and impactful "
            "suggestions, focusing on highlighting the user's skills, experiences, and achievements."
        )
        if message and file_content:
            prompt += f"\n\nUser message: {message}\nFile content: {file_content}"
        elif message:
            prompt += f"\n\nUser message: {message}"
        elif file_content:
            prompt += f"\n\nFile content: {file_content}"

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify({'response': response.choices[0].message.content.strip()})

    except openai.error.OpenAIError as e:
        return jsonify({'error': f'OpenAI error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
