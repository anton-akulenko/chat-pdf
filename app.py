from flask import Flask, render_template, request, redirect, url_for, flash
from langchain_utils import initialize_chat_conversation
from search_indexing import download_and_index_pdf
from werkzeug.utils import secure_filename
from constants import search_number_messages
import os
import re

import logging

# You can print the contents of app.config
# print(app.config)

# Alternatively, you can log the contents
logging.basicConfig(level=logging.DEBUG)  # Set the logging level to DEBUG
logger = logging.getLogger(__name__)

# # Log the contents of app.config
# logger.debug("Contents of app.config: %s", app.config)



app = Flask(__name__)


# Директорія для зберігання завантажених файлів
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Шлях до теки з шаблонами
TEMPLATE_FOLDER = 'templates'

# Встановлюємо теку з шаблонами
app.config['TEMPLATE_FOLDER'] = TEMPLATE_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if 'faiss_index' not in app.config:
    app.config['faiss_index'] = {
        'indexed_urls': [],
        'index': None
    }

# Initialize conversation memory used by Langchain
if 'conversation_memory' not in app.config:
    app.config['conversation_memory'] = None

# Initialize chat history used by StreamLit (for display purposes)
if "messages" not in app.config:
    app.config["messages"] = []

# Store the URLs added by the user in the UI
if 'urls' not in app.config:
    app.config["urls"] = []





@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    logger.debug("Contents of app.config in the route: %s", app.config)
    return render_template('index.html', files=files)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Отримуємо список завантажених файлів
    uploaded_files = request.files.getlist("file[]")
    urls = []

    # Зберігаємо файли та отримуємо URL
    for file in uploaded_files:
        if file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            urls.append(filepath)
            print(urls)
            flash(f"Файл '{filename}' був успішно завантажений.", 'success')

    # Після того, як ми маємо URL, завантажуємо та індексуємо PDF
    faiss_index = download_and_index_pdf(urls)
    app.config['faiss_index'] = faiss_index
    return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])

def search():
    if request.method == 'POST':
        query = request.form.get('query')
    else:
        query = request.args.get('query')

    if query:
        logger.debug("Contents of app.config,content in the route: %s", app.config)

        app.config["messages"].append({"role": "user", "content": query})

        # Check if FAISS index already exists, or if it needs to be created as it includes new URLs
        faiss_index = app.config.get('faiss_index')

        # Initialize conversation memory used by Langchain
        conversation_memory = app.config.get('conversation_memory')

        # Search PDF snippets using the last few user messages
        user_messages_history = [message['content'] for message in app.config.get('messages')[-search_number_messages:] if message['role'] == 'user']
        user_messages_history = '\n'.join(user_messages_history)

        response = ""

        if not faiss_index:
            response = "FAISS index not found. Please upload PDFs first."
        else:
            with app.app_context():
                if not conversation_memory:
                    conversation = initialize_chat_conversation(faiss_index)
                    app.config['conversation_memory'] = conversation
                    conversation_memory = conversation
                else:
                    conversation = app.config['conversation_memory']

                # with st.spinner('Quer'):ying OpenAI GPT...
                response = conversation_memory.predict(input=query, user_messages_history=user_messages_history)
        print("\n\n" + response + "\n\n")

        snippet_memory = conversation.memory.memories[1]
        for page_number, snippet in zip(snippet_memory.pages, snippet_memory.snippets):
            print(f'Snippet from page {page_number + 1}')
                # Remove the <START> and <END> tags from the snippets before displaying them
            snippet = re.sub("<START_SNIPPET_PAGE_\d+>", '', snippet)
            snippet = re.sub("<END_SNIPPET_PAGE_\d+>", '', snippet)
            print(snippet)


        # Add assistant response to chat history
        messages = app.config.get('messages', [])
        messages.append({"role": "user", "content": query})

        app.config["messages"].append({"role": "assistant", "content": response})

        messages.append({"role": "assistant", "content": response})
        print(messages)
        app.config['messages'] = messages

    # return redirect(url_for('index'))
    return render_template('results.html')

if __name__ == '__main__':
    app.run(debug=True)
