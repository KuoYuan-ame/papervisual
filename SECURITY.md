# Security Policy

## Reporting

Please do not report security vulnerabilities in public issues. Contact the repository maintainers through GitHub's private vulnerability reporting feature. Include the affected version, impact, and a minimal reproduction when possible.

## Scope

`init`, `suggest`, `validate`, `render`, `batch`, and `qa` run locally. The optional `draft` command sends selected manuscript text to the explicitly configured model endpoint; see [the privacy notes](docs/privacy.md). The program does not execute brief contents. Treat third-party JSON and SVG files as untrusted input and inspect SVG before embedding it in a website.
