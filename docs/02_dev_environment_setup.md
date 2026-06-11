# Developer Environment Setup

## Prerequisites

Install the following tools before cloning any repository:

| Tool | Version | Install |
|------|---------|---------|
| Git | >= 2.40 | `brew install git` / [git-scm.com](https://git-scm.com) |
| Docker Desktop | >= 4.30 | [docker.com/products/docker-desktop](https://docker.com) |
| Node.js | 20 LTS | via `nvm install 20` |
| Python | 3.11 | via `pyenv install 3.11` |
| kubectl | >= 1.28 | `brew install kubectl` |
| Terraform | >= 1.7 | `brew install terraform` |
| AWS CLI | v2 | `brew install awscli` |

## One-Time Setup Steps

### 1. Clone the bootstrapper
```bash
git clone git@github.com:acme-corp/dev-bootstrap.git
cd dev-bootstrap
./setup.sh
```
This script installs all listed tools, configures git hooks, and sets up your SSH key for GitHub.

### 2. Configure AWS SSO
We use AWS SSO (Identity Center). Run:
```bash
aws configure sso
# SSO Start URL: https://acme.awsapps.com/start
# SSO Region: us-west-2
# Default region: us-west-2
# Default output format: json
```
Profile name must be `acme-dev`. The platform team will grant you the correct permission set — ping #infra-team if access doesn't appear within 24 hours of your start date.

### 3. Configure GitHub access
- Ensure your GitHub username is added to the `acme-corp` org. HR triggers this during onboarding.
- Add your SSH key: `cat ~/.ssh/id_ed25519.pub` → paste into GitHub Settings → SSH Keys.
- Set your git identity:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.name@acme.com"
```

### 4. Install pre-commit hooks
All repos use pre-commit hooks for linting and secrets detection:
```bash
pip install pre-commit
pre-commit install  # run inside each repo you clone
```

### 5. Set up local secrets
Copy `.env.example` to `.env` in each service repo. Never commit `.env` files. Secrets are managed in AWS Secrets Manager — ask your team lead for the path prefix for your squad.

## Running Services Locally

Most services run via Docker Compose:
```bash
docker compose up -d
```
Service ports are documented in each repo's README. The standard port mapping:
- API Gateway: `localhost:8080`
- Frontend: `localhost:3000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## IDE Recommendations

**VS Code** is the team standard. Install the recommended extensions by opening the repo in VS Code — it will prompt you to install `.vscode/extensions.json`.

Key extensions:
- ESLint, Prettier (JS/TS)
- Pylance, Ruff (Python)
- HashiCorp Terraform
- GitLens
- Docker

**JetBrains** IDEs are also supported. Reach out to #devex-team for license info.

## Troubleshooting

**Docker daemon not running:** Start Docker Desktop. On Linux, run `sudo systemctl start docker`.

**AWS SSO session expired:** Run `aws sso login --profile acme-dev`.

**Permission denied on GitHub:** Verify your SSH key is added both locally and on GitHub. Run `ssh -T git@github.com` to test.

**Port already in use:** Run `lsof -i :<port>` to find and kill the conflicting process.

For anything else, post in #devex-team — do not DM individuals.
