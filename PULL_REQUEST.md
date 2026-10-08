# Give the model the author's context

Authors often explain in the pull request description why a change looks the way it does, and the model never saw that. This passes the description into the request text, under a short heading, so the review can take the author's intent into account instead of flagging things the description already explains.

- `context/request.py`: the description is included after the instructions when a pull request is present
