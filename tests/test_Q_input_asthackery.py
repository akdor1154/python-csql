from csql import Q, RenderedQuery, ParameterList as PL
import pytest

@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_Q_lambda():
	q = Q(lambda: "select 1")
	assert q.build() == RenderedQuery(
		sql="select 1",
		parameters=PL()
	)

@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_Q_lambda_dep():
	q1 = Q("select 1")
	q2 = Q(lambda: f"select 1 from {q1}")

	assert q1.queryParts == ['select 1']
	assert q2.queryParts == [
		'select 1 from ',
		q1
	]

def test_Q_deprecation():
	with pytest.warns(DeprecationWarning):
		q = Q(lambda: "select 1")