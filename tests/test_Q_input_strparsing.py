from csql import Q, RenderedQuery

def test_Q_str():
	q = Q("select 1")
	assert q.build() == RenderedQuery(
		sql="select 1",
		parameters=[]
	)

def test_Q_dep():
	q1 = Q("select 1")
	q2 = Q(f"select 1 from {q1}")

	assert q1.queryParts == ['select 1']
	assert q2.queryParts == [
		'select 1 from ',
		q1
	]


def test_Q_single():
	q1 = Q("select 1")
	q2 = Q(f"{q1}")

	assert q1.queryParts == ['select 1']
	assert q2.queryParts == [
		q1
	]


def test_Q_adjacent():
	q1 = Q("select 1")
	q2 = Q(f"{q1}{q1}")

	assert q1.queryParts == ['select 1']
	assert q2.queryParts == [
		q1, q1
	]


def test_Q_suffix():
	q1 = Q("select 1")
	q2 = Q(f"select from {q1} where blah")

	assert q1.queryParts == ['select 1']
	assert q2.queryParts == [
		'select from ',
		q1,
		' where blah'
	]
