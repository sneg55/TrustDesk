# Security

- Never commit .env, private keys, or API secrets
- All secrets via environment variables through core/config.py
- Validator wallet key MUST be separate from agent wallet key
- Kraken API key permissions: minimum required per use case
- IPFS evidence is public — never include private keys or raw API responses with secrets
- Use --validate flag on Kraken orders during development
- Paper trading by default (TRUSTDESK_MODE=paper)
