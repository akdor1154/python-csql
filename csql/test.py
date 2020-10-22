from .api import Q, Parameters

q1 = Q(lambda: f"""select val""")
p = Parameters(
	options=['1', '2', '3'],
	abc="def"
)
q2 = Q(lambda: f"""select a from {q1} where "val" in {p['options']} or abc = {p['abc']}""", p)
q3 = Q(lambda: f"""select a from {q1} where {'fdsa'} """)

p = Parameters(
	abc='abc'
)
q4 = Q(lambda: f"""select a from {q2} join {q3} where "abc" = {p['abc']} or "abc" = {p['abc']}""", p)

def __main__() -> None:
	from .renderer.query import BoringSQLRenderer

	r = BoringSQLRenderer.render(q4)
	print(r.sql)
	print(r.parameters)

__main__()