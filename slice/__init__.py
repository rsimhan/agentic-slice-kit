"""
The spine.

This package is deliberately NOT a library you install. It is ~1,100 lines you
are expected to read, understand, and edit. Every architectural principle the
kit teaches lives in here, and the whole point is that it fits in your head.

    records.py   what a run is made of          (stdlib)
    store.py     durable append-only state      (stdlib)
    budget.py    the fences                     (stdlib)
    llm.py       the one place model calls happen
    retrieve.py  chunk / embed / search
    runner.py    the state machine
    callback.py  suspend, resume, time out
"""
__version__ = "0.1.0"
