import os
import logging
import google.generativeai as genai
import PyPDF2
import docx
import requests
from bs4 import BeautifulSoup  # type: ignore
import re
from flask import Flask, request, jsonify, render_template  # Import render_template



# Setup logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)



# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

# Function to extract text from a Word (.docx) file
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return '\n'.join(full_text)

# Function to extract text from a TXT file
def extract_text_from_txt(txt_path):
    with open(txt_path, 'r') as file:
        return file.read()

# Function to extract text from a webpage
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract text from webpage (you can customize this further to focus on certain parts of the page)
        text = soup.get_text(separator='\n')
        return text.strip()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch webpage content: {e}")
    


# Function to check if a string is a valid URL
def is_valid_url(url):
    regex = re.compile(
        r'^(https?|ftp)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None



# Function to extract content based on file type or URL
def extract_text_from_source(source):
    if is_valid_url(source):
        print("Valid URL found, extracting text from webpage...")
        return extract_text_from_url(source)
    
    file_extension = os.path.splitext(source)[1].lower()

    if file_extension == '.pdf':
        return extract_text_from_pdf(source)
    elif file_extension == '.docx':
        return extract_text_from_docx(source)
    elif file_extension == '.txt':
        return extract_text_from_txt(source)
    else:
        raise ValueError(f"Unsupported file type or invalid URL: {source}")
    


# Paths to the possible files containing system instructions
docx_file_path = "data.docx"
pdf_file_path = "data.pdf"
txt_file_path = "data.txt"
url = "http://www.trivelleshotels.pk"  # Example URL, replace with an actual URL if needed



# Check if the file exists or if it's a URL and choose accordingly
if os.path.exists(pdf_file_path):
    source = pdf_file_path
    print("PDF file found, extracting text from PDF...")
elif os.path.exists(docx_file_path):
    source = docx_file_path
    print("Word file found, extracting text from DOCX...")
elif os.path.exists(txt_file_path):
    source = txt_file_path
    print("TXT file found, extracting text from TXT...")
elif is_valid_url(url):
    source = url
    print("URL found, extracting text from the website...")
else:
    print("No valid file or URL found!")
    exit()

# Extract the system instruction from the provided source (file or URL)
try:
    system_instruction = extract_text_from_source(source)
except ValueError as e:
    print(e)
    exit()



# Set the API key and configure the environment
GEMINI_API_KEY = "AIzaSyBrzQklT-FeUsROncuGbUR1e_ABSF-kiVE"
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
genai.configure(api_key=os.environ["GEMINI_API_KEY"])



# Create the model with the extracted system instruction
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 10000,  # 8192
    "response_mime_type": "text/plain",
}



model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction="Your name is AMMAR, your virtual assistant! and you are ready to assist with their queries under 150 words. If you do not know the answer to a question, suggest that they try rephrasing their prompt or give the user contact information so that we can contact. "+system_instruction  # Use extracted content here
)



@app.route('/')
def home():
    return render_template('app.html')  # Serve the HTML file

@app.route('/api/chatbot/GetResponse', methods=['POST'])
def get_response():
    app.logger.debug(f"Request headers: {request.headers}")
    app.logger.debug(f"Request body: {request.get_data(as_text=True)}")
    
    print('API IS WORKING')
    
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Invalid input'}), 400

        question = data['text']
        
        # Create a chat session
        chat_session = model.start_chat(history=[])

        # Send the input text to the chat session
        response = chat_session.send_message(question)

        # Extract the response text from the response object
        response_text = response.text  # Assuming `text` is the attribute holding the string

        # Remove the asterisks (*) from the response text
        
        clean_response = re.sub(r'^\*\s*|\*\s*$', '', response.text)
        clean_response = response_text.replace('*', '')
        clean_response = clean_response.replace('\ud83d\udc4b', '👋').replace('\ud83d\ude0a', '😎')

        return jsonify({'response': clean_response})

    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=25000, debug=True)  # Ensure it's accessible
