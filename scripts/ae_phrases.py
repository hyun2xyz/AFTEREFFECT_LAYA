"""AE scope recognition only; no model, app access or execution."""
import re
import unicodedata

APP_PREFIX = re.compile(r"^(?:애프터\s*이펙트|애프터\s*이펙츠|after[\s-]+effects|에펙|애펙)\s*", re.IGNORECASE)
LAUNCH_ONLY = re.compile(r"(?:켜줘|열어줘|실행해줘|열기|실행|켜|열어|open|launch|꺼줘|종료해줘|닫아줘|종료|quit|close)", re.IGNORECASE)
KOREAN_SCOPES = ("컴포지션", "컴프", "배경", "텍스트", "널", "3D 널", "선택 레이어", "현재 상태", "레이어", "키프레임")


def strip_app_prefix(text):
    return APP_PREFIX.sub("", text.strip(), count=1).strip()


def looks_like_ae(text):
    text=unicodedata.normalize("NFC", " ".join(text.split()))
    app=APP_PREFIX.match(text)
    if app:
        # Preserve the legacy CLI's explicit launch/quit operations, but never
        # give an AE editing request to its generic system-status fallback.
        return LAUNCH_ONLY.fullmatch(text[app.end():].strip()) is None
    if re.match(r"^(?:comp|composition)(?=\s|\d|$)",text,re.IGNORECASE):
        return True
    return any(text.startswith(prefix) for prefix in KOREAN_SCOPES)
