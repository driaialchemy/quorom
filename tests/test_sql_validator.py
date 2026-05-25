"""Tests for SQL validator deterministic safety checks."""

import pytest

from quorum.tools.sql_validator import SQLValidationError, validate_and_fix_sql


class TestValidSQL:
    """Tests for SQL that should pass validation."""

    def test_valid_sql_with_limit_under_100(self):
        """Should pass through valid SQL with LIMIT under 100."""
        sql = "SELECT * FROM ORDERS LIMIT 50"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 50"

    def test_valid_sql_with_limit_exactly_100(self):
        """Should pass through valid SQL with LIMIT exactly 100."""
        sql = "SELECT * FROM ORDERS LIMIT 100"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 100"

    def test_valid_sql_with_limit_above_100_gets_capped(self):
        """Should cap LIMIT above 100 to 100."""
        sql = "SELECT * FROM ORDERS LIMIT 500"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 100"

    def test_valid_sql_without_limit_gets_limit_50(self):
        """Should append LIMIT 50 when missing."""
        sql = "SELECT * FROM ORDERS WHERE O_ORDERDATE > '2024-01-01'"
        result = validate_and_fix_sql(sql)
        assert result.endswith("LIMIT 50")
        assert "SELECT * FROM ORDERS WHERE O_ORDERDATE > '2024-01-01' LIMIT 50" == result

    def test_valid_complex_sql_without_limit(self):
        """Should append LIMIT 50 to complex query."""
        sql = """
        SELECT
            C_NAME,
            SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) as revenue
        FROM CUSTOMER
        JOIN ORDERS ON C_CUSTKEY = O_CUSTKEY
        JOIN LINEITEM ON O_ORDERKEY = L_ORDERKEY
        GROUP BY C_NAME
        ORDER BY revenue DESC
        """
        result = validate_and_fix_sql(sql)
        assert result.strip().endswith("LIMIT 50")

    def test_valid_sql_with_trailing_semicolon(self):
        """Should strip trailing semicolon and validate."""
        sql = "SELECT * FROM ORDERS LIMIT 50;"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 50"

    def test_valid_sql_case_insensitive_select(self):
        """Should accept lowercase SELECT."""
        sql = "select * from orders limit 20"
        result = validate_and_fix_sql(sql)
        assert "select * from orders" in result

    def test_valid_sql_case_insensitive_limit(self):
        """Should handle case-insensitive LIMIT keyword."""
        sql = "SELECT * FROM ORDERS limit 200"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 100"

    def test_unqualified_table_names_preserved(self):
        """Should preserve unqualified TPCH table names."""
        tables = ["CUSTOMER", "ORDERS", "LINEITEM", "PART", "SUPPLIER", "NATION", "REGION"]
        for table in tables:
            sql = f"SELECT * FROM {table}"
            result = validate_and_fix_sql(sql)
            assert table in result
            assert result.endswith("LIMIT 50")

    def test_join_with_unqualified_tables(self):
        """Should preserve multiple unqualified tables in JOIN."""
        sql = """
        SELECT C_NAME, O_ORDERDATE
        FROM CUSTOMER
        JOIN ORDERS ON C_CUSTKEY = O_CUSTKEY
        """
        result = validate_and_fix_sql(sql)
        assert "CUSTOMER" in result
        assert "ORDERS" in result
        assert result.strip().endswith("LIMIT 50")

    def test_cte_without_limit(self):
        """Should append LIMIT 50 to CTE query."""
        sql = """
        WITH revenue_by_customer AS (
            SELECT C_CUSTKEY, SUM(L_EXTENDEDPRICE * (1 - L_DISCOUNT)) as revenue
            FROM CUSTOMER
            JOIN LINEITEM ON C_CUSTKEY = L_CUSTKEY
            GROUP BY C_CUSTKEY
        )
        SELECT * FROM revenue_by_customer
        """
        result = validate_and_fix_sql(sql)
        assert "WITH revenue_by_customer AS" in result
        assert result.strip().endswith("LIMIT 50")

    def test_cte_with_limit_over_100(self):
        """Should cap LIMIT in CTE query."""
        sql = """
        WITH top_customers AS (
            SELECT * FROM CUSTOMER
        )
        SELECT * FROM top_customers LIMIT 200
        """
        result = validate_and_fix_sql(sql)
        assert "WITH top_customers AS" in result
        assert result.strip().endswith("LIMIT 100")

    def test_multiple_ctes(self):
        """Should handle multiple CTEs and append LIMIT."""
        sql = """
        WITH cte1 AS (
            SELECT * FROM CUSTOMER
        ),
        cte2 AS (
            SELECT * FROM ORDERS
        )
        SELECT * FROM cte1 JOIN cte2 ON cte1.C_CUSTKEY = cte2.O_CUSTKEY
        """
        result = validate_and_fix_sql(sql)
        assert "WITH cte1 AS" in result
        assert "cte2 AS" in result
        assert result.strip().endswith("LIMIT 50")

    def test_cte_lowercase_with(self):
        """Should accept lowercase WITH keyword."""
        sql = """
        with revenue AS (
            select * from ORDERS
        )
        select * from revenue
        """
        result = validate_and_fix_sql(sql)
        assert "with revenue AS" in result
        assert result.strip().endswith("LIMIT 50")


