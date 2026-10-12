import pytest
import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from atlas.persistence.db import init_db, SessionFactory, Base, engine as db_engine
from atlas.analytics.engine import engine
from examples.generate_sample_data import generate_sample_sales_data

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    init_db()
    yield

@pytest.fixture(autouse=True)
def clean_tables():
    # Clean tables before each test for total isolation
    db = SessionFactory()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()
    yield

@pytest.fixture
def sample_sales_df():
    return generate_sample_sales_data(100, seed=123)

@pytest.fixture
def registered_dataset(sample_sales_df):
    dataset_id = "test_sales_ds"
    engine.register_dataset(dataset_id, sample_sales_df)
    return dataset_id
