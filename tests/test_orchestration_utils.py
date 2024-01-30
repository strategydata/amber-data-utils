import os
import json
import csv
import pandas as pd

from gitlabdata.orchestration_utils import (
    snowflake_engine_factory,
    query_executor,
    dataframe_uploader,
    snowflake_stage_load_copy_remove,
)

config_dict = os.environ.copy()


class TestSnowflakeEngineFactory:
    """
    Tests the snowflake_engine_factory.
    """

    config_dict = os.environ.copy()

    def test_connection(self):
        """
        Tests that a connection can be made.
        """

        engine = snowflake_engine_factory(config_dict, "SYSADMIN")
        try:
            connection = engine.connect()
            result = connection.execute("select current_version()").fetchone()[0]
            print(result)
            assert type(result) == str
        finally:
            connection.close()
            engine.dispose()

    def test_database(self):
        """
        Tests that a connection can be made.
        """

        engine = snowflake_engine_factory(config_dict, "SYSADMIN")
        try:
            connection = engine.connect()
            result = connection.execute("select current_database()").fetchone()[0]
            print(result)
            assert result == "TESTING_DB"
        finally:
            connection.close()
            engine.dispose()

    def test_schema(self):
        """
        Tests that a connection can be made.
        """

        engine = snowflake_engine_factory(config_dict, "SYSADMIN", "GITLAB")
        try:
            connection = engine.connect()
            result = connection.execute("select current_schema()").fetchone()[0]
            print(result)
            assert result == "GITLAB"
        finally:
            connection.close()
            engine.dispose()


class TestQueryExecutor:
    """
    Tests the query_executor.
    """

    config_dict = os.environ.copy()

    def test_connection(self):
        """
        Tests that a connection can be made.
        """

        engine = snowflake_engine_factory(config_dict, "SYSADMIN", "GITLAB")
        query = "select current_version()"
        results = query_executor(engine, query)
        assert type(results[0][0]) == str


class TestDataFrameUploader:
    """
    Tests the dataframe_uploader.
    """

    config_dict = os.environ.copy()

    def test_upload(self):
        """
        Tests that a connection can be made.
        """

        engine = snowflake_engine_factory(config_dict, "SYSADMIN", "GITLAB")
        table = "test_table"
        dummy_dict = {"foo": [1, 2, 3], "bar": [1, 2, 3]}

        # Create a dummy DF to upload
        dummy_df = pd.DataFrame(dummy_dict)
        dataframe_uploader(dummy_df, engine, table)

        query = f"select * from {table}"
        results = query_executor(engine, query)
        query_executor(engine, f"drop table {table}")
        assert results[0][:2] == (1, 1)


