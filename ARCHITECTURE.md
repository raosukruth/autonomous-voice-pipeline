# Architecture

This project uses a real time voice pipeline to run phone conversations with the
PGAI's (Pretty Good AI) test line. Twilio handles outbound calls and audio streaming through media
streams. A public ngrok URL exposes the local WebSocket server so that Twilio can
connect to the bot.

Incoming mulaw audio is sent to Deepgram STT for transcription. The transcript is
passed to an OpenAI-powered patient agent, which generates the next patient reply.
That reply is converted to mulaw audio with Deepgram TTS and streamed back to the
call through Twilio.

Each call is recorded with mixed inbound and outbound audio and saved as MP3,
along with timestamped transcripts. After runs complete, transcript content is
analyzed to generate bug reports and round-level quality summaries.
