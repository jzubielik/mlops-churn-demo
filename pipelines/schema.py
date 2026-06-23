"""Pandera — data contract for the Telco churn dataset.

Describes the allowed types, ranges and value sets for each column.
If a frame does not satisfy the contract, validation raises `SchemaError(s)` and
stops the pipeline — before dirty data leaks into feature engineering.

Ranges are chosen with margin so that real (clean) data passes, while
anomalies (negative values, absurd values, unknown categories, wrong type) are caught.
"""

from __future__ import annotations

from pandera.pandas import Check, Column, DataFrameSchema

YES_NO = ["Yes", "No"]
SERVICE = ["Yes", "No", "No internet service"]
LINES = ["Yes", "No", "No phone service"]
CONTRACTS = ["Month-to-month", "One year", "Two year"]
INTERNET = ["DSL", "Fiber optic", "No"]
PAYMENTS = [
    "Electronic check",
    "Mailed check",
    "Bank transfer (automatic)",
    "Credit card (automatic)",
]

churn_schema = DataFrameSchema(
    {
        "customerID": Column(str, nullable=False),
        "gender": Column(str, Check.isin(["Female", "Male"]), nullable=False),
        "SeniorCitizen": Column(int, Check.isin([0, 1]), nullable=False),
        "Partner": Column(str, Check.isin(YES_NO), nullable=False),
        "Dependents": Column(str, Check.isin(YES_NO), nullable=False),
        "tenure": Column(int, Check.in_range(0, 72), nullable=False),
        "PhoneService": Column(str, Check.isin(YES_NO), nullable=False),
        "MultipleLines": Column(str, Check.isin(LINES), nullable=False),
        "InternetService": Column(str, Check.isin(INTERNET), nullable=False),
        "OnlineSecurity": Column(str, Check.isin(SERVICE), nullable=False),
        "OnlineBackup": Column(str, Check.isin(SERVICE), nullable=False),
        "DeviceProtection": Column(str, Check.isin(SERVICE), nullable=False),
        "TechSupport": Column(str, Check.isin(SERVICE), nullable=False),
        "StreamingTV": Column(str, Check.isin(SERVICE), nullable=False),
        "StreamingMovies": Column(str, Check.isin(SERVICE), nullable=False),
        "Contract": Column(str, Check.isin(CONTRACTS), nullable=False),
        "PaperlessBilling": Column(str, Check.isin(YES_NO), nullable=False),
        "PaymentMethod": Column(str, Check.isin(PAYMENTS), nullable=False),
        "MonthlyCharges": Column(float, Check.in_range(0.0, 200.0), nullable=False),
        "TotalCharges": Column(float, Check.in_range(0.0, 20000.0), nullable=False),
        "Churn": Column(str, Check.isin(YES_NO), nullable=False),
    },
    coerce=False,
    strict=False,
)
