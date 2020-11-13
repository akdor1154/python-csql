import csql
import pytest

def qWithStrParsing(queryLambda, parameters=None):
	querySql = queryLambda()
	assert isinstance(querySql, str)
	return csql.Q(querySql, parameters)

@pytest.fixture(scope='package', params=['asthackery', 'strparsing'])
def Q(request):
	method = request.param
	if method == 'asthackery':
		return csql.Q
	elif method == 'strparsing':
		return qWithStrParsing