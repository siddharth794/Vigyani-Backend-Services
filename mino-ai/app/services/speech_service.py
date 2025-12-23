from faster_whisper import WhisperModel

# Lazy load model - only load when first needed
_model = None

def get_model():
    """Lazy load faster-whisper model - CPU optimized, much smaller than openai-whisper"""
    global _model
    if _model is None:
        # Use "tiny" model for smallest size, or "base" for better accuracy
        # CPU device, no GPU needed
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model

def transcribe_audio(file_path: str, language: str = None) -> str:
    """
    Transcribes an audio file using faster-whisper (CPU-optimized, lightweight).
    
    :param file_path: Path to the audio file.
    :param language: Optional hint for language (e.g., 'en', 'es').
    :return: Transcribed text.
    """
    try:
        model = get_model()  # Lazy load model only when needed
        
        # Transcribe with faster-whisper API
        segments, info = model.transcribe(
            file_path,
            language=language,
            beam_size=5
        )
        
        # Combine all segments into full text
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text)
        
        return " ".join(text_parts).strip()

    except Exception as e:
        # Handle/log error as needed
        return f"❌ Error during transcription: {str(e)}"
