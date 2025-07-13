from flask import Flask, request, render_template, jsonify, send_from_directory
import shutil
import os
import subprocess
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('editor.html')

@app.route('/reset_index', methods=['POST'])
def reset_index():
    try:
        shutil.copyfile('index_template.html', '/tmp/index.html')
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
    qr_path = 'static/themeqr_demo_qr.png'
    
    # Output filename with unique ID
    output_filename = f"themeqr_build_{uuid.uuid4().hex[:8]}.mp4"
    output_path = f"/tmp/{output_filename}"

    try:
        # Call generate_qr_video_wrapper.py
        subprocess.run([
            'python3', 'generate_qr_video_wrapper.py',
            '--wrapper', wrapper,
            '--qr', qr_path,
            '--landing', landing,
            '--output', output_path
        ], check=True)

        # Update index.html from template and inject new video path
        with open('index_template.html', 'r') as template:
            html = template.read()

        # Replace placeholder src in template with new path
        new_html = html.replace(
            'src="https://res.cloudinary.com/themeqr-test/video/upload/v1752014993/themeqr/wrappers/obsg01o6dfzl6du5bsaa.mp4"',
            f'src="/static/{output_filename}"'
        )

        with open('/tmp/index.html', 'w') as f:
            f.write(new_html)

        # Optionally copy video to static folder if needed (for previewing)
        shutil.copyfile(output_path, f'static/{output_filename}')

        return jsonify(success=True, video_url=f"/static/{output_filename}")

    except Exception as e:
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



