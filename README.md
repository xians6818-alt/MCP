# Content Engine Pro

AI short-video content production workbench for product and brand seeding workflows.

## Features

- Generate three script directions from a short product brief.
- Score scripts with a 7-dimension rubric.
- Rewrite scripts based on score weaknesses.
- Generate phone-friendly storyboard and shooting guidance.
- Predict playback ranges and record retrospective calibration data.
- Export call sheets and history records to Excel.
- Store evaluation, prediction, and calibration records in Supabase.

## Setup

```bash
pip install -r requirements.txt
streamlit run web_ui.py
```

## Environment

Copy `.env.example` to `.env` for local development, or configure the same keys in Streamlit Cloud secrets.

```env
MOONSHOT_API_KEY=your_moonshot_api_key_here
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=moonshot-v1-8k
DASHSCOPE_API_KEY=your_dashscope_api_key_here
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_KEY=your_supabase_anon_or_service_role_key_here
```

## CLI

```bash
python -m cli.main status
python -m cli.main score scripts/test.md
python -m cli.main predict scripts/test.md
python -m cli.main export-call-sheet scripts/test.md
python -m cli.main export-history
```
