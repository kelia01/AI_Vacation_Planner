# tests/test_guardrails.py
from unittest.mock import patch, MagicMock

class TestMultimodalService:
    def test_detect_jpeg(self):
        from app.services.multimodal_service import _detect_media_type
        jpeg_bytes = b"\xff\xd8\xff" + b"\x00" * 10
        assert _detect_media_type(jpeg_bytes) == "image/jpeg"

    def test_detect_png(self):
        from app.services.multimodal_service import _detect_media_type
        png_bytes = b"\x89PNG" + b"\x00" * 10
        assert _detect_media_type(png_bytes) == "image/png"

    def test_detect_unknown_defaults_to_jpeg(self):
        from app.services.multimodal_service import _detect_media_type
        assert _detect_media_type(b"\x00\x00\x00\x00") == "image/jpeg"

    def test_tts_returns_bytes(self):
        from app.services.multimodal_service import text_to_speech
        with patch("app.services.multimodal_service.gTTS") as mock_gtts:
            mock_gtts.return_value.write_to_fp = lambda buf: buf.write(b"fake-mp3")
            result = text_to_speech("hello")
        assert isinstance(result, bytes) and len(result) > 0

    def test_tts_returns_none_on_error(self):
        from app.services.multimodal_service import text_to_speech
        with patch("app.services.multimodal_service.gTTS", side_effect=Exception("network error")):
            result = text_to_speech("hello")
        assert result is None

    def test_analyze_image_calls_claude(self):
        from app.services.multimodal_service import analyze_image
        mock_response = MagicMock()
        mock_response.content = "Eiffel Tower in Paris"
        with patch("app.services.multimodal_service.llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = analyze_image(b"\xff\xd8\xff\x00", content_type="image/jpeg")
        assert result == "Eiffel Tower in Paris"
