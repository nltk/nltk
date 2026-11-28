import io
from pickle import UnpicklingError

from nltk.picklesec import allowlisted_pickle_load

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-c59x-vh6j-3w8v")
def probe_ghsa_c59x_vh6j_3w8v():
    """Verify allowlisted_pickle_load rejects numpy submodule-local file I/O

    callables when unpickling untrusted models (GHSA-c59x-vh6j-3w8v).
    """
    pickle_payload = b"\x80\x04" b"c" b"numpy.lib._npyio_impl\nrecfromtxt\n" b"."

    try:
        allowlisted_pickle_load(io.BytesIO(pickle_payload), allowed_modules=("numpy",))
        return VULNERABLE, "Submodule sink unpickled without restriction"
    except UnpicklingError as e:
        return FIXED, f"UnpicklingError raised for unauthorized submodule global: {e}"
