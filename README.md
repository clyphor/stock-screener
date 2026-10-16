# Stock Screener (US + ASX)

Ranks ~80 large US stocks and ~50 ASX stocks every weekday by blending:

| Part | Weight | What it uses |
|---|---|---|
| Model | 45% | LightGBM trained on price trends (momentum, RSI, moving averages, volatility, volume spikes, strength vs index) to predict next-month return vs the index |
| Fundamentals | 30% | Value (earnings & cash-flow yield vs sector), quality (ROE, margins, debt), growth |
| News | 15% | Sentiment of the company's headlines from the last 10 days |
| Peers | 10% | Sentiment of competitors' news in the same sector, plus policy/macro flags (tariffs, rates, elections…) |

Results appear on a phone-friendly page and in `results/latest.csv` (with daily history in `results/history/`).
The page also shows an honest backtest on the last 6 months the model never trained on.

## One-time setup (all doable from your phone's browser)

1. **Turn on the page:** repo **Settings → Pages → Source: Deploy from a branch → `main` / `docs`** → Save.
   Your page will be at `https://<your-username>.github.io/<repo-name>/`. Bookmark it.
2. **First run:** **Actions → Daily screener → Run workflow**. Takes ~5 minutes. After that it runs by itself at 9:30am Sydney, Tue–Sat.
3. **Optional, better news scoring:** add an Anthropic API key under **Settings → Secrets and variables → Actions → New secret**, named `ANTHROPIC_API_KEY`. Without it, a built-in finance word list is used.

## Changing things

Edit `config.py` (tickers, weights, filters), or just ask Claude to do it.
Test locally without internet: `python run.py --demo`.

## Limits

- Free Yahoo data: fine for daily use, occasionally flaky.
- Fundamentals and news are only today's snapshot, so the backtest only tests the price-based model.
- A positive backtest is not a promise. Not financial advice — paper-trade first.
