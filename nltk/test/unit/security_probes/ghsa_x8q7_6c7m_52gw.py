from nltk.internals import java

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-x8q7-6c7m-52gw")
def probe_ghsa_x8q7_6c7m_52gw():
    """Verify nltk.internals.java rejects launcher options like -jar or @argfile

    when supplied in the cmd sequence (GHSA-x8q7-6c7m-52gw).
    """
    # Probe 1: -jar option in cmd list
    try:
        java(cmd=["-jar", "/path/to/untrusted.jar"], classpath=None)
        return VULNERABLE, "Launcher flag -jar permitted in cmd sequence"
    except ValueError:
        pass
    except (OSError, RuntimeError, FileNotFoundError):
        return VULNERABLE, "Flag -jar reached subprocess execution without validation"

    # Probe 2: @argfile syntax in cmd list
    try:
        java(cmd=["org.example.Main", "@/path/to/argfile"], classpath=None)
        return VULNERABLE, "Launcher option @argfile permitted in cmd sequence"
    except ValueError:
        pass
    except (OSError, RuntimeError, FileNotFoundError):
        return (
            VULNERABLE,
            "Option @argfile reached subprocess execution without validation",
        )

    return FIXED, "Disallowed java launcher options successfully blocked"
