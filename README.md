# NPS Text Feedback Dashboard

Flask + vanilla HTML/JS single-page data app for Keboola.

## Repo structure

```
nps-app/
├── app.py                              # Flask backend
├── index.html                          # Frontend SPA
├── pyproject.toml                      # Python deps (uv)
└── keboola-config/
    ├── setup.sh                        # Runs uv sync on startup
    ├── nginx/sites/default.conf        # Reverse proxy 8888 → 5000
    └── supervisord/services/app.conf   # Starts gunicorn
```

## Keboola secrets required

Add these in `dataApp.secrets`:

| Key            | Value                                               |
|----------------|-----------------------------------------------------|
| `#KBC_TOKEN`   | Your Keboola Storage API token                      |
| `#KBC_URL`     | e.g. `https://connection.europe-west3.gcp.keboola.com` |

## Deployment

1. Push this repo to Git (branch: `main` or whatever you configure in Keboola)
2. In Keboola → Data Apps → create a new **Python/JS** data app
3. Point it at this Git repo + branch
4. Add the two secrets above
5. Deploy — the app will start and load the table automatically

## Endpoints

| Endpoint      | Method   | Description                      |
|---------------|----------|----------------------------------|
| `/`           | GET/POST | Serves `index.html`              |
| `/api/data`   | GET      | Returns full table as JSON array |
| `/api/reload` | POST     | Re-fetches table from Keboola    |

## Data table

`in.c-dataaps-test.nps_text_feedback` — 17 columns:

`response_id`, `project_id`, `source`, `internal_project`, `response_date`,
`cohort_date`, `score`, `nps_category`, `tariff`, `segment`, `month`,
`main_topic`, `topic_label`, `subtopic`, `sentiment_polarity`,
`theme_confidence`, `feedback_text`
