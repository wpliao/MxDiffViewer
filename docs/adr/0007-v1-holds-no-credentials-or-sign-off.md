# v1 holds no credentials and records no sign-off

v1 works only on a Git repo the user has already cloned, using their existing Git setup. It creates its own worktrees in a short-path cache folder, because Mendix paths otherwise exceed Windows' path limit. It never stores a Team Server PAT or other token.

The Release report informs the Approver's decision but doesn't record it. Sign-off stays in the team's existing process, and a stable report hash lets a pipeline attach the report as evidence.

Cloning from a URL and recording sign-off both need identity and secure storage, which only make sense once a hosted team version exists. Until then, storing secrets is a responsibility we don't take on.
