## Unreleased

## v0.3.1
  - make big queries format more nicely by using textwrap.dedent() and indent() - i haven't tested in a huge amount of cases and I probably can't
    make every possible query beautiful, but most things should look a bit better now.
## v0.3.0
  - allow parameters to be called as attributes as well as keys
    ( `p.myparam` vs `p['myparam']` ) (thanks @tomfunk)

  - Implement string parsing as an alternative to AST manipulation, so Q(lambda: f"select 1 from {q}") can now be written as Q(f"select 1 from {q}") (thanks @alexmojaki)
