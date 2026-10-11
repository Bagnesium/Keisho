Reservation replacement leaves phantom inventory holds. Fix the supplied repository so all public and hidden behavioral tests pass. Preserve the API and the documented input contracts. Edit source modules only; test fixtures are immutable. Use the provided tools; no network or external files.

A reserve for an existing ID REPLACES its units. Release removes that ID once. Unknown releases are no-ops. Event order is significant. Availability is capacity minus current active units.
