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

    try:
        qr_path = os.path.join('static', 'themeqr_demo_qr.png')  # Output QR path
        output_video_path = '/tmp/generated_video.mp4'  # Final video with QR

        # === Run the external QR+video generator script ===
        subprocess.run([
            'python3', 'generate_qr_video_wrapper.py',
            '--wrapper', wrapper,
            '--qr', qr_path,
            '--landing', landing,
            '--output', output_video_path
        ], check=True)

        # === Update index.html with new video source ===
        new_index_html = f"""
        <html>
        <body>
          <section class="video-wrapper">
            <h2>📽️ See It In Action</h2>
            <video autoplay loop muted playsinline width="100%">
              <source src="/tmp/generated_video.mp4" type="video/mp4">
              Your browser does not support the video tag.
            </video>
          </section>
        </body>
        </html>
        """

        with open('/tmp/index.html', 'w') as f:
            f.write(new_index_html)

        return jsonify(success=True)

    except subprocess.CalledProcessError as e:
        return jsonify(success=False, error=f"Video generation failed: {e}")
    except Exception as e:
        return jsonify(success=False, error=str(e))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



