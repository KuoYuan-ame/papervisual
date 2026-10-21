# Privacy and model use

All core commands (`init`, `suggest`, `validate`, `render`, `batch`, `qa`) run locally and make no network requests.

`draft` is the only network feature. It sends the selected UTF-8 text to the URL supplied by `--base-url` (HTTPS required, except localhost), along with a prompt and model name. The API key is read from `PAPERFIG_API_KEY`. The program does not log the text or key, but endpoint operators may process or retain requests under their own policies. Do not submit confidential, personal, peer-review, or unpublished content unless you have authorization and have assessed the provider's terms.

The program does not save a copy of the submitted manuscript excerpt or log the API key. Network and provider-side records may still exist according to the chosen service's policies. The model response is untrusted input: it is size-limited, parsed as JSON, validated against supported fields, and marked for author review before rendering. Do not treat source snippets or model-created explanations as independently verified evidence.
