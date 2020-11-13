## Unreleased

## v0.3.0
 - allow parameters to be called as attributes as well as keys
	( `p.myparam` vs `p['myparam']` ) (thanks @tomfunk)

 - Implement string parsing as an alternative to AST manipulation, so Q(lambda: f"select 1 from {q}") can now be written as Q(f"select 1 from {q}") (thanks @alexmojaki)
