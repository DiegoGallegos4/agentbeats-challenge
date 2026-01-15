# GitHub Actions Deployment

This repo includes a GitHub Actions workflow that builds and publishes Docker images to GHCR for the green and purple agents.

## Workflow
- File: `.github/workflows/docker-publish.yml`
- Trigger: push to `main` or manual `workflow_dispatch`
- Images:
  - `ghcr.io/diegogallegos4/agentbeats-challenge:latest` (green)
  - `ghcr.io/diegogallegos4/agentbeats-challenge:green`
  - `ghcr.io/diegogallegos4/agentbeats-challenge:purple`

## Required Secrets
No extra secrets are required for GHCR. The workflow uses the built-in `GITHUB_TOKEN`.

## Notes
- The green image is tagged as `latest` and `green`.
- The purple image is tagged as `purple`.
- Update `IMAGE_REPO` in the workflow if you need a different GHCR repo name.
