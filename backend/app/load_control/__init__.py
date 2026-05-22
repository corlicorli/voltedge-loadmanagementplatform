"""Load Control Context — the bounded context that owns load management.

Realizes the Load Management core subdomain: registration/updating of charging
sessions and load, evaluation against thresholds, activation of load rules and
regulation, and publication of domain events. It does NOT own billing, firmware
or partner settlement (those integrate via events across context boundaries).
"""
