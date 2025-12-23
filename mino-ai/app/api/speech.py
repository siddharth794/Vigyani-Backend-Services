from flask import Blueprint, request, jsonify
import os
import uuid
from app.services.speech_service import transcribe_audio
import tempfile

UPLOAD_DIR = tempfile.gettempdir()


speech_api = Blueprint("speech_api", __name__)



@speech_api.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    ext = os.path.splitext(audio_file.filename)[-1]
    temp_filename = f"{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)

    # Save file
    audio_file.save(temp_path)

    try:
        # Transcribe
        text = transcribe_audio(temp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Delete file after transcription
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify({"transcript": text})
