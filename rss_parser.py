name: Update RSS Feed
on:
  schedule:
    - cron: "0 */6 * * *"  # Каждые 6 часов
  workflow_dispatch:  # Ручной запуск
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.PAT_TOKEN }}
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install feedparser requests beautifulsoup4 html2text playwright
          python -m pip show playwright
          python -m pip list
          # Устанавливаем браузеры для Playwright
          playwright install --with-deps chromium
      - name: Run script
        run: python rss_parser.py
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git commit -m "Updated RSS feed" || echo "No changes"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.PAT_TOKEN }}
