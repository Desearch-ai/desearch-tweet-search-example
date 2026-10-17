# Desearch Tweet Search Example

Made by Desearch | https://desearch.ai

A one-page web app to search public X posts with filters and export the results to CSV, built on the Desearch API X search endpoint (`GET https://api.desearch.ai/twitter`). Python standard library only: no framework, no X account, no X developer setup.

Latest live run: 2026-10-17, see [samples/live-run-2026-10-17.md](samples/live-run-2026-10-17.md).

## What it does

- One search box, plus an optional "any of" list that becomes `(a OR b)` in the query. Example: `desearch` with any of `bittensor, subnet` sends `desearch (bittensor OR subnet)`.
- Filters: sort (Latest or Top), count (1 to 100), language, min likes, min replies, min reposts, verified, blue verified, video, image, quote, date range.
- Results show time (UTC), text, likes, replies and a link in `x.com/i/status/<id>` form. Author handles are not shown, and `@mentions` in post text are shown as `@user`.
- "Download CSV" exports the same search.
- Input is checked before any API call (blank query, count out of range, bad language code, negative numbers, bad or reversed dates, future start date). A bad form returns HTTP 400 and costs nothing.
- Each result page says how many posts came back versus how many you asked for, and flags rows that fall outside your filters.

## Requirements

- Python 3.9 or newer.
- A Desearch API key from [console.desearch.ai](https://console.desearch.ai).

## Install

```bash
git clone https://github.com/Desearch-ai/desearch-tweet-search-example
cd desearch-tweet-search-example
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install -r requirements.txt   # only pytest, for the tests
```

## Set your API key

Use one of these:

```bash
export DESEARCH_API_KEY=your-api-key
# or keep the key in a file outside the repo
export DESEARCH_API_KEY_FILE=$HOME/.config/desearch/api_key
```

`DESEARCH_API_KEY` wins if both are set. The app sends the key in the `Authorization` header and never writes it to disk: when logging is on, saved calls show `Authorization: <redacted>`, and the client refuses to write any file that contains the key.

## Run

```bash
python3 app.py --port 8000
# open http://127.0.0.1:8000
```

Add `--log-dir runs/today` to save each API call (key redacted, with the billing headers) for debugging. `runs/` is in `.gitignore`.

You can also call the pages directly:

```bash
curl "http://127.0.0.1:8000/search?q=desearch&any=bittensor,subnet&sort=Latest&count=15"
curl -o tweets.csv "http://127.0.0.1:8000/search.csv?q=desearch&any=bittensor,subnet&count=15"
```

## Check the filters yourself

`tools/filter_check.py` runs one search per filter with the same client and counts the returned rows that break the filter.

```bash
python3 tools/filter_check.py --query bitcoin --count 10 --start-date 2026-10-14 --end-date 2026-10-15 --out runs/filter-check
```

Each check is one paid call. With `--count 10` the 9 checks cost $0.0135 in our 2026-10-17 run.

## Tests

```bash
python3 -m pytest -q
```

23 offline tests (no network, no key): validation, query building, handle masking, CSV and HTML escaping, the HTTP pages with a fake client, key loading, and the key-redaction guard.

## Files

- `app.py`: the HTTP server and the Desearch client.
- `core.py`: validation, query building, result rows, filter checks, CSV and HTML. No network.
- `tools/filter_check.py`: optional live filter check.
- `tests/`: offline tests.
- `samples/live-run-2026-10-17.md`: the live run behind the samples, with timestamps and costs.
- `samples/page.html`, `samples/tweets.csv`: one search page and its CSV from that run.
- `samples/filter-checks-2026-10-17.json`: filter check summary from that run.

## Cost

Billing is per post returned: $0.00015 per post in our runs, so 15 posts cost $0.00225 and 10 posts cost $0.0015 (2026-10-17). The cost of each call is in the `X-Desearch-Cost-Usd` response header, and the post count in `X-Desearch-Usage-Count`. The app prints both for each call.

## Known issues

Seen in our own runs, with dates:

- A search that matches nothing takes about 30 s and is still billed: a count of 5 was billed as 5 posts (2026-10-17), a count of 20 was billed as 10 posts (2026-10-16).
- `verified` returns blue-check accounts, and the `verified` field on those posts is false (10 of 10 on 2026-10-17). The app flags these rows as outside the filter. Use `blue_verified` if that is what you want.
- `sort=Top` with no date range can return old posts (a 2021 post in a Top search of 10 on 2026-10-17). Set a start date for recent top posts.
- `count=100` with `sort=Top` returned 48 posts, and Latest with 100 took about 28 s (2026-10-16).
- Post text sometimes comes back with `&amp;` instead of `&` (1 of 15 posts on 2026-10-17). The app decodes it once before display and CSV.
- The cost header can carry float noise, for example `0.0014999999999999998`. Round it before showing it to users.
- Dates are whole UTC days.

## License

MIT. See [LICENSE](LICENSE).
