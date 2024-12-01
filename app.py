from flask import Flask, render_template, request, send_file
import pandas as pd
import os
import random
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def filter_questions(data, exclude_nice_for_laq=True):
    """
    Filter questions based on criteria:
    - Exclude Nice to Know (N) for LAQ if specified.
    """
    if exclude_nice_for_laq:
        data = data[~((data['LAQ/ SAQ/ BAQ/ MCQ'] == 'LAQ') & (data['Must know/ Desirable to know / Nice to know (M/D/N)'] == 'N'))]
    return data

def generate_question_paper(data, question_counts):
    """
    Generate a question paper ensuring:
    - No repeated competency numbers.
    - The specified number of questions for each type (LAQ, SAQ, etc.).
    """
    selected_questions = pd.DataFrame()
    used_competency_numbers = set()
    
    for q_type, count in question_counts.items():
        filtered = data[data['LAQ/ SAQ/ BAQ/ MCQ'] == q_type]
        filtered = filtered[~filtered['COMP. NO'].isin(used_competency_numbers)]
        
        if len(filtered) < count:
            count = len(filtered)  # Adjust count to available questions
        
        chosen = filtered.sample(count)
        selected_questions = pd.concat([selected_questions, chosen], ignore_index=True)
        used_competency_numbers.update(chosen['COMP. NO'])
    
    return selected_questions

def create_pdf(question_paper, output_file):
    """
    Generate a PDF for the question paper.
    """
    c = canvas.Canvas(output_file, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Question Paper")
    y -= 30

    # Add questions
    for index, row in question_paper.iterrows():
        question_type = row['LAQ/ SAQ/ BAQ/ MCQ']
        question_text = row['Questions']
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, f"{question_type}:")
        y -= 20

        c.setFont("Helvetica", 10)
        lines = question_text.split("\n")
        for line in lines:
            c.drawString(margin + 20, y, line.strip())
            y -= 15

        # Move to the next page if needed
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - margin

    c.save()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle file upload
        if 'file' not in request.files:
            return render_template('index.html', error="No file part")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error="No selected file")
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        try:
            data = pd.read_excel(file_path)
            data = filter_questions(data)
        except Exception as e:
            return render_template('index.html', error=f"Error processing file: {e}")
        
        # Get question counts from form
        try:
            laq_count = int(request.form.get('laq_count', 0))
            saq_count = int(request.form.get('saq_count', 0))
            baq_count = int(request.form.get('baq_count', 0))
            mcq_count = int(request.form.get('mcq_count', 0))
            
            question_counts = {
                'LAQ': laq_count,
                'SAQ': saq_count,
                'BAQ': baq_count,
                'MCQ': mcq_count
            }
            
            question_paper = generate_question_paper(data, question_counts)
            
            if question_paper.empty:
                return render_template('index.html', error="No questions could be selected. Please adjust your criteria.")
            
            output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'question_paper.pdf')
            create_pdf(question_paper, output_file)
            return render_template('index.html', success=True, download_link='/download')
        except Exception as e:
            return render_template('index.html', error=f"Error generating question paper: {e}")
    
    return render_template('index.html')

@app.route('/download')
def download():
    output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'question_paper.pdf')
    return send_file(output_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

