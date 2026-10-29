from datetime import date
from typing import Any

import pytest

from csql import Parameters, Q, RenderedQuery
from csql.dialect import ParamStyle, SQLDialect


def test_parameters():
	p = Parameters(abc="abc")
	q = Q(f"select 1 where abc = {p['abc']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1", parameters=("abc",), parameter_names=("abc",)
	)


def test_parameters_list():
	p = Parameters(abc="abc", list=[1, 2, 3])
	q = Q(f"select 1 where abc = {p['abc']} or def in {p['list']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1 or def in ( :2,:3,:4 )",
		parameters=("abc", 1, 2, 3),
		parameter_names=("abc", None, None, None),
	)


def test_parameters_reuse():
	p = Parameters(list=[1, 2, 3])
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = ( :1,:2,:3 ) or def in ( :1,:2,:3 )",
		parameters=(1, 2, 3),
		parameter_names=(None, None, None),
	)


def test_parameters_getattr():
	p = Parameters(abc="abc")
	q = Q(f"select 1 where abc = {p.abc}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1", parameters=("abc",), parameter_names=("abc",)
	)


def test_parameters_dialect_dollar_numeric():
	p = Parameters(abc="abc")
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric_dollar)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = $1", parameters=("abc",), parameter_names=("abc",)
	)


def test_parameters_dialect_qmark():
	p = Parameters(abc="abc")
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = ?", parameters=("abc",), parameter_names=("abc",)
	)


def test_parameters_dialect_qmark_reuse():
	p = Parameters(list=[1, 2, 3])
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}")

	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = ( ?,?,? ) or def in ( ?,?,? )",
		parameters=(1, 2, 3, 1, 2, 3),
		parameter_names=(None, None, None, None, None, None),
	)


def test_parameters_dialect_clickhouse():
	p = Parameters(abc="abc")
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.clickhouse)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = {abc:String}",
		parameters=("abc",),
		parameter_names=("abc",),
	)


def test_parameters_dialect_clickhouse_list():
	p = Parameters(ids=["a", "b"])
	q = Q(f"select 1 where id in {p['ids']:Array(String)}")
	dialect = SQLDialect(paramstyle=ParamStyle.clickhouse)
	built = q.build(dialect=dialect)
	assert built.sql == "select 1 where id in {ids:Array(String)}"
	assert built.ch["parameters"] == {"ids": ["a", "b"]}


@pytest.mark.parametrize(
	("value", "fmt"),
	[
		(["a", "b"], "Array(String)"),
		([1, 2], "Array(Int64)"),
		([date(2024, 1, 1)], "Array(Date)"),
		([1, "a"], ""),
		([], ""),
	],
)
def test_parameters_dialect_clickhouse_list_inferred_type(value: list[Any], fmt: str):
	p = Parameters(ids=value)
	q = Q(f"select 1 where id in {p['ids']}")
	dialect = SQLDialect(paramstyle=ParamStyle.clickhouse)
	built = q.build(dialect=dialect)
	assert built.sql == f"select 1 where id in {{ids:{fmt}}}"
	assert built.ch["parameters"] == {"ids": value}


def test_parameters_add_simple():
	p = Parameters()

	q = Q(f"select {p.add(1)}, {p.add(2)}")

	assert q.build() == RenderedQuery(
		sql="select :1, :2", parameters=(1, 2), parameter_names=(None, None)
	)


def test_parameters_add_to_existing():
	p = Parameters(existing="abc")

	q = Q(f"select {p.add(1)}, {p.add(2)} where abc = {p['existing']}")

	assert q.build() == RenderedQuery(
		sql="select :1, :2 where abc = :3",
		parameters=(1, 2, "abc"),
		parameter_names=(None, None, "existing"),
	)


def test_parameters_add_to_existing_qmark():
	p = Parameters(existing="abc")

	q = Q(f"select {p.add(1)}, {p.add(2)} where abc = {p['existing']}")

	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select ?, ? where abc = ?",
		parameters=(1, 2, "abc"),
		parameter_names=(None, None, "existing"),
	)


def test_parameters_add_key():
	p = Parameters(existing="abc")

	q = Q(f"select {p.add(one=1)}, {p.add(two=2)} where abc = {p['existing']}")

	assert q.build() == RenderedQuery(
		sql="select :1, :2 where abc = :3",
		parameters=(1, 2, "abc"),
		parameter_names=("one", "two", "existing"),
	)

	assert q.build(newParams={"one": "one"}) == RenderedQuery(
		sql="select :1, :2 where abc = :3",
		parameters=("one", 2, "abc"),
		parameter_names=("one", "two", "existing"),
	)


def test_parameters_add_nothing():
	p = Parameters(existing="abc")

	with pytest.raises(ValueError):
		p.add()


def test_parameters_add_arg_and_kw():
	p = Parameters(existing="abc")

	with pytest.raises(ValueError):
		p.add(1, kw="hi")


def test_parameters_add_multiple_kw():
	p = Parameters(existing="abc")

	with pytest.raises(ValueError):
		p.add(kw1="hi", kw2="hi")
