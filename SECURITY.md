# Security

## How Scribr stores your API keys

Scribr keeps your settings, including your Groq and OpenAI API keys, in a plain
JSON file on your own Mac:

```
~/Library/Application Support/Scribr/settings.json
```

This file never leaves your machine and is not part of this repository. It is
listed in `.gitignore`, so it cannot be committed by accident. Keys are sent
only to the provider you configured them for (Groq or OpenAI) when transcribing
or formatting your audio.

Because the file is stored in plain text, treat your Mac user account as the
security boundary. If you share or sell the machine, remove the file first.

## Logs

Scribr writes logs to `~/Library/Logs/Scribr/scribr.log`. By default it logs at
INFO level and does not write your transcript text. Set `SCRIBR_DEBUG=1` to
enable verbose DEBUG logging while troubleshooting, which may include short
snippets of transcribed text. Turn it off again afterwards.

## Reporting a vulnerability

Please do not open a public issue for security problems. Email the maintainer
directly and allow reasonable time for a fix before any public disclosure.
