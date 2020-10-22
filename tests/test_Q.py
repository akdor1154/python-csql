from csql import Q, RenderedQuery

def test_Q_str() -> None:
    q = Q("select 1")
    assert q.build() == RenderedQuery(
        sql="select 1",
        parameters=[]
    )

def test_Q_lambda_str() -> None:
    q = Q(lambda: "select 1")
    assert q.build() == RenderedQuery(
        sql="select 1",
        parameters=[]
    )

def test_Q_lambda_fstr() -> None:
    q = Q(lambda: f"select 1")
    assert q.build() == RenderedQuery(
        sql="select 1",
        parameters=[]
    )

def test_Q_lambda_fstr_no_assign() -> None:
    # can't test the result of this, waahh, but the AST looks
    # different and this used to crash.
    Q(lambda: f"select 1")
    pass

def test_Q_lambda_fstr_in_fn() -> None:
    # can't test the result of this, waahh, but the AST looks
    # different and this used to crash.
    str(Q(lambda: f"select 1"))
    pass