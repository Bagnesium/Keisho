Unicode frames corrupt the following message. Fix the supplied repository so all public and hidden behavioral tests pass. Preserve the API and the documented input contracts. Edit source modules only; test fixtures are immutable. Use the provided tools; no network or external files.

Frames are ASCII decimal BYTE length, then colon, then exactly that many UTF-8 bytes. Colons may appear in a body. Multiple frames and arbitrary input chunk boundaries must preserve every message.
