# Google Form answer drafts

| Field | Draft |
|---|---|
| Name | Damien (XAVORIAN) |
| Email | [DAMIEN_EMAIL] |
| Agent name | BlindSpot |
| Description | BlindSpot tests an inventory classifier against labels I supply, remembers which camera conditions break it, and chooses the next experiment. It saves the photo pairs, predictions and reason for each action, including when to ask for a retake. |
| Connectors | Pinecone through the Sprites gateway for failure signatures. Optional Box gateway adapter for labelled image intake and report export. Current evidence verifies LOCAL/MOCK and simulated gateway responses. Replace this status only after the corresponding live checks pass. |
| Code link | [PUBLIC_CODE_URL] |
| Demo link | [PUBLIC_DEMO_URL] |
| Social post link | [PUBLISHED_POST_URL] |
| Notes for judges | Built November 25 during Hacksgiving week. The local sample replay shows a retrieved low-light failure changing test order, a preserved low-light prediction, and a JPEG-induced violin prediction at 93.84%. The owner can substitute personally labelled photos. The sample corpus is curated, and the agent uses a bounded deterministic policy and local CPU inference. Sprite deployment and authenticated connector proof are pending. |

These answers are drafts. The event requires a running Sprite and a connector. Set the links and update verification status after those requirements are met. [Event rules](https://fly.io/hacksgiving/)
