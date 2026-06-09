# How to Find Your ESPN Fantasy Baseball Credentials

You need four values to connect the agent to your ESPN league:

| Value | Where it comes from |
|---|---|
| `espn_s2` | Browser cookie after logging in |
| `SWID` | Browser cookie after logging in |
| `league_id` | Your league's URL |
| `team_id` | Your team's URL |

---

## Step 1 — Log in to ESPN Fantasy Baseball

Go to [fantasy.espn.com](https://fantasy.espn.com) and sign in with your ESPN account.

---

## Step 2 — Find Your League ID

Navigate to your fantasy baseball league. Look at the URL — it will look like:

```
https://fantasy.espn.com/baseball/league?leagueId=123456
```

Your `league_id` is the number after `leagueId=`. In this example it is **123456**.

---

## Step 3 — Find Your Team ID

Click on your team name to go to your team page. The URL will look like:

```
https://fantasy.espn.com/baseball/league?leagueId=123456&teamId=5
```

Your `team_id` is the number after `teamId=`. In this example it is **5**.

---

## Step 4 — Open Browser Developer Tools

While still on the ESPN Fantasy site (stay logged in), open your browser's developer tools:

| Browser | Shortcut |
|---|---|
| Chrome / Edge | `F12` or `Ctrl + Shift + I` |
| Firefox | `F12` or `Ctrl + Shift + I` |
| Safari | `Cmd + Option + I` (enable dev tools in Safari > Preferences > Advanced first) |

---

## Step 5 — Find the Cookies

### Chrome / Edge
1. Click the **Application** tab in the developer tools panel
2. In the left sidebar expand **Cookies** → click on `https://www.espn.com`
3. In the cookie list find `espn_s2` — copy the entire **Value** column (it is a long string)
4. Find `SWID` — copy the **Value** (it looks like `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`)

### Firefox
1. Click the **Storage** tab
2. Expand **Cookies** → click on `https://www.espn.com`
3. Find `espn_s2` and `SWID` and copy their values

### Safari
1. Click the **Storage** tab
2. Expand **Cookies** → click on `espn.com`
3. Find `espn_s2` and `SWID` and copy their values

> **Tip:** If you don't see `espn_s2` or `SWID` under `espn.com`, try `fantasy.espn.com` in the cookie list instead.

---

## Step 6 — Save Your Credentials

Run the setup script from the `fantasy-baseball-agent` directory:

```bash
python scripts/credentials/setup_credentials.py
```

When prompted, paste in the values you copied above. The script will save them to `config.ini` and confirm the connection to your league.

---

## Notes

- **These cookies expire periodically.** If the agent stops connecting, re-run the setup script with fresh cookie values from your browser.
- **Never commit `config.ini` to git.** It is already in `.gitignore`.
- The `espn_s2` value is a long URL-encoded string — copy the whole thing including any `%` characters.
