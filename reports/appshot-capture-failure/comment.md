**Additional Chrome observation on desktop build 7377**

Adding diagnostic evidence from a newer build. The capture-start error matches this report, but the failing target here is Chrome rather than Slack; a shared root cause is not established.

**Environment**

- ChatGPT/Codex desktop: `26.825.51511` (build `7377`), bundle identifier `com.openai.codex`.
- Installed Computer Use helper: `26.828.1000919` (build `1000919`).
- macOS `27.0` (`26A5416b`), `Darwin 27.0.0 arm64 arm`.
- Installed Chrome: `152.0.7977.64`, bundle identifier `com.google.Chrome`.

Versions were read from installed application metadata, not the About dialog. Failure stacks point to `ChatGPT.app`; the loaded helper version was not independently checked. Subscription was not recorded.

**Observed behavior and comparison**

During user-driven Appshot attempts on 2026-08-31, pressing both Command keys produced `Unable to attach appshot`. Desktop records between `15:47:00Z` and `16:10:00Z` contain:

| Target | Settled captures | Image and accessibility text |
| --- | --- | --- |
| Chrome | 10 failures | Both absent |
| Finder, Calendar | 2 successes each | Both present |
| Notes, Reminders, App Store, Brave, Safari | 1 success each | Both present |
| Discord | 2 successes | Both present |
| Visual Studio Code, Spotify, Notion, Preview, Terminal, UTM | 1 success each | Both present |
| System Settings, Zed | 1 success each | Both present |

Appshot images and some accessibility data from all 16 successful applications also arrived in the conversation. Spotify and Zed provided minimal accessibility output; presence does not establish complete text capture. These counts describe this observation window, not a general failure rate.

One failed request selected `com.google.Chrome` at `15:55:53.374Z`, sent capture-start at `.381Z`, and failed at `.549Z`:

```text
Codex Computer Use Apple Event error -10005: noWindowsAvailable
failureReason=start_request_failed:computer_use:-10005
hadAxText=false
hadScreenshot=false
status=failed
```

The user reports failures when trying both standalone Chrome and ChatGPT's embedded browser. All ten reviewed failed requests name Chrome, so a separate embedded-browser failure path is not independently established. Window visibility and permissions were not independently verified for each attempt.

**Separate follow-up: capturing Codex itself**

The user also reports an error when trying to capture the Codex app itself. Between `16:20:39Z` and `16:20:48Z`, five hotkey attempts logged `Appshot shortcut had no target`, without creating a capture request. These records do not identify the target app, so their association with Codex itself is user-reported. This stops earlier than Chrome's capture-start failure; these five attempts are excluded from the table above. Whether self-capture is supported or intentionally excluded remains unverified.

Expected: attach the frontmost window image and available text, as described in the [Appshots documentation](https://learn.chatgpt.com/docs/appshots). The successful comparisons narrow the failure, but do not rule out a permission or window-selection problem. No permission reset or application restart was performed during this investigation. Raw logs and attachments are omitted to protect private content.

Could you advise whether this belongs to the same window-selection issue or should be tracked separately? Thank you.

<!-- report_id: 97c0c633-d01f-5023-9868-f2939ac39ebd; machine_contract: reviewed -> published -> verified; publication does not confirm root cause. -->