class TestRejectedSQL:
    """Tests for SQL that should be rejected."""

    def test_empty_sql_rejected(self):
        """Should reject empty SQL string."""
        with pytest.raises(SQLValidationError, match="SQL is empty"):
            validate_and_fix_sql("")

    def test_whitespace_only_sql_rejected(self):
        """Should reject whitespace-only SQL."""
        with pytest.raises(SQLValidationError, match="SQL is empty"):
            validate_and_fix_sql("   \n\t  ")

    def test_non_select_statement_rejected(self):
        """Should reject non-SELECT statements."""
        invalid_statements = [
            "INSERT INTO ORDERS VALUES (1, 2, 3)",
            "UPDATE ORDERS SET O_ORDERSTATUS = 'F' WHERE O_ORDERKEY = 1",
            "DELETE FROM ORDERS WHERE O_ORDERKEY = 1",
            "DROP TABLE ORDERS",
            "CREATE TABLE test (id INT)",
        ]
        for sql in invalid_statements:
            with pytest.raises(
                SQLValidationError,
                match="Only SELECT statements are allowed",
            ):
                validate_and_fix_sql(sql)

    def test_multi_statement_sql_rejected(self):
        """Should reject multi-statement SQL with semicolons."""
        sql = "SELECT * FROM ORDERS; SELECT * FROM CUSTOMER"
        with pytest.raises(
            SQLValidationError,
            match="Multi-statement SQL is not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_multi_statement_with_insert_rejected(self):
        """Should reject SELECT followed by INSERT."""
        sql = "SELECT * FROM ORDERS; INSERT INTO CUSTOMER VALUES (1, 'test')"
        with pytest.raises(
            SQLValidationError,
            match="Multi-statement SQL is not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_fully_qualified_table_name_rejected(self):
        """Should reject fully qualified TPCH table names."""
        sql = "SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS"
        with pytest.raises(
            SQLValidationError,
            match="Fully qualified table names are not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_fully_qualified_with_lowercase_rejected(self):
        """Should reject fully qualified names regardless of case."""
        sql = "SELECT * FROM snowflake_sample_data.tpch_sf1.customer"
        with pytest.raises(
            SQLValidationError,
            match="Fully qualified table names are not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_fully_qualified_in_join_rejected(self):
        """Should reject fully qualified names in JOIN clause."""
        sql = """
        SELECT *
        FROM ORDERS
        JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER ON C_CUSTKEY = O_CUSTKEY
        """
        with pytest.raises(
            SQLValidationError,
            match="Fully qualified table names are not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_mixed_qualified_and_unqualified_rejected(self):
        """Should reject SQL with mix of qualified and unqualified names."""
        sql = """
        SELECT *
        FROM ORDERS
        JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.LINEITEM ON O_ORDERKEY = L_ORDERKEY
        """
        with pytest.raises(
            SQLValidationError,
            match="Fully qualified table names are not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_cte_with_qualified_table_rejected(self):
        """Should reject CTE with fully qualified table names."""
        sql = """
        WITH revenue AS (
            SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS
        )
        SELECT * FROM revenue
        """
        with pytest.raises(
            SQLValidationError,
            match="Fully qualified table names are not allowed",
        ):
            validate_and_fix_sql(sql)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_limit_with_extra_whitespace(self):
        """Should handle LIMIT with extra whitespace."""
        sql = "SELECT * FROM ORDERS LIMIT    50   "
        result = validate_and_fix_sql(sql)
        assert "LIMIT 50" in result or "LIMIT    50" in result

    def test_limit_one(self):
        """Should preserve LIMIT 1."""
        sql = "SELECT * FROM ORDERS LIMIT 1"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 1"

    def test_limit_exactly_101_gets_capped(self):
        """Should cap LIMIT 101 to 100."""
        sql = "SELECT * FROM ORDERS LIMIT 101"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 100"

    def test_limit_very_large_number_gets_capped(self):
        """Should cap extremely large LIMIT to 100."""
        sql = "SELECT * FROM ORDERS LIMIT 999999"
        result = validate_and_fix_sql(sql)
        assert result == "SELECT * FROM ORDERS LIMIT 100"

    def test_select_with_leading_whitespace(self):
        """Should handle SELECT with leading whitespace."""
        sql = "   \n  SELECT * FROM ORDERS"
        result = validate_and_fix_sql(sql)
        assert result.strip().startswith("SELECT")
        assert result.endswith("LIMIT 50")

    def test_select_with_newlines(self):
        """Should handle multi-line SELECT without LIMIT."""
        sql = """
        SELECT
            O_ORDERKEY,
            O_ORDERDATE
        FROM ORDERS
        """
        result = validate_and_fix_sql(sql)
        assert result.strip().endswith("LIMIT 50")

    def test_subquery_without_limit(self):
        """Should append LIMIT to query with subquery."""
        sql = """
        SELECT * FROM (
            SELECT O_ORDERKEY FROM ORDERS
        ) AS subquery
        """
        result = validate_and_fix_sql(sql)
        # Main query should get LIMIT, not subquery
        assert result.strip().endswith("LIMIT 50")

    def test_multiple_semicolons_rejected(self):
        """Should reject SQL with multiple semicolons."""
        sql = "SELECT * FROM ORDERS;;"
        with pytest.raises(
            SQLValidationError,
            match="Multi-statement SQL is not allowed",
        ):
            validate_and_fix_sql(sql)

    def test_semicolon_in_middle_rejected(self):
        """Should reject SQL with semicolon in middle."""
        sql = "SELECT * FROM ORDERS; SELECT * FROM CUSTOMER;"
        with pytest.raises(
            SQLValidationError,
            match="Multi-statement SQL is not allowed",
        ):
            validate_and_fix_sql(sql)
