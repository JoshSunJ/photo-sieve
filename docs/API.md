# Local engine API · version 1

Base address: `http://<Mac-local-host>:8765`.
Every route requires `Authorization: Bearer <pairing-token>`.
Tokens rotate each process start and are not written to a file.

## GET /v1/health

Only ready after the model has loaded:

```json
{"api_version": 1, "status": "ready", "storage": "memory-only"}
```

## POST /v1/score

Content type: `application/json`. Body limit: 3 MiB. Decoded image limit: 2 MiB.
Maximum decoded dimensions: 4096 per side; send a 512-pixel JPEG thumbnail.
Descriptions: 1–12 nonempty include descriptions; 0–12 keep descriptions;
at most 240 characters each. Empty lines are removed and descriptions deduplicated.

```json
{
  "api_version": 1,
  "image_base64": "<base64 JPEG bytes>",
  "prompts": ["a bowl of ramen", "a plate of sushi"],
  "exclude_prompts": ["a screenshot of a restaurant menu"],
  "threshold": 0.25,
  "margin": 0.02
}
```

Illustrative response, not a measured example:

```json
{
  "api_version": 1,
  "score": 0.34,
  "best_prompt": "a bowl of ramen",
  "keep_score": 0.21,
  "candidate": true,
  "scores": {"a bowl of ramen": 0.34, "a plate of sushi": 0.19},
  "model": "ViT-B-32/laion2b_s34b_b79k"
}
```

The response contains no deletion instruction. `candidate` is a suggestion for
review. Selection and deletion are separate client capabilities.

| Status | Meaning | Client behavior |
| --- | --- | --- |
| 200 | Scored or healthy | Decode and validate API version |
| 400 | Invalid JSON, image, descriptions, or tuning | Show error; correct input |
| 401 | Missing/wrong pairing token | Re-pair |
| 404 | Unsupported route | Check app/engine versions |
| 408 | Request read timed out | Check connection |
| 413 | Body outside limit | Send a smaller thumbnail |
| 415 | Wrong content type | Use JSON |
| 429 | Two scoring requests already admitted | Retry later; prototype stops scan |
| 500 | Inference/internal failure | Check engine installation/device |

There is deliberately **no `/delete` API**, CORS support, or file upload storage.
The server doesn't require or receive PhotoKit asset identifiers. Images and
prompts are not printed in request logs. The standard library HTTP server is a
small trusted-LAN prototype, not an Internet-facing production server.

Sequential iPhone requests are intentional. Scoring is read-only and can be
retried; deletion should never be blindly retried after an ambiguous outcome.
The app leaves explicit restart/re-pairing to the user rather than hiding errors
in an unbounded retry loop.
