from flask import Flask, request, render_template, jsonify
from flask import send_from_directory
import shutil 

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('editor.html')  # Your HTML UI

@app.route('/reset_index', methods=['POST'])
def reset_index():
    try:
        shutil.copyfile('index_template.html', 'index.html')
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))
        
@app.route('/update_index', methods=['POST'])
def update_index():
    data = request.get_json()
    wrapper = data['wrapper']
    landing = data['landing']

    with open('index.html', 'w') as f:
        f.write(f"""
        <html>
        <body>
          <video src="{wrapper}" autoplay loop></video>
          <a href="{landing}">Go to Landing Page</a>
        </body>
        </html>
        """)

    return jsonify(success=True)


if __name__ == '__main__':
    app.run(debug=True)
