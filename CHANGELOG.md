## v0.9.0
  - Queries and Parameters are now immutable. This makes a bunch of stuff simpler for me and avoids a couple of bugs. There are
    possibly race conditions related to id() usage that are also now all gone, woohoo. This does mean parameter values must be hashable, but there's a check in there to turn any lists/seq etc into a tuple, and I'm not sure what else you'd run into frequently that would hit this.
  - Implement Extensions and Replacers system - this is considered internal for now but it's quite general purpose, you may
    be able to do some fun stuff with it. (everybody wants an ECS implementation in their SQL preprocessor, right?)
  - Implement caching using Extensions/Replacers
  - Refactor reparameterization to use Extensions/Replacers
## v0.8.0
  - add parameters.add()
  - fix for preview_pd
  - make parameterlist look like a list
## v0.7.0
  - implement Overrides system as a hook to supply your own weird renderers and stuff (e.g. i'm using it in another
    project to render as a UDF body, where params need to look like `:param`.)
## v0.6.0
  - implement reparameterization (so you can run your queries with different params to their original values)
## v0.5.0
  - implement Dialects for where we need to know about SQL dialects (param styles, limit method I think is all atm)
## v0.4.0
  - add .db() renderer `-> (sql, params)` to pass to dbapi like `execute(*.db())`
## v0.3.2
  - patch release to remove extraneous print
## v0.3.1
  - make big queries format more nicely by using textwrap.dedent() and indent() - i haven't tested in a huge amount of cases and I probably can't
    make every possible query beautiful, but most things should look a bit better now.
## v0.3.0
  - allow parameters to be called as attributes as well as keys
    ( `p.myparam` vs `p['myparam']` ) (thanks @tomfunk)

  - Implement string parsing as an alternative to AST manipulation, so Q(lambda: f"select 1 from {q}") can now be written as Q(f"select 1 from {q}") (thanks @alexmojaki)
