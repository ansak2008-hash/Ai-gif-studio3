# Security hardening

## API
- Production API endpoints require APP_API_KEY; health/readiness remain unauthenticated for probes.
- Request bodies are capped by APP_MAX_REQUEST_BYTES.
- Client-supplied request IDs are accepted only as bounded printable values; generated IDs are used otherwise.
- Security headers are added to every HTTP response.

## Media processing
- FFmpeg and ffprobe are invoked with argv lists, never shell command strings.
- Media processing disables proxy environment variables and uses bounded subprocess timeouts.
- Upload size, duration, and dimensions are checked before rendering.
- Artifacts are stored below per-job directories and filenames are validated.

## Telegram
- TELEGRAM_ALLOWED_USER_IDS can restrict bot access. An empty list means the bot accepts all Telegram users and should only be used intentionally.
- Bot credentials are environment configuration and must never be committed.

## Production baseline
- Run workers as an unprivileged user.
- Disable outbound network access for media workers where possible.
- Use PostgreSQL/Redis with authentication and TLS where supported by the deployment environment.
- Keep logs free of bot tokens, API keys, media contents, and full user-controlled payloads.
