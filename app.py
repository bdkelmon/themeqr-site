from flask import Flask, request, render_template, jsonify, send_from_directory
import shutil
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('editor.html')  # Loads the Deck Builder UI

@app.route('/reset_index', methods=['POST'])
def reset_index():
    try:
        shutil.copyfile('index_template.html', '/tmp/index.html')  # ⬅ fix path
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/index.html')
def serve_updated_index():
    return send_from_directory('/tmp', 'index.html')

@app.route('/update_index', methods=['POST'])
def update_index():
    data = request.get_json()
    wrapper = data['wrapper']
    landing = data['landing']
    try:
        with open('/tmp/index.html', 'w') as f:  # ⬅ write to /tmp
            f.write(f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>ThemeQR Preview</title>
  </head>
  <body>
    <video src="{wrapper}" autoplay loop controls style="max-width:100%; height:auto;"></video>
    <br>
    <a href="{landing}" target="_blank">Go to Landing Page</a>
  </body>
</html>
""")
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


