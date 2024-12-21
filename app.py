from flask import Flask, request, jsonify, render_template
import os
import time
from werkzeug.utils import secure_filename
import openai
import pdfplumber
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükleyin
load_dotenv()


app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

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
            "You are an expert assistant specializing in creating professional CVs and tailored cover letters for specific job applications. "
            "Your role is to help users craft a CV and cover letter that effectively highlight their strengths and align with the job requirements. "
            "Ensure the CV includes the following sections:\n"
            "- **Contact Information**: Full name, phone number, email address, and LinkedIn profile (if applicable).\n"
            "- **Professional Summary**: A concise, impactful statement summarizing the user's expertise, skills, and career goals.\n"
            "- **Work Experience**: Detailed descriptions of relevant roles, responsibilities, achievements, and measurable results.\n"
            "- **Education**: Academic qualifications, degrees, relevant coursework, and honors.\n"
            "- **Skills**: A list of both technical and soft skills tailored to the job requirements.\n"
            "- **Certifications and Trainings**: Industry-recognized certifications or additional education.\n"
            "- **Languages**: Spoken and written languages with proficiency levels.\n"
            "- **Projects**: Notable projects that showcase expertise and measurable impact.\n"
            "\n"
            "In addition, create a personalized and compelling cover letter for the specific company and job title provided by the user. The cover letter should include:\n"
            "- **Opening Paragraph**: A strong introduction explaining the user's interest in the company and role, referencing specific details about the company.\n"
            "- **Middle Section**: Highlights of key achievements, experiences, and skills that align with the job description and company values.\n"
            "- **Closing Paragraph**: A call to action expressing enthusiasm for the role, a willingness to contribute to the company's success, and a request for next steps (e.g., an interview).\n"
            "\n"
            "Both the CV and cover letter should be professional, concise, and customized to showcase the user's strengths and alignment with the job requirements."
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
