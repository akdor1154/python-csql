from csql import Q, RenderedQuery, Parameters, ParameterList as PL
from csql.dialect import SQLDialect, ParamStyle
import pytest

def test_paramlist_list_eq():
	pl = PL(1,2,3)
	assert pl == [1, 2, 3]


def test_paramlist_eq():
	pl = PL(1,2,3)
	assert pl == PL(1, 2, 3)


def test_paramlist_is_list():
	pl = PL(1,2,3)
	assert isinstance(pl, list)

def test_paramlist_iter():
	pl = PL(1,2,3)
	assert list(pl) == [1, 2, 3]

def test_paramlist_getitem():
	pl = PL(1,2,3)
	assert pl[0] == 1
	assert pl[1] == 2
	assert pl[2] == 3

def test_paramlist_len():
	pl = PL(1,2,3)
	assert len(pl) == 3