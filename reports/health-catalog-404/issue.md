<!-- report_id: 2fa26d64-16c9-59f7-b216-97957bccfd22 -->
<!-- machine_contract: reviewed evidence -> public report; publication does not establish reproduction or root cause. -->

### What version of the Codex App are you using (From “About Codex” dialog)?

The original running version was not recorded. A follow-up inspection of installed application metadata on 2026-08-31 found:

- `ChatGPT.app`: `26.825.51511` (build `7377`).
- `Codex.app`: `26.715.31925` (build `5551`).

These are installed versions, not a verified identification of the application that produced the error.

### What subscription do you have?

Not recorded in the supplied evidence.

### What platform is your computer?

macOS `27.0` (build `26A5416b`). Follow-up `uname -mprs` output: `Darwin 27.0.0 arm64 arm`.

### What issue are you seeing?

The desktop plugin catalog offers **Health** with an **Install** action, but the supplied screenshots show the Health detail view ending at **Failed to load plugin**:

```text
read remote plugin details: remote plugin catalog request to https://chatgpt.com/backend-api/plugins/plugin_connector_1p_e569f8b8dfd08191903c9bd2cd7da9ac failed with status 404 Not Found: {"detail":"Plugin not found"}
```

The application is labeled ChatGPT in the screenshots. I am filing here because the [official desktop troubleshooting guide](https://learn.chatgpt.com/docs/reference/troubleshooting) directs desktop reports to this repository.

### What steps can reproduce the bug?

Reported sequence, reconstructed from the conversation and screenshots reviewed on 2026-08-31:

1. Open the desktop application's **Plugins** catalog.
2. Find **Health** and select **Install**.
3. Attempt to continue through its connection/detail flow.
4. Observe **Failed to load plugin** and the error above.

No fresh reproduction was performed. The exact intermediate navigation, original running version, and account eligibility remain unverified.

### What is the expected behavior?

The catalog should reflect availability in the current application and account. If Health is unavailable, hide or disable the action, or explain the limitation before sending the user into a generic 404.

The [Health documentation](https://help.openai.com/en/articles/20001036-health-in-chatgpt) says Health is unsupported in Codex. This report concerns catalog availability and error handling; it does not assume Health should work in Codex.

### Additional information

- A separate browser inspection loaded the same Health plugin's web detail page, version `0.1.4`. Its launch link identified it as `connector_openai_olympic`. This confirms the identifier mapping only; it does not establish desktop availability or successful connection.
- I searched this tracker for both identifiers and related catalog/404 reports. No matching report was identified in the results reviewed; the search was limited.
- No health records, private conversation links, screenshots, or raw logs are included. Root cause remains unconfirmed.
