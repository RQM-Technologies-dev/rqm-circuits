# Public circuit and compiler boundaries

Schema 0.2 carries public circuit instructions. Internal compiler descriptors
such as `su4q` are deliberately not standard gates and must not cross API,
storage, or Studio circuit boundaries.

Call `validate_public_circuit` at external boundaries. Backend compilation may
use richer internal descriptors after the public circuit has been validated.
