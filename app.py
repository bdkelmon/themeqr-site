from flask import Flask, request, render_template, jsonify

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('editor.html')  # Your HTML UI

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