class TestSnowflakeStageLoadCopyRemove:
    """
    Test snowflake_stage_load_copy_remove()

    Setup/teardown functions are seperated from test function
    so that future tests will use them automatically.
    """

    # get a copy of the environment variables
    env_vars = os.environ.copy()

    @staticmethod
    def dump_json(dict_to_dump, filename):
        """
        Dump a dictionary to a JSON file.

        Args:
            dict_to_dump (dict): The dictionary to dump to the file.
            filename (str): The name of the file to create or overwrite.
        """
        with open(filename, "w+", encoding="utf-8") as json_file:
            json.dump(dict_to_dump, json_file)

    def setup_method(self):
        """
        Set up the necessary components for testing.
        """
        # create a Snowflake engine and connection
        self.engine = snowflake_engine_factory(self.env_vars, "SYSADMIN", "GITLAB")
        self.connection = self.engine.connect()

        # create a second engine just for snowflake_stage_load_copy_remove
        self.upload_engine = snowflake_engine_factory(
            self.env_vars, "SYSADMIN", "GITLAB"
        )

        # create stage for testing
        self.test_stage = "test_utils_json_stage"
        self.connection.execute(
            f"CREATE OR REPLACE STAGE {self.test_stage} FILE_FORMAT = (TYPE = 'JSON');"
        )
        self.test_table_name = "snowflake_stage_load_copy_remove_test_table"

    def teardown_method(self):
        """
        Remove the temporary components used for testing.
        """
        # drop the test stage and table, and dispose of the connection and engine
        self.connection.execute(f"DROP STAGE IF EXISTS {self.test_stage}")
        self.connection.execute(f"DROP TABLE IF EXISTS {self.test_table_name}")
        self.connection.close()
        self.engine.dispose()

    def test_snowflake_stage_load_copy_remove_json(self):
        """
        Test the file upload functionality.
        Two conditions to be tested:
            1. upload_dict is uploaded sucessfully and deleted from stage
            2. keep.json is placed in internal stage but not uploaded nor deleted
        """

        # create table to upload to
        create_table_query = f"""
        CREATE OR REPLACE TABLE {self.test_table_name} (
          jsontext variant,
          uploaded_at timestamp_ntz(9) DEFAULT CAST(CURRENT_TIMESTAMP() AS TIMESTAMP_NTZ(9))
        );
        """
        self.connection.execute(create_table_query)

        # Create a local 'keep' file, upload it to the internal stage
        keep_file_name = "keep_in_stage_do_not_upload.json"
        self.dump_json({"1": "keep_in_stage"}, keep_file_name)
        put_query = (
            f"PUT 'file://{keep_file_name}' @{self.test_stage} AUTO_COMPRESS=TRUE;"
        )
        self.connection.execute(put_query)

        # Create a local 'upload' file that will be uploaded to a table and then removed from stage
        upload_file_name = "upload.json"
        upload_dict = {"1": "uploaded"}
        self.dump_json(upload_dict, upload_file_name)

        # the upload function we are testing
        snowflake_stage_load_copy_remove(
            upload_file_name, self.test_stage, self.test_table_name, self.upload_engine
        )

        # Condition 1: Correct file was uploaded to table
        select_query = f"SELECT * FROM {self.test_table_name};"
        df_select = pd.read_sql(select_query, self.engine)
        print(f"\ndf_select: {df_select}")

        # assert that the table only has one record
        assert df_select.shape == (1, 2)

        # assert that the dictionary we uploaded is the same dictionary in the table
        json_str = df_select.iloc[0]["jsontext"]  # to_sql converted col to lower
        res_dict = json.loads(json_str)
        print(f"\nres_dict: {res_dict}")
        assert res_dict == upload_dict

        # Condition 2: the interal stage should still have 'keep.json'
        stage_query = f"LIST @{self.test_stage};"
        df_stages = pd.read_sql(stage_query, self.engine)

        assert df_stages.shape[0] == 1  # should be 1 file in stage
        print(f"\ndf_stages: {df_stages}")

        assert (
            f"{self.test_stage}/{keep_file_name}.gz" == df_stages["name"][0]
        )  # And the remaining file is the 'keep' file

        # remove local files
        os.remove(upload_file_name)
        os.remove(keep_file_name)

    def test_snowflake_stage_load_copy_remove_csv(self):
        """
        Ensure that csv upload works
        """
        # create table to upload to
        create_table_query = f"""
        CREATE OR REPLACE TABLE {self.test_table_name} (
          first_name varchar,
          last_name varchar,
          age int
        );
        """
        self.connection.execute(create_table_query)

        upload_file_name = "upload.csv"
        csv_data = [["John", "Doe", "35"], ["Jane", "Smith", "27"]]

        # Open the CSV file and write the data
        with open(upload_file_name, mode="w+", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        snowflake_stage_load_copy_remove(
            upload_file_name,
            self.test_stage,
            self.test_table_name,
            self.upload_engine,
            type="csv",
        )

        # Condition 1: Correct file was uploaded to table
        select_query = f"SELECT * FROM {self.test_table_name} WHERE first_name = 'John' OR first_name = 'Jane';"
        df_select = pd.read_sql(select_query, self.engine)
        print(f"\ndf_select: {df_select}")

        # assert that the table returns 2 records
        assert df_select.shape == (2, 3)

        # Condition 2: the interal stage should be empty now
        stage_query = f"LIST @{self.test_stage};"
        df_stages = pd.read_sql(stage_query, self.engine)
        assert df_stages.shape[0] == 0

        os.remove(upload_file_name)
