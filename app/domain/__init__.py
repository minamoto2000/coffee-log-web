"""Pure domain logic: no database, no HTTP, no Pydantic.

Everything here is a deterministic function of its arguments so that the
rules in 01b (step validation, condition diff, EY, statistics, warnings)
can be unit-tested in isolation.
"""
